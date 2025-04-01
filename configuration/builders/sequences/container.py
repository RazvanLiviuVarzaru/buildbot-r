from configuration.builders.infra.runtime import InContainerBuildSequence
from configuration.steps.base import StepOptions
from configuration.steps.commands.compile import (
    MAKE,
    CompileMakeCommand,
    InstallRPMFromProp,
)
from configuration.steps.commands.configure import ConfigureMariaDBCMake
from configuration.steps.commands.fetch_file import FetchCompat, FetchTarball, FindFiles
from configuration.steps.commands.mtr import ArchiveLogs, MTRTest
from configuration.steps.commands.packages import CreateRpmRepo, SavePackages
from configuration.steps.generators.cmake.generator import CMakeGenerator
from configuration.steps.generators.cmake.options import (
    OTHER,
    BuildConfig,
    CMakeOption,
)
from configuration.steps.generators.mtr.generator import MTRGenerator
from configuration.steps.generators.mtr.options import (
    MTR,
    SUITE,
    MTROption,
    TestSuiteCollection,
)
from configuration.steps.remote import DockerShellStep, PropFromShellStep, ShellStep
from constants import SAVED_PACKAGE_BRANCHES
from utils import hasFailed, hasPackagesGenerated, savePackageIfBranchMatch


def rpm_autobake(
    config,
    jobs,
    buildername,
    rpm_type,
    arch,
    artifacts_url,
    has_compat=False,
    test_galera=False,
):
    steps = []
    if has_compat:
        steps.append(
            ShellStep(
                command=FetchCompat(
                    rpm_type=rpm_type,
                    arch=arch,
                    url=artifacts_url,
                    workdir="",
                ),
            )
        )
    steps.extend(
        [
            ShellStep(
                FetchTarball(workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX")
            ),
            ShellStep(
                command=ConfigureMariaDBCMake(
                    name="mysql_release",
                    cmake_generator=CMakeGenerator(
                        use_ccache=True,
                        flags=[
                            CMakeOption(OTHER.BUILD_CONFIG, BuildConfig.MYSQL_RELEASE),
                            CMakeOption(OTHER.RPM, rpm_type),
                        ],
                    ),
                    workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX",
                )
            ),
            ShellStep(
                CompileMakeCommand(
                    option=MAKE.COMPILE,
                    jobs=jobs,
                    verbose=False,
                    workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX",
                )
            ),
            ShellStep(
                CompileMakeCommand(
                    option=MAKE.PACKAGE,
                    jobs=jobs,
                    verbose=False,
                    workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX",
                )
            ),
            ShellStep(
                CompileMakeCommand(
                    option=MAKE.SOURCE,
                    jobs=jobs,
                    verbose=False,
                    workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX",
                )
            ),
            PropFromShellStep(
                command=FindFiles(
                    include="*.rpm",
                    exclude="*.src.rpm",
                    workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX",
                ),
                property="packages",
            ),
            DockerShellStep(
                command=InstallRPMFromProp(
                    workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX",
                    property_name="packages",
                ),
                checkpoint=True,
            ),
            ShellStep(
                MTRTest(
                    name="normal",
                    workdir="/usr/share/mariadb-test",
                    testcase=MTRGenerator(
                        flags=[
                            MTROption(MTR.VERBOSE_RESTART, True),
                            MTROption(MTR.FORCE, True),
                            MTROption(MTR.RETRY, 3),
                            MTROption(MTR.MAX_SAVE_CORE, 2),
                            MTROption(MTR.MAX_SAVE_DATADIR, 1),
                            MTROption(MTR.MAX_TEST_FAIL, 20),
                            MTROption(MTR.PARALLEL, jobs * 2),
                            MTROption(MTR.VARDIR, "/home/buildbot/mtr/logs/normal"),
                        ],
                    ),
                ),
            ),
        ]
    )
    if test_galera:
        steps.append(
            ShellStep(
                MTRTest(
                    name="galera",
                    workdir="/usr/share/mariadb-test",
                    testcase=MTRGenerator(
                        flags=[
                            MTROption(MTR.VERBOSE_RESTART, True),
                            MTROption(MTR.FORCE, True),
                            MTROption(MTR.RETRY, 3),
                            MTROption(MTR.MAX_SAVE_CORE, 2),
                            MTROption(MTR.MAX_SAVE_DATADIR, 10),
                            MTROption(MTR.MAX_TEST_FAIL, 20),
                            MTROption(MTR.BIG_TEST, True),
                            MTROption(MTR.PARALLEL, jobs * 2),
                            MTROption(MTR.VARDIR, "/home/buildbot/mtr/logs/galera"),
                        ],
                        suite_collection=TestSuiteCollection(
                            [
                                SUITE.WSREP,
                                SUITE.GALERA,
                                SUITE.GALERA_3NODES,
                                SUITE.GALERA_3NODES_SR,
                            ]
                        ),
                    ),
                ),
            ),
        )
    steps.extend(
        [
            ShellStep(
                command=CreateRpmRepo(
                    rpm_type=rpm_type,
                    url=artifacts_url,
                    workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX",
                ),
            ),
            ShellStep(
                command=SavePackages(
                    packages=["MariaDB.repo", "rpms", "srpms"],
                    workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX",
                    destination="/packages/%(prop:tarbuildnum)s/%(prop:buildername)s",
                ),
                options=StepOptions(
                    doStepIf=(
                        lambda step: hasPackagesGenerated(step)
                        and savePackageIfBranchMatch(step, SAVED_PACKAGE_BRANCHES)
                    )
                ),
            ),
            ShellStep(
                command=ArchiveLogs(
                    workdir="/home/buildbot/mtr",
                    logs=["*.log", "*.err", "core*"],
                    archive_name="logs.tar.gz",
                    destination="/packages/%(prop:tarbuildnum)s/logs/%(prop:buildername)s",
                ),
                options=StepOptions(
                    alwaysRun=True, doStepIf=(lambda step: hasFailed(step))
                ),
            ),
        ]
    )
    return InContainerBuildSequence(config=config, steps=steps, buildername=buildername)
