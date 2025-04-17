from buildbot.plugins import steps
from configuration.steps.base import PrefixableStep, StepOptions
from configuration.steps.commands.base import Command


class ShellStep(PrefixableStep):
    def __init__(
        self,
        command: Command,
        options: StepOptions = None,
        interrupt_signal="TERM",
        env_vars: list[tuple] = None,
        run_in_container: bool = False,
        container_commit: bool = False,
    ):
        if env_vars is None:
            env_vars = []
        self.command = command
        self.interrupt_signal = interrupt_signal
        assert isinstance(command, Command)
        super().__init__(command.name, options, env_vars=env_vars)
        self.run_in_container = run_in_container
        self.container_commit = container_commit
        self.prefix_cmd = []

    def add_cmd_prefix(self, command):
        self.prefix_cmd.extend(command)

    def generate(self):
        return steps.ShellCommand(
            name=self.name,
            command=[*self.prefix_cmd, *self.command.as_cmd_arg()],
            interruptSignal=self.interrupt_signal,
            **self.options.getopt,
        )


class PropFromShellStep(PrefixableStep):
    def __init__(
        self,
        command: Command,
        property,
        options: StepOptions = None,
        interrupt_signal="TERM",
        env_vars: list[tuple] = None,
        run_in_container: bool = False,
        container_commit: bool = False,
    ):
        if env_vars is None:
            env_vars = []
        self.command = command
        self.interrupt_signal = interrupt_signal
        self.property = property
        assert isinstance(command, Command)
        name = f"Set {self.property} from {command.name}"
        super().__init__(name, options, env_vars=env_vars)
        self.run_in_container = run_in_container
        self.container_commit = container_commit
        self.prefix_cmd = []

    def add_cmd_prefix(self, command):
        self.prefix_cmd.extend(command)

    def generate(self):
        return steps.SetPropertyFromCommand(
            name=self.name,
            command=[*self.prefix_cmd, *self.command.as_cmd_arg()],
            interruptSignal=self.interrupt_signal,
            property=self.property,
            **self.options.getopt,
        )
