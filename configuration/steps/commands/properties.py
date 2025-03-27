from buildbot.plugins import util

from configuration.steps.commands.base import Command


class hasRpmPackages(Command):
    def __init__(self, workdir: str = ""):
        name = "Set Packages property"
        super().__init__(name=name, workdir=workdir)

    def as_cmd_arg(self) -> list[str]:
        return [
            "bash",
            "-ec",
            util.Interpolate(
                "ls -1 *.txt",
            ),
        ]
