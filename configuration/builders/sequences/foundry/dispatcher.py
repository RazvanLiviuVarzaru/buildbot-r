from configuration.builders.infra.runtime import (
    BuildSequence,
    DockerConfig,
    InContainer,
)
from configuration.steps.remote import PropFromShellStep, ShellStep
from configuration.steps.commands.util import PrintEnvironmentDetails



def trigger_foundry():
    sequence = BuildSequence()
    sequence.add_step(ShellStep(command=PrintEnvironmentDetails()))
    return sequence
