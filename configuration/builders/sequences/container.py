from configuration.builders.infra.runtime import InContainerBuildSequence
from configuration.steps.remote import ShellStep,PropFromShellStep, DockerShellStep
from configuration.steps.commands.compile import CompileRpmAutobake, InstallRPMPackages
from configuration.steps.commands.configure import ConfigureMariaDBCMake, ConfigureRpmAutoBakeCMake
from configuration.steps.commands.fetch_file import UnpackTarball, SimpleTouchFile
from configuration.steps.commands.properties import hasRpmPackages
# from configuration.steps.packages import CreateRpmRepo, SaveRpmPackages
# from configuration.steps.properties import hasRpmPackages
from configuration.steps.commands.mtr import MTRTest, TestCases
from configuration.steps.generators.cmake.generator import CMakeGenerator
from configuration.steps.generators.cmake.compilers import GCCCompiler
from configuration.steps.generators.cmake.options import CMAKE, BuildType, CMakeOption, PLUGIN
# from constants import SAVED_PACKAGE_BRANCHES
# from utils import hasPackagesGenerated, savePackageIfBranchMatch
from utils import ls2string


# def quick_build(config, mtr_jobs : int, has_galera : bool = False, has_s3 : bool = False):
#     steps = []
#     steps.extend([
#         ShellStep(command=UnpackTarball(workdir="")),

#         PropFromShellStep(command=hasRpmPackages(), extract_fn=ls2string),

#         ShellStep(
#             command=ConfigureMariaDBCMake(
#                 name='ReleaseWithDebInfo',
#                 cmake_generator=CMakeGenerator(
#                     compiler=GCCCompiler(),
#                     use_ccache=True,
#                     flags=[
#                         CMakeOption(CMAKE.BUILD_TYPE, BuildType.RELWITHDEBUG),
#                         CMakeOption(PLUGIN.TOKUDB_STORAGE_ENGINE, False),
#                         CMakeOption(PLUGIN.MROONGA_STORAGE_ENGINE, False),
#                         CMakeOption(PLUGIN.SPIDER_STORAGE_ENGINE, False),
#                         CMakeOption(PLUGIN.OQGRAPH_STORAGE_ENGINE, False),
#                         CMakeOption(PLUGIN.PERFSCHEMA_FEATURE, True),
#                         CMakeOption(PLUGIN.SPHINX_STORAGE_ENGINE, False),
#                     ]),
#         )),])
#     #     CompileMakeCommand(),
#     #     MTRTest(name="normal", workdir="mysql-test", testcase=TestCases(jobs=mtr_jobs,vardir="/home/buildbot/var/normal").normal),   
#     # ])

#     # if has_galera:
#     #     steps.extend([MTRTest(name="galera", workdir="mysql-test", testcase=TestCases(vardir="/home/buildbot/var/galera").galera),])

#     # if has_s3:
#     #     pass # TODO(Razvan) add s3 tests

#     return InContainerBuildSequence(
#         config=config,
#         steps=steps,
#     )





# def rpm_autobake(config, buildername, rpm_type, arch, url, has_compat=False):
#     steps = []
#     # if has_compat:
#     #     steps.append(FetchCompat(rpm_type=rpm_type, arch=arch, url=url, workdir=""))

#     steps.extend([
#         # ShellStep(UnpackTarball(workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX")),
#         # ShellStep(ConfigureRpmAutoBakeCMake(
#         #     workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX", rpm_type=rpm_type)
#         # ),
#         # ShellStep(CompileRpmAutobake(workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX")),
#         DockerShellStep(command=InstallRPMPackages(workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX"), checkpoint=True),
#         ShellStep(
#             MTRTest(name="normal", workdir="/usr/share/mariadb-test", testcase=TestCases(jobs=14,vardir="/home/buildbot/mtr/logs/normal").normal),
#         )
#         # hasRpmPackages(workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX"),
#         # CreateRpmRepo(
#         #     rpm_type=rpm_type,
#         #     url=url,
#         #     workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX",
#         # ),
#         # SaveRpmPackages(
#         #     rpm_type=rpm_type,
#         #     url=url,
#         #     workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX",
#         #     options=CommandOptions(
#         #         doStepIf=(
#         #             lambda step: hasPackagesGenerated(step)
#         #             and savePackageIfBranchMatch(step, SAVED_PACKAGE_BRANCHES)
#         #         )
#         #     ),
#         # )
#     ])
#     return InContainerBuildSequence(
#         config=config,
#         steps=steps,
#         buildername=buildername
#     )

def rpm_autobake(config,buildername, rpm_type, arch, url, has_compat=False):
    steps = []
    # if has_compat:
    #     steps.append(FetchCompat(rpm_type=rpm_type, arch=arch, url=url, workdir=""))

    steps.extend([
        # ShellStep(UnpackTarball(workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX")),
        # ShellStep(ConfigureRpmAutoBakeCMake(
        #     workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX", rpm_type=rpm_type)
        # ),
        # ShellStep(CompileRpmAutobake(workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX")),
        # ShellStep(InstallRPMPackages(workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX")),
        # ShellStep(
        #     MTRTest(name="normal", workdir="/usr/share/mariadb-test", testcase=TestCases(jobs=14,vardir="/home/buildbot/mtr/logs/normal").normal),
        # )
        DockerShellStep(SimpleTouchFile(workdir="/tmp/", filename="test.txt"), checkpoint=False),
        DockerShellStep(SimpleTouchFile(workdir="/tmp/", filename="test1.txt"), checkpoint=False),
        DockerShellStep(SimpleTouchFile(workdir="/tmp/", filename="test_checkpoint1.txt"), checkpoint=True),
        DockerShellStep(SimpleTouchFile(workdir="/tmp/", filename="test3.txt"), checkpoint=False),
        DockerShellStep(SimpleTouchFile(workdir="/tmp/", filename="test4.txt"), checkpoint=False),
        DockerShellStep(SimpleTouchFile(workdir="/tmp/", filename="test_checkpoint2.txt"), checkpoint=True),
        DockerShellStep(SimpleTouchFile(workdir="/tmp/", filename="test5.txt"), checkpoint=False),
        DockerShellStep(SimpleTouchFile(workdir="/tmp/", filename="test6.txt"), checkpoint=False),
        # hasRpmPackages(workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX"),
        # CreateRpmRepo(
        #     rpm_type=rpm_type,
        #     url=url,
        #     workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX",
        # ),
        # SaveRpmPackages(
        #     rpm_type=rpm_type,
        #     url=url,
        #     workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX",
        #     options=CommandOptions(
        #         doStepIf=(
        #             lambda step: hasPackagesGenerated(step)
        #             and savePackageIfBranchMatch(step, SAVED_PACKAGE_BRANCHES)
        #         )
        #     ),
        # )
    ])
    return InContainerBuildSequence(
        config=config,
        steps=steps,
        buildername=buildername
    )