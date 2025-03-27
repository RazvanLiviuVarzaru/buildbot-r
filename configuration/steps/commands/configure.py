from buildbot import interfaces, steps
from buildbot.plugins import util

from configuration.steps.commands.base import Command
from configuration.steps.generators.cmake.compilers import CompilerCommand
from configuration.steps.generators.cmake.generator import CMakeGenerator
from configuration.steps.generators.cmake.options import CMAKE, BuildType, CMakeOption


class ConfigureMariaDBCMake(Command):
    def __init__(self, name: str, cmake_generator: CMakeGenerator, workdir: str = ""):
        self.cmake_generator = cmake_generator
        super().__init__(name=f"Configure MariaDB Server - {name}", workdir=workdir)

    def as_cmd_arg(self) -> list[str]:
        return self.cmake_generator.generate()

# TODO (Razvan) Use multiple steps, use generator for CMAKE command
class ConfigureRpmAutoBakeCMake(Command):
    def __init__(
        self,
        rpm_type,
        workdir: str = "",
    ):
        name = "MariaDB - Configure"
        self.rpm_type = rpm_type
        super().__init__(name=name, workdir=workdir)

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
