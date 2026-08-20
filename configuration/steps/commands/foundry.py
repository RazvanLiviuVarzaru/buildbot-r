from pathlib import PurePath

from buildbot.plugins import util
from configuration.steps.commands.base import Command


class BuildPlugin(Command):
    # package_type: "RPM" or "DEB" -- the -D flag run.cmake expects.
    def __init__(self, package_type: str, workdir: PurePath = PurePath(".")):
        self.package_type = package_type
        super().__init__(name=f"Build plugin ({package_type})", workdir=workdir)

    def as_cmd_arg(self) -> list[str]:
        return [
            "bash",
            "-exc",
            util.Interpolate(f"cmake -D{self.package_type}=1 -P run.cmake %(prop:plugin)s"),
        ]
