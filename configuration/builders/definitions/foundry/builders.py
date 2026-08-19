from pathlib import Path

import yaml

from configuration.builders.base import GenericBuilder
from configuration.builders.sequences.foundry import autobake, dispatcher

with open(Path(__file__).parent / "foundry.yaml") as f:
    _FOUNDRY_CONFIG = yaml.safe_load(f)

_SEQUENCE_BY_PACKAGE_TYPE = {
    "rpm": autobake.rpm,
    "deb": autobake.deb,
}


def foundry_scheduler_name(mariadb_version):
    return f"foundry_{mariadb_version.replace('.', '_')}_scheduler"


FOUNDRY_BUILDERS_BY_ARCH = {}
# Builders grouped by (ops, os version), regardless of arch.
FOUNDRY_BUILDERS_BY_PACKAGE = {}
for package_config in _FOUNDRY_CONFIG["packages"]:
    ops = package_config["ops"]
    version = package_config["version"]
    package = f"{ops}-{version}"
    sequence_fn = _SEQUENCE_BY_PACKAGE_TYPE[package_config["type"]]
    for arch in package_config["arch"]:
        builder = GenericBuilder(
            name=f"foundry-{arch}-{ops}-{version}",
            sequences=[sequence_fn()],
        )
        FOUNDRY_BUILDERS_BY_ARCH.setdefault(arch, []).append(builder)
        FOUNDRY_BUILDERS_BY_PACKAGE.setdefault(package, []).append(builder)

# Supported MariaDB versions, and which packages get built for each one.
# Configured in configuration/builders/definitions/foundry/foundry.yaml.
FOUNDRY_MARIADB_VERSIONS = _FOUNDRY_CONFIG["mariadb_versions"]
for packages in FOUNDRY_MARIADB_VERSIONS.values():
    for package in packages:
        assert package in FOUNDRY_BUILDERS_BY_PACKAGE, f"Unknown foundry package: {package}"

DISPATCHER_BUILDER = GenericBuilder(
    name="foundry-trigger-builders",
    sequences=[
        dispatcher.trigger_foundry(
            [
                (foundry_scheduler_name(version), {"mariadb_version": version})
                for version in FOUNDRY_MARIADB_VERSIONS
            ]
        )
    ],
)
