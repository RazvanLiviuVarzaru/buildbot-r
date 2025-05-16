import os
from dataclasses import dataclass
from pathlib import Path, PurePath
from typing import Iterable

from buildbot.interfaces import IBuildStep
from buildbot.plugins import steps, util
from configuration.steps.base import PrefixableStep, BaseStep
import copy


class BuildSequence:
    def __init__(self):
        self.steps = []

    def get_steps(self) -> Iterable[IBuildStep]:
        return self.steps

    def add_step(self, step: BaseStep):
        self.steps.append(step)

## ----------------------------------------------------------------------##
##                           Docker Helper Classes                       ##
##-----------------------------------------------------------------------##

@dataclass
class DockerConfig:
    repository: str  # e.g. quay/ghcr + org/repo
    image_tag: str
    container_name: str
    bind_mounts: list[tuple[Path, Path]]  # src, dst
    env_vars: list[tuple[str, str]]
    shm_size: str
    memlock_limit: int
    workdir: PurePath

    @property
    def image(self) -> str:
        return f"{self.repository}{self.image_tag}"

    @property
    def volumemount(self):
        return f"type=volume,src={self.container_name},dst={self.workdir}"


class InContainer:
    def __new__(cls, step: PrefixableStep, docker_environment: DockerConfig, container_commit: bool = False) -> PrefixableStep:
        step = copy.deepcopy(step)
        step.run_in_container = True,
        step.container_commit = container_commit
        step.docker_environment = docker_environment

        step.add_cmd_prefix(
            [
                "docker",
                "run",
                "--init",
                "--name",
                f"{docker_environment.container_name}",
                "-u",
                f"{step.command.user}",
            ]
        )
        # Mandatory volume mount for state sharing between steps
        step.add_cmd_prefix(
            [
                "--mount",
                docker_environment.volumemount,
            ]
        )

        if not container_commit:
            step.add_cmd_prefix(["--rm"])

        # User defined bind mounts
        for src, dst in docker_environment.bind_mounts:
            step.add_cmd_prefix(
                [
                    "--mount",
                    f"type=bind,src={src},dst={dst}",
                ]
            )

        # Global variables form the base
        env_vars = dict(docker_environment.env_vars)
        # Step variables override global variables
        env_vars.update(step.env_vars)
        for variable, value in env_vars.items():
            step.add_cmd_prefix(["-e", util.Interpolate(f"{variable}={value}")])

        step.add_cmd_prefix([f"--shm-size={docker_environment.shm_size}"])

        path = docker_environment.workdir / step.command.workdir
        # Absolute command workdir overrides basedir.
        if step.command.workdir.is_absolute():
            path = step.command.workdir

        step.add_cmd_prefix(["-w", path.as_posix()])

        step.add_cmd_prefix([docker_environment.image])

        return step

class CreateDockerWorkdirs(steps.ShellCommand):
    def __init__(self, config: DockerConfig, workdirs: list[str]):
        super().__init__(
            name=f"Create Docker Workdirs",
            command=(
                "docker run --rm "
                f"--mount{config.volumemount} "
                f"{config.image} mkdir -p . {' '.join(workdirs)} "
            ),
            haltOnFailure=True,
        )

class CleanupDockerResources(steps.ShellCommand):
    def __init__(self, name, config: DockerConfig):
        super().__init__(
            name=f"Cleanup Docker resources - {name} run",
            command=[
                "bash",
                "-ec",
                f"""
                (
                    docker rm --force {config.container_name};
                    docker volume rm {config.container_name};
                    docker image rm buildbot:{config.container_name};
                ) || true
                """,
            ],
            alwaysRun=True,
        )
class FetchContainerImage(steps.ShellCommand):
    def __init__(self, config: DockerConfig):
        super().__init__(
            name=f"Fetch Container Image - {config.image_tag}",
            command=["docker", "pull", config.repository + config.image_tag],
            haltOnFailure=True,
        )


class TagContainerImage(steps.ShellCommand):
    def __init__(self, config: DockerConfig):
        super().__init__(
            name=f"Tag Container Image - {config.image_tag}",
            command=[
                "bash",
                "-ec",
                (
                    f"docker image rm -f buildbot:{config.container_name} && "
                    f"docker tag {config.image} buildbot:{config.container_name}"
                ),
            ],
            haltOnFailure=True,
        )

class ContainerCommit(steps.ShellCommand):
    def __init__(self, config: DockerConfig, step_name: str):
        super().__init__(
            name=f"Checkpoint {step_name}",
            command=[
                "bash",
                "-c",
                (
                    "docker container commit "
                    f"--message {step_name} {config.container_name} "
                    f"buildbot:{config.container_name} && "
                    f"docker rm {config.container_name}"
                ),
            ],
            haltOnFailure=True,
        )
## ----------------------------------------------------------------------##
##                           Worker Helper Classes                       ##
##-----------------------------------------------------------------------##

class CleanupWorkerDir(steps.ShellCommand):
    def __init__(self, name):
        super().__init__(
            name=f"Cleanup Worker Directory - {name} run",
            command="rm -r * .* 2> /dev/null || true",
            alwaysRun=True,
        )