from buildbot import interfaces, steps
from buildbot.plugins import util

from .base_step import Command, CommandOptions
from .cmake.options import CMakeOption, BuildType, CMAKE
from .cmake.compilers import CompilerCommand
from .cmake.generator import CMakeGenerator


class ConfigureMariaDBCMake(Command):
    def __init__(self,
                 name: str,
                 cmake_generator: CMakeGenerator,
                 workdir: str = ''):
        self.cmake_generator = cmake_generator
        super().__init__(name=f'Configure MariaDB Server - {name}',
                         workdir=workdir)

    def as_cmd_arg(self) -> list[str]:
        return self.cmake_generator.generate()


def simple_debug_conf(compiler: CompilerCommand = None,
                      use_ccache: bool = False,
                      workdir: str = '') -> ConfigureMariaDBCMake:
    return ConfigureMariaDBCMake(
        name='Debug Build',
        cmake_generator=CMakeGenerator(
            compiler=compiler,
            use_ccache=use_ccache,
            flags=[
                CMakeOption(CMAKE.BUILD_TYPE, BuildType.DEBUG),
            ]),
        workdir=workdir)

class ConfigureRpmAutoBakeCMake(Command):
    def __init__(self,options: CommandOptions,workdir: str = '', ):
        name = 'Configure'
        super().__init__(name=name, workdir=workdir, options=options)

    def as_cmd_arg(self) -> list[str]:
        result = [
            'bash',
            '-ec'
            ,util.Interpolate(
                    """
                    export PATH=/usr/lib/ccache:/usr/lib64/ccache:$PATH && cmake . \\
                        -DBUILD_CONFIG=mysql_release \\
                        -DRPM=%(prop:rpm_type)s \\
                        -DCMAKE_C_COMPILER_LAUNCHER=ccache \\
                        -DCMAKE_CXX_COMPILER_LAUNCHER=ccache
                    """,
                    jobs=util.Property("jobs", default="$(getconf _NPROCESSORS_ONLN)"),
                ),
        ]
        return result
