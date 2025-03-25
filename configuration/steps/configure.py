from buildbot import interfaces, steps
from buildbot.plugins import util

from configuration.steps.base import Command, CommandOptions
from configuration.steps.generators.cmake.compilers import CompilerCommand
from configuration.steps.generators.cmake.generator import CMakeGenerator
from configuration.steps.generators.cmake.options import CMAKE, BuildType, CMakeOption


class ConfigureMariaDBCMake(Command):
    def __init__(self, name: str, cmake_generator: CMakeGenerator, workdir: str = "", options: CommandOptions = None):
        self.cmake_generator = cmake_generator
        if options is None:
            options = CommandOptions()
        super().__init__(name=f"Configure MariaDB Server - {name}", workdir=workdir, options=options)

    def as_cmd_arg(self) -> list[str]:
        return self.cmake_generator.generate()


class ConfigureRpmAutoBakeCMake(Command):
    def __init__(
        self,
        rpm_type,
        options: CommandOptions = None,
        workdir: str = "",
    ):
        name = "MariaDB - Configure"
        self.rpm_type = rpm_type
        if options is None:
            options = CommandOptions()
        super().__init__(name=name, workdir=workdir, options=options)

    def as_cmd_arg(self) -> list[str]:
        result = [
            "bash",
            "-ec",
            util.Interpolate(
                f"""
                    export PATH=/usr/lib/ccache:/usr/lib64/ccache:$PATH && cmake . \\
                        -DBUILD_CONFIG=mysql_release \\
                        -DRPM={self.rpm_type} \\
                        -DCMAKE_C_COMPILER_LAUNCHER=ccache \\
                        -DCMAKE_CXX_COMPILER_LAUNCHER=ccache
                    """,
                jobs=util.Property("jobs", default="$(getconf _NPROCESSORS_ONLN)"),
            ),
        ]
        return result
