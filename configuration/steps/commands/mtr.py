from dataclasses import dataclass

from buildbot.plugins import util

from configuration.steps.commands.base import Command
from configuration.steps.generators.mtr.generator import MTRGenerator
from configuration.steps.generators.mtr.options import (
    MTR,
    SUITE,
    MTROption,
    TestSuiteCollection,
)


class MTRTest(Command):
    def __init__(self, name: str, testcase: MTRGenerator, workdir: str = "mysql-test"):
        name = f"MTR - {name}"
        super().__init__(name=name, workdir=workdir)
        assert isinstance(testcase, MTRGenerator)
        self.testcase = testcase

    def as_cmd_arg(self) -> list[str]:
        return self.testcase.generate()


class ArchiveLogs(Command):
    def __init__(
        self,
        workdir: str = "",
        logs: list[str] = ["*.log", "*.err", "core*"],
        archive_name: str = "logs.tar.gz",
        destination: str = "",
    ):
        name = "Archive and save logs"
        self.logs = logs
        self.archive_name = archive_name
        self.destination = destination
        super().__init__(name=name, workdir=workdir)

    def as_cmd_arg(self) -> list[str]:
        patterns = " -o ".join([f'-iname "{log}"' for log in self.logs])
        result = [
            "bash",
            "-ec",
            util.Interpolate(
                f"""
            mkdir -p {self.destination}
            find . -type f \( {patterns} \) -print0 | tar --null -czvf {self.destination}/{self.archive_name} --files-from=-;
            """,
            ),
        ]
        return result
