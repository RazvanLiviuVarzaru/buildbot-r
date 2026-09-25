from abc import ABC, abstractmethod
from collections import namedtuple
from dataclasses import dataclass
from typing import Optional


@dataclass
class StepOptions:  # all step (shell, compile, etc) types support these options
    """
    Options for a build step.
    This class defines the options that can be applied to a build step,
    such as whether it should always run, halt on failure, and custom run conditions.
    Attributes:
        alwaysRun (bool): If True, the step will always run regardless of previous failures.
        haltOnFailure (bool): If True, the build will halt if this step fails.
        flunkOnWarnings (bool): If True, a step ending in WARNINGS fails the
            build, which carries on; the step itself stays a warning.
        doStepIf (callable): A callable that determines if the step should be executed.
    """

    # Default : safety first
    alwaysRun: bool = False
    haltOnFailure: bool = True
    flunkOnWarnings: bool = False
    doStepIf: callable = lambda _: True
    description: str = None
    descriptionDone: str = None

    @property
    def getopt(self):
        return {
            key: value
            for key, value in self.__dict__.items()
            if not key.startswith("_") and value is not None
        }


class BaseStep(ABC):
    # buildbot stores step names in a VARCHAR(50) and only rejects a longer
    # one mid-build, so check at config time. Derived names count too:
    # "Checkpoint <name>" and PropFromShellStep's "Set <property> from <name>".
    MAX_NAME_LENGTH = 50

    def __init__(self, name: str, options: Optional[StepOptions] = None):
        self.name = name
        self.options = options
        if self.options is None:
            self.options = StepOptions()  # Load default options
        assert isinstance(self.options, StepOptions)

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        # A setter, as PropFromShellStep renames the step after __init__.
        if isinstance(value, str) and len(value) > self.MAX_NAME_LENGTH:
            raise ValueError(
                f"step name is {len(value)} characters, over the "
                f"{self.MAX_NAME_LENGTH} buildbot stores: {value!r}"
            )
        self._name = value

    @abstractmethod
    def generate(self): ...
