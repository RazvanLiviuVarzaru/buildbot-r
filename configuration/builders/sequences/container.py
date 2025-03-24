from configuration.builders.infra.runtime import InContainerBuildSequence
from configuration.steps.generators.cmake.compilers import GCCCompiler
from configuration.steps.generators.cmake.generator import CMakeGenerator
from configuration.steps.generators.cmake.options import CMAKE, BuildType, CMakeOption
from configuration.steps.configure import ConfigureMariaDBCMake, ConfigureRpmAutoBakeCMake
from configuration.steps.compile import CompileMakeCommand, CompileRpmAutobake
from configuration.steps.properties import hasRpmPackages
from configuration.steps.fetch_file import UnpackTarball, FetchCompat
from configuration.steps.base import CommandOptions

def rpm_autobake(config, rpm_type, arch, url, has_compat = False):
    steps = []
    if has_compat:
        steps.append(FetchCompat(rpm_type=rpm_type, arch=arch, url=url, workdir=""))
    steps.append(UnpackTarball(workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX"))
    steps.append(ConfigureRpmAutoBakeCMake(workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX", rpm_type=rpm_type))
    steps.append(CompileRpmAutobake(workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX"))
    steps.append(hasRpmPackages(workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX"))
    return InContainerBuildSequence(
                config=config,
                steps=steps,
            #     steps=[
            #         FetchCompat(),
            #         UnpackTarball(, options=CommandOptions(haltOnFailure=True)),
            #         ConfigureRpmAutoBakeCMake(,options=CommandOptions(haltOnFailure=True, doStepIf=lambda _: True)),
            #         # CompileRpmAutobakeStep(options=CommandOptions(haltOnFailure=True, doStepIf=lambda _: True), workdir="ceva/test"),
            #         # CompileRpmAutobakeStep(options=CommandOptions(haltOnFailure=True, doStepIf=lambda _: True), workdir="altceva/test"),
            #         # MTR Step
            #         # MTRTest(type=MTRTest.Normal),
            #         # MTRTest(type=MTRTest.Galera),
            #         # MTRTest(type=MTRTest.S3),
            #         # MTRTest(type=MTRTest.RocksDB),
            #         # MTRTest(type=MTRTest.OptimizerTrace),
            #         # SavePackages(),
            # ]
        )
