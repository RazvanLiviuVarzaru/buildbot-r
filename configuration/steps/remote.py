from configuration.steps.base import BaseStep, StepOptions, PrefixableStep
from configuration.steps.commands.base import Command
from buildbot.plugins import steps


class ShellStep(PrefixableStep):
    def __init__(self, command: Command, options: StepOptions = None, interruptSignal="TERM"):
        self.command = command
        self.interruptSignal = interruptSignal
        assert isinstance(command, Command)
        super().__init__(command.name, options)
        self.prefix_cmd = []

    def add_cmd_prefix(self, command):
        self.prefix_cmd.extend(command)

    def generate(self):
        return steps.ShellCommand(
                name=self.name,
                command = [*self.prefix_cmd, *self.command.as_cmd_arg()],
                interruptSignal=self.interruptSignal,
                **self.options.getopt,
            )
    
class PropFromShellStep(PrefixableStep):
    def __init__(self, command: Command,extract_fn, options: StepOptions = None, interruptSignal="TERM"):
        self.command = command
        self.interruptSignal = interruptSignal
        self.extract_fn = extract_fn
        assert isinstance(command, Command)
        super().__init__(command.name, options)
        self.prefix_cmd = []

    def add_cmd_prefix(self, command):
        self.prefix_cmd.extend(command)

    def generate(self):
        return steps.SetPropertyFromCommand(
                name=self.name,
                command = [*self.prefix_cmd, *self.command.as_cmd_arg()],
                interruptSignal=self.interruptSignal,
                extract_fn=self.extract_fn,
                **self.options.getopt,
            )
# Supports checkpointing
class DockerShellStep(ShellStep):
    def __init__(self, command: Command, options: StepOptions = None, interruptSignal="TERM", checkpoint:bool=False):
        self.checkpoint = checkpoint
        super().__init__(command, options, interruptSignal)
        

