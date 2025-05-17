from buildbot.plugins import steps
from configuration.steps.base import StepOptions, BaseStep
from configuration.steps.commands.base import Command


class ShellStep(BaseStep):
    def __init__(
        self,
        command: Command,
        options: StepOptions = None,
        interrupt_signal="TERM",
        env_vars: list[tuple] = None,
    ):
        if env_vars is None:
            env_vars = []
        self.command = command
        self.interrupt_signal = interrupt_signal
        self.env_vars = env_vars
        assert isinstance(command, Command)
        super().__init__(command.name, options)
        self.prefix_cmd = []

    def generate(self):
        self._set_workdir()
        return steps.ShellCommand(
            name=self.name,
            command=[*self.prefix_cmd, *self.command.as_cmd_arg()],
            interruptSignal=self.interrupt_signal,
            **self.options.getopt,
            workdir=self.workdir,
        )
    
    def _set_workdir(self):
        # Assume it's a docker environment and default to worker build dir
        # because docker will set the workdir via -w to the running container
        self.workdir = "build"
        # Running on the worker host requires changing the workdir
        if not self.run_in_container:
            if self.command.workdir.is_absolute():
                self.workdir = self.command.workdir
            else:
                self.workdir = "build" / self.command.workdir


class PropFromShellStep(ShellStep):
    def __init__(
        self,
        command: Command,
        property,
        options: StepOptions = None,
        interrupt_signal="TERM",
        env_vars: list[tuple] = None,
    ):
        self.property = property
        super().__init__(
            command=command,
            options=options,
            interrupt_signal=interrupt_signal,
            env_vars=env_vars,
        )

    def generate(self):
        self._set_workdir()
        return steps.SetPropertyFromCommand(
            name=self.name,
            command=[*self.prefix_cmd, *self.command.as_cmd_arg()],
            interruptSignal=self.interrupt_signal,
            property=self.property,
            **self.options.getopt,
            workdir=self.workdir,
        )
