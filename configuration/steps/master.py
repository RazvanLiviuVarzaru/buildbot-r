from buildbot.plugins import steps
from configuration.steps.base import PrefixableStep, StepOptions
from configuration.steps.commands.base import Command


class MasterShellStep(PrefixableStep):
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
        assert isinstance(command, Command)
        super().__init__(command.name, options, env_vars=env_vars)
        self.prefix_cmd = []

    def add_cmd_prefix(self, command):
        self.prefix_cmd.extend(command)

    def generate(self):
        return steps.MasterShellCommand(
            name=self.name,
            command=[*self.prefix_cmd, *self.command.as_cmd_arg()],
            interruptSignal=self.interrupt_signal,
            **self.options.getopt,
        )
