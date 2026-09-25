"""BaseStep's check of the 50 characters buildbot stores per step name,
including the names derived from it."""

import pathlib
import unittest

from configuration.steps.base import BaseStep
from configuration.steps.commands.base import Command
from configuration.steps.commands.infra import ContainerCommit
from configuration.steps.remote import PropFromShellStep, ShellStep

LIMIT = BaseStep.MAX_NAME_LENGTH


class _StubCommand(Command):
    # Not a real command: some, like commands/download.py's, import utils,
    # which needs the master's environment.
    def __init__(self, name):
        super().__init__(name=name, workdir=pathlib.PurePath("."))

    def as_cmd_arg(self) -> list:
        return ["true"]


class TestStepNameLimit(unittest.TestCase):
    def test_matches_the_database_column(self):
        from buildbot.db.model import Model

        self.assertEqual(Model.steps.c.name.type.length, LIMIT)

    def test_accepts_a_name_at_the_limit(self):
        step = ShellStep(command=_StubCommand("x" * LIMIT))
        self.assertEqual(len(step.name), LIMIT)

    def test_rejects_a_longer_name(self):
        with self.assertRaises(ValueError) as caught:
            ShellStep(command=_StubCommand("x" * (LIMIT + 1)))
        self.assertIn(str(LIMIT + 1), str(caught.exception))

    def test_rejects_the_checkpoint_name(self):
        """A checkpointed step adds a "Checkpoint <name>" step."""
        name = "x" * (LIMIT - 10)
        ShellStep(command=_StubCommand(name))  # fits on its own
        with self.assertRaises(ValueError):
            ShellStep(
                command=ContainerCommit(
                    container_name="c", runtime_tag="t", step_name=name
                )
            )

    def test_rejects_the_property_name(self):
        """PropFromShellStep renames to "Set <property> from <name>"."""
        name = "x" * (LIMIT - 10)
        ShellStep(command=_StubCommand(name))  # fits on its own
        with self.assertRaises(ValueError):
            PropFromShellStep(command=_StubCommand(name), property="some_property")


if __name__ == "__main__":
    unittest.main()
