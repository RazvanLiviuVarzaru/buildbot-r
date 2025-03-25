from buildbot.plugins import util

from configuration.steps.base import Command, CommandOptions


class CreateDebRepo:
    pass


class CreateRpmRepo(Command):
    def __init__(
        self,
        rpm_type,
        url,
        options: CommandOptions = None,
        workdir: str = "",
    ):
        name = "MariaDB - Create local RPM repository"
        if options is None:
            options = CommandOptions()
        super().__init__(name=name, workdir=workdir, options=options)
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


class SaveRpmPackages(Command):
    def __init__(
        self,
        rpm_type,
        url,
        options: CommandOptions = None,
        workdir: str = "",
    ):
        name = "MariaDB - Save RPM packages"
        if options is None:
            options = CommandOptions()
        super().__init__(name=name, workdir=workdir, options=options)

    def as_cmd_arg(self) -> list[str]:
        result = [
            "bash",
            "-ec",
            util.Interpolate(
                f"""
                mkdir -p /packages/%(prop:tarbuildnum)s/%(prop:buildername)s &&
                cp -r MariaDB.repo rpms srpms /packages/%(prop:tarbuildnum)s/%(prop:buildername)s/ &&
                ln -sf %(prop:tarbuildnum)s/%(prop:buildername)s/MariaDB.repo /packages/%(prop:branch)s-latest-%(prop:buildername)s.repo &&
                sync /packages/%(prop:tarbuildnum)s
                    """,
            ),
        ]
        return result
