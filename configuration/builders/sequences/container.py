from configuration.builders.infra.runtime import InContainerBuildSequence
from configuration.steps.remote import ShellStep,PropFromShellStep
# from configuration.steps.compile import CompileRpmAutobake, CompileMakeCommand
from configuration.steps.commands.configure import ConfigureMariaDBCMake
from configuration.steps.commands.fetch_file import UnpackTarball
from configuration.steps.commands.properties import hasRpmPackages
# from configuration.steps.packages import CreateRpmRepo, SaveRpmPackages
# from configuration.steps.properties import hasRpmPackages
# from configuration.steps.mtr import MTRTest, TestCases
from configuration.steps.generators.cmake.generator import CMakeGenerator
from configuration.steps.generators.cmake.compilers import GCCCompiler
from configuration.steps.generators.cmake.options import CMAKE, BuildType, CMakeOption, PLUGIN
# from constants import SAVED_PACKAGE_BRANCHES
# from utils import hasPackagesGenerated, savePackageIfBranchMatch
from utils import ls2string


def quick_build(config, mtr_jobs : int, has_galera : bool = False, has_s3 : bool = False):
    steps = []
    steps.extend([
        ShellStep(command=UnpackTarball(workdir="")),

        PropFromShellStep(command=hasRpmPackages(), extract_fn=ls2string),

        ShellStep(
            command=ConfigureMariaDBCMake(
                name='ReleaseWithDebInfo',
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
        )),])
    #     CompileMakeCommand(),
    #     MTRTest(name="normal", workdir="mysql-test", testcase=TestCases(jobs=mtr_jobs,vardir="/home/buildbot/var/normal").normal),   
    # ])

    # if has_galera:
    #     steps.extend([MTRTest(name="galera", workdir="mysql-test", testcase=TestCases(vardir="/home/buildbot/var/galera").galera),])

    # if has_s3:
    #     pass # TODO(Razvan) add s3 tests

    return InContainerBuildSequence(
        config=config,
        steps=steps,
    )





# def rpm_autobake(config, rpm_type, arch, url, has_compat=False):
#     steps = []
#     if has_compat:
#         steps.append(FetchCompat(rpm_type=rpm_type, arch=arch, url=url, workdir=""))

#     steps.extend([
#         UnpackTarball(workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX"),
#         ConfigureRpmAutoBakeCMake(
#             workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX", rpm_type=rpm_type
#         ),
#         CompileRpmAutobake(workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX"),
#         hasRpmPackages(workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX"),
#         CreateRpmRepo(
#             rpm_type=rpm_type,
#             url=url,
#             workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX",
#         ),
#         SaveRpmPackages(
#             rpm_type=rpm_type,
#             url=url,
#             workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX",
#             options=CommandOptions(
#                 doStepIf=(
#                     lambda step: hasPackagesGenerated(step)
#                     and savePackageIfBranchMatch(step, SAVED_PACKAGE_BRANCHES)
#                 )
#             ),
#         )
#     ])
#     return InContainerBuildSequence(
#         config=config,
#         steps=steps,
#     )
