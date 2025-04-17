from abc import ABC, abstractmethod
from collections import namedtuple
from dataclasses import dataclass
from typing import Optional

from configuration.steps.commands.base import Command


@dataclass
class StepOptions:  # all step (shell, compile, etc) types support these options
    # Default : safety first
    alwaysRun: bool = False
    haltOnFailure: bool = True
    doStepIf: callable = lambda _: True

    @property
    def getopt(self):
        Options = namedtuple("Options", ["alwaysRun", "haltOnFailure", "doStepIf"])
        return Options(self.alwaysRun, self.haltOnFailure, self.doStepIf)._asdict()


class BaseStep(ABC):
    def __init__(self, name: str, options: Optional[StepOptions] = None):
        self.name = name
        # Only classes that can implement steps capable of running in a
        # container should accept *container* options as constructor arguments
        self.run_in_container = False
        self.container_commit = False
        self.options = options
        if self.options is None:
            self.options = StepOptions()  # Load default options
        assert isinstance(self.options, StepOptions)

    @abstractmethod
    def generate(self): ...


class PrefixableStep(BaseStep):
    def __init__(self, name: str, options: StepOptions, env_vars: list[tuple]):
        self.env_vars = env_vars
        super().__init__(name, options)

    @abstractmethod
    def add_cmd_prefix(self, command: Command): ...
