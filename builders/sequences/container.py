from builders.infra.runtime import InContainerBuildSequence
from steps.cmake.compilers import GCCCompiler
from steps.cmake.generator import CMakeGenerator
from steps.cmake.options import CMAKE, BuildType, CMakeOption
from steps.configure import ConfigureMariaDBCMake, ConfigureRpmAutoBakeCMake
from steps.compile import CompileMakeCommand, CompileRpmAutobakeStep
from steps.fetch_file import UnpackTarball
from steps.base_step import CommandOptions

def rpm_autobake(config):
    return InContainerBuildSequence(
                config=config,
                steps=[
                    UnpackTarball(workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX", options=CommandOptions(haltOnFailure=True)),
                    ConfigureRpmAutoBakeCMake(workdir="padding_for_CPACK_RPM_BUILD_SOURCE_DIRS_PREFIX",options=CommandOptions(haltOnFailure=True, doStepIf=lambda _: True)),
                    # CompileRpmAutobakeStep(options=CommandOptions(haltOnFailure=True, doStepIf=lambda _: True), workdir="ceva/test"),
                    # CompileRpmAutobakeStep(options=CommandOptions(haltOnFailure=True, doStepIf=lambda _: True), workdir="altceva/test"),
                    # MTR Step
                    # MTRTest(type=MTRTest.Normal),
                    # MTRTest(type=MTRTest.Galera),
                    # MTRTest(type=MTRTest.S3),
                    # MTRTest(type=MTRTest.RocksDB),
                    # MTRTest(type=MTRTest.OptimizerTrace),
                    # SavePackages(),
            ])
