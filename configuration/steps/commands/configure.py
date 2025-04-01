from buildbot import interfaces, steps
from buildbot.plugins import util

from configuration.steps.commands.base import Command
from configuration.steps.generators.cmake.compilers import CompilerCommand
from configuration.steps.generators.cmake.generator import CMakeGenerator
from configuration.steps.generators.cmake.options import CMAKE, BuildType, CMakeOption


class ConfigureMariaDBCMake(Command):
    def __init__(self, name: str, cmake_generator: CMakeGenerator, workdir: str = ""):
        self.cmake_generator = cmake_generator
        super().__init__(name=f"Configure - {name}", workdir=workdir)

    def as_cmd_arg(self) -> list[str]:
        return self.cmake_generator.generate()

