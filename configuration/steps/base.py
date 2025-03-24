from abc import ABC, abstractmethod
from collections import namedtuple
from dataclasses import dataclass

@dataclass
class CommandOptions: # all step (shell, compile, etc) types support these options
    # Default : safety first
    alwaysRun: bool = False
    haltOnFailure: bool = True
    doStepIf: callable = lambda _: True

    @property
    def options(self):
        Options = namedtuple('Options', ['alwaysRun', 'haltOnFailure', 'doStepIf'])
        return Options(self.alwaysRun, self.haltOnFailure, self.doStepIf)._asdict()


class Command(ABC):
    def __init__(self, name: str, workdir: str, options: CommandOptions):
        self.name = name
        self.workdir = workdir
        assert isinstance(options, CommandOptions)
        self.options = options.options
        self.user = 'buildbot' # All commands run as buildbot user by default

    @abstractmethod
    def as_cmd_arg(self) -> list[str]:
        pass

    def as_build_property(self):
        pass
