from configuration.builders.infra.runtime import InContainerBuildSequence
from configuration.steps.base import CommandOptions
from configuration.steps.compile import CompileRpmAutobake, CompileMakeCommand
from configuration.steps.configure import ConfigureRpmAutoBakeCMake, ConfigureMariaDBCMake
from configuration.steps.fetch_file import FetchCompat, UnpackTarball
from configuration.steps.packages import CreateRpmRepo, SaveRpmPackages
from configuration.steps.properties import hasRpmPackages
from configuration.steps.mtr import MTRTest, TestCases
from configuration.steps.generators.cmake.generator import CMakeGenerator
from configuration.steps.generators.cmake.compilers import GCCCompiler
from configuration.steps.generators.cmake.options import CMAKE, BuildType, CMakeOption, PLUGIN
from constants import SAVED_PACKAGE_BRANCHES
from utils import hasPackagesGenerated, savePackageIfBranchMatch



def quick_build(config):
    steps = []
    steps.append(
        UnpackTarball(workdir="")
    )

    steps.extend([
        ConfigureMariaDBCMake(
        'ReleaseWithDebInfo',
        cmake_generator=CMakeGenerator(
            compiler=GCCCompiler(),
            use_ccache=True,
            flags=[
                CMakeOption(CMAKE.BUILD_TYPE, BuildType.RELWITHDEBUG),
                CMakeOption(PLUGIN.TOKUDB_STORAGE_ENGINE, False),
                CMakeOption(PLUGIN.MROONGA_STORAGE_ENGINE, False),
                CMakeOption(PLUGIN.SPIDER_STORAGE_ENGINE, False),
                CMakeOption(PLUGIN.OQGRAPH_STORAGE_ENGINE, False),
                CMakeOption(PLUGIN.PERFSCHEMA_FEATURE, True),
                CMakeOption(PLUGIN.SPHINX_STORAGE_ENGINE, False),
            ]),
    ),
        CompileMakeCommand(),
        MTRTest(name="normal", workdir="mysql-test", testcase=TestCases(vardir="/home/buildbot/var/normal").normal)
    ])

    return InContainerBuildSequence(
        config=config,
        steps=steps,
    )


def rpm_autobake(config, rpm_type, arch, url, has_compat=False):
    steps = []
    if has_compat:
        steps.append(FetchCompat(rpm_type=rpm_type, arch=arch, url=url, workdir=""))
    steps.append(
        UnpackTarball(workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX")
    )
    steps.append(
        ConfigureRpmAutoBakeCMake(
            workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX", rpm_type=rpm_type
        )
    )
    steps.append(
        CompileRpmAutobake(workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX")
    )
    steps.append(
        hasRpmPackages(workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX")
    )
    steps.append(
        CreateRpmRepo(
            rpm_type=rpm_type,
            url=url,
            workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX",
        )
    )
    steps.append(
        SaveRpmPackages(
            rpm_type=rpm_type,
            url=url,
            workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX",
            options=CommandOptions(
                doStepIf=(
                    lambda step: hasPackagesGenerated(step)
                    and savePackageIfBranchMatch(step, SAVED_PACKAGE_BRANCHES)
                )
            ),
        )
    )
    return InContainerBuildSequence(
        config=config,
        steps=steps,
    )
