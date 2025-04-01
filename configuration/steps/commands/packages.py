from buildbot.plugins import util

from configuration.steps.base import Command


class CreateDebRepo:
    pass

# TODO (Razvan):This is a copy-paste only to showcase a full factory. Re-work needed.
class CreateRpmRepo(Command):
    def __init__(
        self,
        rpm_type,
        url,
        workdir: str = "",
    ):
        name = "Create local RPM repository"
        super().__init__(name=name, workdir=workdir)
        self.rpm_type = rpm_type
        self.url = url

    def as_cmd_arg(self) -> list[str]:
        result = [
            "bash",
            "-ec",
            util.Interpolate(
                f"""
                if [ -e MariaDB-shared-10.1.*.rpm ]; then
                rm MariaDB-shared-10.1.*.rpm
                fi
                mkdir -p rpms srpms
                mv *.src.rpm srpms/
                mv *.rpm rpms/
                createrepo rpms/
                cat << EOF > MariaDB.repo
    [MariaDB-%(prop:branch)s]
    name=MariaDB %(prop:branch)s repo (build %(prop:tarbuildnum)s)
    baseurl={self.url}/%(prop:tarbuildnum)s/%(prop:buildername)s/rpms
    gpgcheck=0
    EOF
                if [ "{self.rpm_type}" = rhel8 ] || [ "{self.rpm_type}" = centosstream8 ] || [ "{self.rpm_type}" = almalinux8 ] || [ "{self.rpm_type}" = rockylinux8 ]; then
                    echo "module_hotfixes = 1" >> MariaDB.repo
                fi
                    """,
            ),
        ]
        return result
    

class SavePackages(Command):
    """
    This class is used to recursively copy a list of files and dirs to CI,
    starting from the current working directory and
    assuming that /packages is bind mounted.
    """
    def __init__(
        self,
        packages: list[str],
        workdir: str = "",
        destination: str  = "/packages/%(prop:tarbuildnum)s/%(prop:buildername)s"
    ):
        name = "Save packages"
        self.packages = packages
        self.destination = destination
        super().__init__(name=name, workdir=workdir)

    def as_cmd_arg(self) -> list[str]:
        package_list = " ".join(self.packages)
        result = [
            "bash",
            "-ec",
            util.Interpolate(
            f"""
                mkdir -p {self.destination} &&
                cp -r {package_list} {self.destination}
                """,
            ),
        ]
        return result
