from configuration.builders.base import GenericBuilder
from configuration.builders.sequences.connectors.conodbc import (
    deb,
    rpm,
    rpm_pkg_tests,
    tarball,
    deb_pkg_tests,
    bintar,
    save_packages,
    get_source_package,
    srpm_pkg_test,
)
from configuration.builders.common import (
    docker_config,
)
import os
from configuration.builders.infra.runtime import Sidecar
from configuration.builders.infra.runtime import DockerConfig
from buildbot.plugins import util

AMD64_DEB_BUILDERS = []
AMD64_RPM_BUILDERS = []

PACKAGES_DIR = f"{os.environ['CONNECTORS_PACKAGES_DIR']}/odbc"
BUILD_BASE_PATH = "build"
BINTAR_PATH = f"{BUILD_BASE_PATH}/bintar"
RPM_PATH = f"{BUILD_BASE_PATH}/rpm"
DEB_PATH = f"{BUILD_BASE_PATH}/deb"
SOURCE_PATH = f"{BUILD_BASE_PATH}/source"
BINTAR_PACKAGES_TO_SAVE = [f"{BINTAR_PATH}/*.tar.gz"]
DEB_PACKAGES_TO_SAVE = [f"{DEB_PATH}/*.deb", f"{DEB_PATH}/*.ddeb"]
RPM_PACKAGES_TO_SAVE = [f"{RPM_PATH}/*.rpm", f"{RPM_PATH}/srpms/*.src.rpm"]


# MariaDB Server used for ODBC tests
SIDECAR = Sidecar(
    repository="docker.io/library/",
    image_tag="mariadb:lts",
    env_vars=[("MARIADB_ALLOW_EMPTY_ROOT_PASSWORD", "1"), ("MARIADB_DATABASE", "test")],
)


TARBALL = GenericBuilder(
    name="codbc-tarball-docker",
    sequences=[
        tarball(
            config=docker_config(
                image="debian13",
                packages_dir=PACKAGES_DIR,
                artifacts_url=f"{os.environ['ARTIFACTS_URL']}/connector-odbc/",
            ),
        )
    ],
)


def generate_rpm_release_sq(ops, version):
    build_environment = docker_config(
        image=f"{ops}{version}",
        packages_dir=PACKAGES_DIR,
        artifacts_url=f"{os.environ['ARTIFACTS_URL']}/connector-odbc/",
    )
    clean_environment = docker_config(
        image=f"{ops}{version}-srpm",
        packages_dir=PACKAGES_DIR,
        artifacts_url=f"{os.environ['ARTIFACTS_URL']}/connector-odbc/",
    )

    if ops == "rhel":
        rhel_subscription_mounts = [
            (
                "/etc/pki/entitlement",
                "/run/secrets/etc-pki-entitlement",
            ),
            ("/etc/rhsm", "/run/secrets/rhsm"),
        ]
        build_environment.bind_mounts += rhel_subscription_mounts
        clean_environment.bind_mounts += rhel_subscription_mounts

    bintar_sqs = [
        get_source_package(
            config=build_environment,
            source_path=SOURCE_PATH,
        ),
        bintar(
            config=build_environment,
            source_path=SOURCE_PATH,
            bintar_path=BINTAR_PATH,
            typ=f"{ops}{version}",
            jobs=util.Property("jobs"),
        ),
        save_packages(
            packages=BINTAR_PACKAGES_TO_SAVE,
            config=clean_environment,
        ),
    ]

    rhel_sqs = [
        rpm(
            config=build_environment,
            jobs=util.Property("jobs"),
            typ=f"{ops}{version}",
            rpm_path=RPM_PATH,
            source_path=SOURCE_PATH,
        ),
        rpm_pkg_tests(
            config=clean_environment,
            rpm_path=RPM_PATH,
        ),
        srpm_pkg_test(
            config=clean_environment,
            jobs=util.Property("jobs"),
            rpms_dir=RPM_PATH,
        ),
        save_packages(
            packages=RPM_PACKAGES_TO_SAVE,
            config=clean_environment,
        ),
    ]

    if ops == "rhel":
        return bintar_sqs + rhel_sqs
    return bintar_sqs


def generate_deb_release_sq(ops, version):
    build_environment = docker_config(
        image=f"{ops}{version}",
        packages_dir=PACKAGES_DIR,
        artifacts_url=f"{os.environ['ARTIFACTS_URL']}/connector-odbc/",
    )
    clean_environment = DockerConfig(
        repository="docker.io/library/",
        image_tag=f"{ops}:{version}",
        bind_mounts=[(f"{PACKAGES_DIR}/", "/packages")],
    )

    return [
        get_source_package(
            config=build_environment,
            source_path=SOURCE_PATH,
        ),
        bintar(
            config=build_environment,
            source_path=SOURCE_PATH,
            bintar_path=BINTAR_PATH,
            typ=f"{ops[:3]}{version}",
            jobs=util.Property("jobs"),
        ),
        deb(
            config=build_environment,
            jobs=util.Property("jobs"),
            typ=f"{ops[:3]}{version}",
            deb_path=DEB_PATH,
            source_path=SOURCE_PATH,
        ),
        deb_pkg_tests(
            config=clean_environment,
            deb_path=DEB_PATH,
        ),
        save_packages(
            packages=DEB_PACKAGES_TO_SAVE + BINTAR_PACKAGES_TO_SAVE,
            user="root",
            config=clean_environment,
        ),
    ]


for (
    ops,
    version,
) in [
    ("debian", "11"),
    ("debian", "12"),
    ("debian", "13"),
    ("ubuntu", "22.04"),
    ("ubuntu", "24.04"),
]:
    AMD64_DEB_BUILDERS.append(
        GenericBuilder(
            name=f"codbc-amd64-{ops}-{version}",
            sidecar=SIDECAR,
            sequences=generate_deb_release_sq(ops=ops, version=version),
        )
    )

for (
    ops,
    version,
) in [
    # ("fedora", "42"),
    # ("fedora", "43"),
    # ("sles", "1507"),
    ("rhel", "8"),
    ("rhel", "9"),
    ("rhel", "10"),
]:
    AMD64_RPM_BUILDERS.append(
        GenericBuilder(
            name=f"codbc-amd64-{ops}-{version}",
            sidecar=SIDECAR,
            sequences=generate_rpm_release_sq(ops=ops, version=version),
        )
    )

# Gather builders for all architectures
RPM_BUILDERS = [*AMD64_RPM_BUILDERS]
# DEB_BUILDERS = [*AMD64_DEB_BUILDERS]
DEB_BUILDERS = []
