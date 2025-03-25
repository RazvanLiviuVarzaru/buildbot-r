from buildbot.plugins import util

from configuration.steps.base import Command, CommandOptions


class CompileMakeCommand(Command):
    def __init__(self, verbose: bool = False, include_package: bool = False, workdir: str = "", options: CommandOptions = None):
        self.include_package = include_package
        self.verbose = verbose
        if options is None:
            options = CommandOptions()
        name = "Compile - package" if self.include_package else "Compile"
        super().__init__(name=name, workdir=workdir, options=options)

    def as_cmd_arg(self) -> list[str]:
        result = [
            "make",
            f"VERBOSE={1 if self.verbose else 0}",
            util.Interpolate("-j%s", util.Property("jobs", default="33")),
        ]
        if self.include_package:
            result.append("package")
        return result


class CompileCMakeCommand(Command):
    def __init__(self, verbose: bool, workdir: str = ""):
        self.verbose = verbose
        super().__init__(name="Compile", workdir=workdir)

    def as_cmd_arg(self) -> list[str]:
        return [
            "cmake",
            "--build" "--verbose" if self.verbose else "",
            "--parallel",
            util.Interpolate("j%(prop:jobs)"),
        ]


class CompileDebAutobake(Command):
    # TODO(cvicentiu) Implement this for Debian Autobake
    def __init__(self): ...


class CompileRpmAutobake(Command):
    def __init__(
        self,
        options: CommandOptions = None,
        workdir: str = "",
    ):
        name = "MariaDB - Make Package"
        if options is None:
            options = CommandOptions()
        super().__init__(name=name, workdir=workdir, options=options)

    def as_cmd_arg(self) -> list[str]:
        # result = [
        #     'bash',
        #     '-ec'
        #     ,util.Interpolate(
        #             f"""
        #             mkdir -p rpms srpms
        #             if grep -qw CPACK_RPM_SOURCE_PKG_BUILD_PARAMS CPackSourceConfig.cmake; then
        #                 make package_source
        #                 mv *.src.rpm srpms/
        #             fi
        #             export PATH=/usr/lib/ccache:/usr/lib64/ccache:$PATH && make -j %(kw:jobs)s package
        #             """,
        #             jobs=util.Property("jobs", default="$(getconf _NPROCESSORS_ONLN)"),
        #         ),
        # ]
        result = [
            "bash",
            "-ec",
            util.Interpolate(
                f"""
                    mkdir -p rpms srpms
                    wget https://mirror.mariadb.org/yum/11.4/centos/9/x86_64/rpms/MariaDB-backup-11.4.5-1.el9.x86_64.rpm && wget https://mirror.mariadb.org/yum/11.4/centos/9/x86_64/rpms/MariaDB-columnstore-cmapi-11.2.1_23.10.0-1.el9.x86_64.rpm
                    cd srpms && wget https://mirror.mariadb.org/yum/11.4/centos/9/x86_64/srpms/MariaDB-11.4.5-1.el9.src.rpm
                    """,
                jobs=util.Property("jobs", default="$(getconf _NPROCESSORS_ONLN)"),
            ),
        ]
        return result
