import os

from buildbot.plugins import util
from configuration.steps.base import Command, CommandOptions
from utils import read_template

class UnpackTarball(Command):
    def __init__(self, workdir: str, options: CommandOptions = None):
        if options is None:
            options = CommandOptions()
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
    

class FetchCompat(Command):
    def __init__(self, workdir: str, rpm_type: str, arch: str, url: str, options: CommandOptions = None):
        if options is None:
            options = CommandOptions()
        super().__init__(name='Fetch MariaDB compat RPMs',
                         workdir=workdir,
                         options=options)
        self.rpm_type = rpm_type
        self.arch = arch
        self.url = url

    def as_cmd_arg(self) -> list[str]:
        return [
            'bash',
            '-ec',
            util.Interpolate(
                f'ls -l && ls -l ../ && wget --no-check-certificate -cO MariaDB-shared-5.3.{self.arch}.rpm "{self.url}/helper_files/mariadb-shared-5.3-{self.arch}.rpm" && wget -cO MariaDB-shared-10.1.{self.arch}.rpm "%(kw:url)s/helper_files/mariadb-shared-10.1-kvm-rpm-{self.rpm_type}-{self.arch}.rpm"',
            ),
        ]
