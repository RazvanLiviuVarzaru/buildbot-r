from dataclasses import replace
from pathlib import Path

import yaml

from configuration.builders.base import GenericBuilder
from configuration.builders.common import docker_config
from configuration.builders.definitions.foundry import sources
from configuration.builders.sequences.foundry import autobake, dispatcher

with open(Path(__file__).parent / "foundry.yaml") as f:
    _FOUNDRY_CONFIG = yaml.safe_load(f)

FOUNDRY_REPOSITORY = _FOUNDRY_CONFIG["repository"]
_CI_URL = _FOUNDRY_CONFIG["server"]["ci_url"]
_MIRROR_URL = _FOUNDRY_CONFIG["server"]["mirror_url"]
_ARCH_OVERRIDES = _FOUNDRY_CONFIG["arch"]

_SEQUENCE_BY_PACKAGE_TYPE = {
    "rpm": autobake.rpm,
    "deb": autobake.deb,
}


def _base_image_config(package_config, arch_override):
    # The target's plain upstream image, where rpm/deb packages are installed
    # and tested (see autobake._packages). A full image reference, hence the
    # empty repository; same bind mounts and environment as the worker image,
    # plus the target's base_mounts.
    image = package_config["base_image"]
    if "base_image_prefix" in arch_override:
        image = arch_override["base_image_prefix"] + image.rsplit("/", 1)[-1]
    config = docker_config(
        image=image,
        platform=arch_override.get("platform"),
        additional_bind_mounts=[
            tuple(mount) for mount in package_config.get("base_mounts", [])
        ],
        # A bare distro image has no debconf defaults; keep apt from
        # prompting (e.g. tzdata) while dependencies get pulled in.
        additional_env_vars=[("DEBIAN_FRONTEND", "noninteractive")],
    )
    return replace(config, repository="")


# (package type, its settings, target, target settings), from the
# per-family sections of "packages" in foundry.yaml.
_TARGETS = [
    (package_type, type_config, package, package_config)
    for package_type, type_config in _FOUNDRY_CONFIG["packages"].items()
    for package, package_config in type_config["targets"].items()
]


FOUNDRY_BUILDERS_BY_ARCH = {}
# Builders grouped by target, regardless of arch.
FOUNDRY_BUILDERS_BY_PACKAGE = {}
for package_type, type_config, package, package_config in _TARGETS:
    for arch in package_config["arch"]:
        arch_override = _ARCH_OVERRIDES.get(arch, {})
        platform = arch_override.get("platform")
        container_config = docker_config(
            image=f"{package_config['image']}{arch_override.get('image_suffix', '')}",
            platform=platform,
        )
        # The MariaDB server builder this one mirrors, e.g.
        # "amd64-debian-12-deb-autobake" -- see BUILDERS_AUTOBAKE in
        # constants.py.
        server_builder = f"{arch}-{package}"
        if package_type == "bintar":
            # Bintar builds link against a MariaDB server bintar (see
            # autobake.bintar) instead of installing -devel packages from an
            # autobake builder's repo, so there's no repo URL to build. Only
            # the CI side is per builder -- the mirror bintar is the same
            # tarball for every builder, see DownloadServerBintarFromMirror.
            sequence = autobake.bintar(
                container_config,
                ci_bintar_url=f"{_CI_URL}/%(prop:tarbuildnum)s/{server_builder}",
                mirror_url=_MIRROR_URL,
                mirror_bintar=type_config["mirror_bintar"],
            )
        else:
            # Both repo sources are wired into every package builder; which
            # one runs is decided per build from the tarbuildnum property.
            # The server builder publishes the CI repo file; the mirrors
            # publish one repo directory per MariaDB version.
            sequence = _SEQUENCE_BY_PACKAGE_TYPE[package_type](
                container_config,
                base_config=_base_image_config(package_config, arch_override),
                repo_file_url=(
                    f"{_CI_URL}/%(prop:tarbuildnum)s/{server_builder}"
                    f"/{type_config['repo_file']}"
                ),
                mirror_repo_url=(
                    f"{_MIRROR_URL}/{type_config['mirror_path']}"
                    "/%(prop:mariadb_version)s"
                ),
                build_packages=type_config["build_packages"],
                test_packages=type_config["test_packages"],
            )
        builder = GenericBuilder(
            name=f"foundry-{server_builder}",
            sequences=[sequence],
        )
        FOUNDRY_BUILDERS_BY_ARCH.setdefault(arch, []).append(builder)
        FOUNDRY_BUILDERS_BY_PACKAGE.setdefault(package, []).append(builder)

# Supported MariaDB versions and the targets each one builds. Configured in
# configuration/builders/definitions/foundry/foundry.yaml.
FOUNDRY_MARIADB_VERSIONS = _FOUNDRY_CONFIG["mariadb_versions"]
for version, version_config in FOUNDRY_MARIADB_VERSIONS.items():
    for package in version_config["targets"] + version_config["ci_only"]:
        assert (
            package in FOUNDRY_BUILDERS_BY_PACKAGE
        ), f"Unknown foundry package: {package}"
    both = set(version_config["targets"]) & set(version_config["ci_only"])
    assert not both, f"{version}: in both targets and ci_only: {sorted(both)}"

FOUNDRY_FORCE_USERS = _FOUNDRY_CONFIG["access"]["force_users"]


def _builder_names(packages):
    return [
        builder.name
        for package in packages
        for builder in FOUNDRY_BUILDERS_BY_PACKAGE[package]
    ]


# Which builders each Triggerable fires, keyed by scheduler name -- consumed
# by FOUNDRY_TRIGGERABLE_SCHEDULERS in configuration/schedulers/foundry.py.
# A version gets a second Triggerable only if it has ci_only targets.
FOUNDRY_TRIGGERABLE_BUILDERS = {}
for version, version_config in FOUNDRY_MARIADB_VERSIONS.items():
    FOUNDRY_TRIGGERABLE_BUILDERS[sources.scheduler_name(version)] = _builder_names(
        version_config["targets"]
    )
    if version_config["ci_only"]:
        FOUNDRY_TRIGGERABLE_BUILDERS[sources.ci_only_scheduler_name(version)] = (
            _builder_names(version_config["ci_only"])
        )


def _dispatch_specs():
    # One spec per supported MariaDB version, telling _FoundryDispatchStep
    # which force-scheduler fields hold that version's choice and which
    # Triggerable to fire once it has read them.
    return [
        {
            "mariadb_version": version,
            "source_property": sources.source_property(version),
            "tarbuildnum_property": sources.tarbuildnum_property(version),
            "scheduler": sources.scheduler_name(version),
            # Fired alongside "scheduler" only for a CI tarball run; None
            # when the version has no ci_only targets.
            "ci_only_scheduler": (
                sources.ci_only_scheduler_name(version)
                if version_config["ci_only"]
                else None
            ),
            "ci_only_targets": version_config["ci_only"],
        }
        for version, version_config in FOUNDRY_MARIADB_VERSIONS.items()
    ]


_DISPATCHER = _FOUNDRY_CONFIG["dispatcher"]

DISPATCHER_BUILDER = GenericBuilder(
    name=_DISPATCHER["builder"],
    sequences=[
        dispatcher.trigger_foundry(
            docker_config(image=_DISPATCHER["image"]), _dispatch_specs()
        )
    ],
)
