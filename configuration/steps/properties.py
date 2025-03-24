

from buildbot.plugins import util

from configuration.steps.base import Command, CommandOptions
from utils import ls2string


class hasRpmPackages(Command):
    def __init__(self, options: CommandOptions = None, workdir: str = ''):
        name = 'MariaDB - Set has RPM packages'
        if options is None:
            options = CommandOptions()
        super().__init__(name=name, workdir=workdir, options=options)

    def as_cmd_arg(self) -> list[str]:
        return [
            "ls -1 *.rpm",
        ]
    
    def as_build_property(self):
        self.options["extract_fn"] = ls2string
        return True
