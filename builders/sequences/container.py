from builders.infra.runtime import InContainerBuildSequence
from steps.cmake.compilers import GCCCompiler
from steps.cmake.generator import CMakeGenerator
from steps.cmake.options import CMAKE, BuildType, CMakeOption
from steps.configure import ConfigureMariaDBCMake
from steps.compile import CompileMakeCommand
from steps.fetch_file import FetchTarball

def rpm_autobake(config):
    return InContainerBuildSequence(
                config=config,
                steps=[
                    FetchTarball('https://ci.mariadb.org', "here"),
                    ConfigureMariaDBCMake(
                        'Debug Build',
                        cmake_generator=CMakeGenerator(flags=[]),
                        # cmake_generator=CMakeGenerator(
                        #     compiler=GCCCompiler(),
                        #     use_ccache=True,
                        #     flags=[
                        #         CMakeOption(CMAKE.BUILD_TYPE, BuildType.DEBUG),
                        #     ]),
                    ),
                    CompileMakeCommand(verbose=True, include_package=True),
                    # MTR Step
                    # MTRTest(type=MTRTest.Normal),
                    # MTRTest(type=MTRTest.Galera),
                    # MTRTest(type=MTRTest.S3),
                    # MTRTest(type=MTRTest.RocksDB),
                    # MTRTest(type=MTRTest.OptimizerTrace),
                    # SavePackages(),
            ])
