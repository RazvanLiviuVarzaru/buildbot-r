from buildbot.plugins import util

from configuration.steps.commands.base import Command


class CompileMakeCommand(Command):
    def __init__(self, verbose: bool = False, include_package: bool = False, workdir: str = ""):
        self.include_package = include_package
        self.verbose = verbose
        name = "Compile - package" if self.include_package else "Compile"
        super().__init__(name=name, workdir=workdir)

    def as_cmd_arg(self) -> list[str]:
        result = [
            "make",
            util.Interpolate("-j%s", util.Property("jobs", default="33")),
        ]
        if self.verbose:
            result.insert(1, "VERBOSE=1") # VERBOSE=0 does not disable verbose output
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


# TODO (Razvan) Use multiple steps and leverage existing classes for MAKE
class CompileRpmAutobake(Command):
    def __init__(
        self,
        workdir: str = "",
    ):
        name = "Make Package"
        super().__init__(name=name, workdir=workdir)

    def as_cmd_arg(self) -> list[str]:
        result = [
            'bash',
            '-ec'
            ,util.Interpolate(
                    f"""
                    mkdir -p rpms srpms
                    if grep -qw CPACK_RPM_SOURCE_PKG_BUILD_PARAMS CPackSourceConfig.cmake; then
                        make package_source
                        mv *.src.rpm srpms/
                    fi
                    export PATH=/usr/lib/ccache:/usr/lib64/ccache:$PATH && make -j %(kw:jobs)s package
                    """,
                    jobs=util.Property("jobs", default="$(getconf _NPROCESSORS_ONLN)"),
                ),
        ]
        return result
