from buildbot.plugins import util
from .base_step import Command, CommandOptions
from utils import read_template

class UnpackTarball(Command):
    def __init__(self, workdir: str, options: CommandOptions):
        super().__init__(name='Fetch Source Tarball',
                         workdir=workdir,
                         options=options)
        self.name = 'Unpack Source Tarball'

    def as_cmd_arg(self) -> list[str]:
        return [
            'bash',
            '-ec',
            util.Interpolate(read_template("get_tarball")),
        ]
