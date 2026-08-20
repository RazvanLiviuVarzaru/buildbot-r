from pathlib import Path

import yaml

from configuration.builders.base import GenericBuilder
from configuration.builders.common import docker_config
from configuration.builders.sequences.foundry import autobake, dispatcher

with open(Path(__file__).parent / "foundry.yaml") as f:
    _FOUNDRY_CONFIG = yaml.safe_load(f)

_SEQUENCE_BY_PACKAGE_TYPE = {
    "rpm": autobake.rpm,
    "deb": autobake.deb,
}
_REPO_FILE_BY_PACKAGE_TYPE = {
    "rpm": "MariaDB.repo",
    "deb": "mariadb.sources",
}
# TEMPORARY: pull the MariaDB-devel/libmariadb-dev repo from production CI
# rather than $ARTIFACTS_URL (dev), to build against real tarballs while this
# pipeline is still dev-only. Revert to os.environ["ARTIFACTS_URL"] once done.
_DEVEL_REPO_ARTIFACTS_URL = "https://ci.mariadb.org"


def foundry_scheduler_name(mariadb_version):
    return f"foundry_{mariadb_version.replace('.', '_')}_scheduler"


# Selectable via foundry_force_scheduler's "plugin" parameter.
FOUNDRY_PLUGINS = _FOUNDRY_CONFIG["plugins"]


FOUNDRY_BUILDERS_BY_ARCH = {}
# Builders grouped by (ops, os version), regardless of arch.
FOUNDRY_BUILDERS_BY_PACKAGE = {}
for package_config in _FOUNDRY_CONFIG["packages"]:
    ops = package_config["ops"]
    version = package_config["version"]
    package = f"{ops}-{version}"
    package_type = package_config["type"]
    sequence_fn = _SEQUENCE_BY_PACKAGE_TYPE[package_type]
    repo_file = _REPO_FILE_BY_PACKAGE_TYPE[package_type]
    for arch in package_config["arch"]:
        # Server autobake builder that publishes MariaDB-devel/libmariadb-dev
        # for this platform, e.g. "amd64-debian-12-deb-autobake" -- see
        # BUILDERS_AUTOBAKE in constants.py.
        autobake_builder = f"{arch}-{package_config['os_info_key']}-{package_type}-autobake"
        repo_file_url = (
            f"{_DEVEL_REPO_ARTIFACTS_URL}/%(prop:tarbuildnum)s/{autobake_builder}/{repo_file}"
        )
        builder = GenericBuilder(
            name=f"foundry-{arch}-{ops}-{version}",
            sequences=[
                sequence_fn(docker_config(image=f"{ops}{version}"), repo_file_url)
            ],
        )
        FOUNDRY_BUILDERS_BY_ARCH.setdefault(arch, []).append(builder)
        FOUNDRY_BUILDERS_BY_PACKAGE.setdefault(package, []).append(builder)

# Supported MariaDB versions: which packages get built for each, and the
# tarbuildnum of the server CI build to install devel packages from.
# Configured in configuration/builders/definitions/foundry/foundry.yaml.
FOUNDRY_MARIADB_VERSIONS = _FOUNDRY_CONFIG["mariadb_versions"]
for version_config in FOUNDRY_MARIADB_VERSIONS.values():
    for package in version_config["packages"]:
        assert package in FOUNDRY_BUILDERS_BY_PACKAGE, f"Unknown foundry package: {package}"

DISPATCHER_BUILDER = GenericBuilder(
    name="foundry-trigger-builders",
    sequences=[
        dispatcher.trigger_foundry(
            [
                (
                    foundry_scheduler_name(version),
                    {
                        "mariadb_version": version,
                        "tarbuildnum": version_config["tarbuildnum"],
                    },
                )
                for version, version_config in FOUNDRY_MARIADB_VERSIONS.items()
            ]
        )
    ],
)
