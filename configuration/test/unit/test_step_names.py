"""buildbot stores step names in steps.name, a VARCHAR(50).

Overflowing it raises DataError(1406) when the step row is inserted, i.e.
partway through a build rather than at config time, so BaseStep checks the
length up front. These tests pin that check and the two places a name grows
after it is first set.
"""

import pathlib
import unittest

from configuration.steps.base import BaseStep
from configuration.steps.commands.base import Command
from configuration.steps.commands.infra import ContainerCommit
from configuration.steps.remote import PropFromShellStep, ShellStep

LIMIT = BaseStep.MAX_NAME_LENGTH


class _StubCommand(Command):
    # Deliberately not a real command: the ones in commands/download.py and
    # commands/foundry.py import utils -> constants, which read os.environ at
    # import time and so are unavailable to a bare unit test run.
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
        """A checkpointed step generates a second step, "Checkpoint <name>",
        so its real budget is 11 characters smaller."""
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
