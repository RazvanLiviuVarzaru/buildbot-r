from configuration.builders.infra.runtime import (
    BuildSequence,
    DockerConfig,
    InContainer,
)
from configuration.steps.remote import PropFromShellStep, ShellStep
from configuration.steps.commands.util import PrintEnvironmentDetails

_MARIADB_VERSION_ENV = [("MARIADB_VERSION", "%(prop:mariadb_version)s")]


def deb():
    sequence = BuildSequence()
    sequence.add_step(
        ShellStep(command=PrintEnvironmentDetails(), env_vars=_MARIADB_VERSION_ENV)
    )
    return sequence


def rpm():
    sequence = BuildSequence()
    sequence.add_step(
        ShellStep(command=PrintEnvironmentDetails(), env_vars=_MARIADB_VERSION_ENV)
    )
    return sequence
