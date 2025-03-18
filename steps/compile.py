from buildbot.plugins import util

from .base_step import Command, CommandOptions


class CompileMakeCommand(Command):
    def __init__(self, verbose: bool, include_package: bool, workdir: str = ''):
        self.include_package = include_package
        self.verbose = verbose
        name = 'Compile - package' if self.include_package else 'Compile'
        super().__init__(name=name, workdir=workdir)

    def as_cmd_arg(self) -> list[str]:
        result = [
            'make',
            f'VERBOSE={1 if self.verbose else 0}',
            util.Interpolate('-j%s', util.Property('jobs', default='33')),
        ]
        if self.include_package:
            result.append('package')
        return result


class CompileCMakeCommand(Command):
    def __init__(self, verbose: bool, workdir: str = ''):
        self.verbose = verbose
        super().__init__(name='Compile', workdir=workdir)

    def as_cmd_arg(self) -> list[str]:
        return [
            'cmake',
            '--build'
            '--verbose' if self.verbose else '',
            '--parallel', util.Interpolate('j%(prop:jobs)'),
        ]


class CompileDebAutobakeStep(Command):
    # TODO(cvicentiu) Implement this for Debian Autobake
    def __init__(self):
        ...

class CompileRpmAutobakeStep(Command):
    def __init__(self,options: CommandOptions,workdir: str = '', ):
        name = 'Compile - package - source package'
        super().__init__(name=name, workdir=workdir, options=options)

    def as_cmd_arg(self) -> list[str]:
        # result = [
        #     'sh',
        #     '-xc'
        #     ,util.Interpolate(
        #             """
        #     mkdir -p rpms srpms
        #     if grep -qw CPACK_RPM_SOURCE_PKG_BUILD_PARAMS CPackSourceConfig.cmake; then
        #         make package_source
        #         mv *.src.rpm srpms/
        #     fi
        #     export PATH=/usr/lib/ccache:/usr/lib64/ccache:$PATH && make -j %(kw:jobs)s package
        # """,
        #             jobs=util.Property("jobs", default="$(getconf _NPROCESSORS_ONLN)"),
        #         ),
        # ]

        result = [
            'sh',
            '-xc'
            ,util.Interpolate(
                    """
            mkdir -p rpms srpms
            if [ 1 -eq 1 ]; then
                touch ceva.txt
            fi
            export PATH=/usr/lib/ccache:/usr/lib64/ccache:$PATH && touch test.txt && touch /packages/test2.txt
        """,
                    jobs=util.Property("jobs", default="$(getconf _NPROCESSORS_ONLN)"),
                ),
        ]
        return result