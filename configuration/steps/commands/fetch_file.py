from buildbot.plugins import util

from configuration.steps.commands.base import Command
from utils import read_template


class UnpackTarball(Command):
    def __init__(self, workdir: str):
        super().__init__(name = "Download and unpack source tarball",workdir=workdir)
    def as_cmd_arg(self) -> list[str]:
        return [
            "bash",
            "-ec",
            util.Interpolate(read_template("get_tarball")),
        ]

# TODO (Razvan) WIP
class FetchCompat(Command):
    def __init__(
        self,
        workdir: str,
        rpm_type: str,
        arch: str,
        url: str,
    ):
        super().__init__(
            name="Fetch MariaDB compat RPMs", workdir=workdir
        )
        self.rpm_type = rpm_type
        self.arch = arch
        self.url = url

    def as_cmd_arg(self) -> list[str]:
        return [
            "bash",
            "-ec",
            util.Interpolate(
                f'ls -l && ls -l ../ && wget --no-check-certificate -cO MariaDB-shared-5.3.{self.arch}.rpm "{self.url}/helper_files/mariadb-shared-5.3-{self.arch}.rpm" && wget -cO MariaDB-shared-10.1.{self.arch}.rpm "%(kw:url)s/helper_files/mariadb-shared-10.1-kvm-rpm-{self.rpm_type}-{self.arch}.rpm"',
            ),
        ]


class SimpleTouchFile(Command):
    def __init__(self, filename: str, workdir: str):
        super().__init__(name=filename, workdir=workdir)
        self.filename = filename

    def as_cmd_arg(self) -> list[str]:
        return ["bash", "-c", f"ls -l && touch {self.filename}"]