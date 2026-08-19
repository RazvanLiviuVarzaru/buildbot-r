from configuration.builders.base import GenericBuilder
from configuration.builders.sequences.foundry import dispatcher

DISPATCHER_BUILDER = GenericBuilder(
    name="foundry-trigger-builders",
    sequences=[dispatcher.trigger_foundry()],
)