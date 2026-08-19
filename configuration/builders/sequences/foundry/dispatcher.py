from configuration.builders.infra.runtime import BuildSequence
from configuration.steps.commands import trigger


def trigger_foundry(trigger_specs):
    # trigger_specs: list of (schedulername, properties) pairs -- see
    # configuration/builders/definitions/foundry/builders.py for how the
    # MariaDB-version/package matrix is turned into this list.
    sequence = BuildSequence()
    sequence.add_step(trigger.FoundryDispatch(trigger_specs))
    return sequence
