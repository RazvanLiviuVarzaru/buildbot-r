from configuration.builders.infra.runtime import (
    BuildSequence,
    DockerConfig,
    InContainer,
)
from configuration.steps.commands.download import GitInitFromCommit
from configuration.steps.commands.foundry import BuildPlugin
from configuration.steps.commands.packages import (
    InstallDEBPackages,
    InstallRPMPackages,
    SetupDEBRepoFromURL,
    SetupRPMRepoFromURL,
)
from configuration.steps.remote import ShellStep

_MARIADB_VERSION_ENV = [("MARIADB_VERSION", "%(prop:mariadb_version)s")]


def _clone_foundry_step(config: DockerConfig):
    return InContainer(
        ShellStep(
            # revision is always empty on foundry_force_scheduler, so fetch
            # the branch tip instead of a pinned commit.
            command=GitInitFromCommit(
                repo_url="%(prop:repository)s",
                commit="%(prop:branch)s",
            ),
        ),
        docker_environment=config,
    )


def deb(config: DockerConfig, repo_file_url: str):
    sequence = BuildSequence()
    sequence.add_step(_clone_foundry_step(config))
    sequence.add_step(
        InContainer(
            ShellStep(command=SetupDEBRepoFromURL(repo_file_url)),
            docker_environment=config,
            container_commit=True,
        )
    )
    sequence.add_step(
        InContainer(
            ShellStep(command=InstallDEBPackages(packages=["libmariadb-dev"])),
            docker_environment=config,
            container_commit=True,
        )
    )
    sequence.add_step(
        InContainer(
            ShellStep(command=BuildPlugin("DEB"), env_vars=_MARIADB_VERSION_ENV),
            docker_environment=config,
        )
    )
    return sequence


def rpm(config: DockerConfig, repo_file_url: str):
    sequence = BuildSequence()
    sequence.add_step(_clone_foundry_step(config))
    sequence.add_step(
        InContainer(
            ShellStep(command=SetupRPMRepoFromURL(repo_file_url)),
            docker_environment=config,
            container_commit=True,
        )
    )
    sequence.add_step(
        InContainer(
            ShellStep(command=InstallRPMPackages(packages=["MariaDB-devel"])),
            docker_environment=config,
            container_commit=True,
        )
    )
    sequence.add_step(
        InContainer(
            ShellStep(command=BuildPlugin("RPM"), env_vars=_MARIADB_VERSION_ENV),
            docker_environment=config,
        )
    )
    return sequence
