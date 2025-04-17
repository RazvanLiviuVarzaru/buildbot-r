import os
from dataclasses import dataclass
from pathlib import Path, PurePath
from typing import Iterable

from buildbot.interfaces import IBuildStep
from buildbot.plugins import steps, util
from configuration.steps.base import PrefixableStep


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


class CleanupWorkerDir(steps.ShellCommand):
    def __init__(self, name):
        super().__init__(
            name=f"Cleanup Worker Directory - {name} run",
            command="rm -r * .* 2> /dev/null || true",
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


class BuildSequence:
    def __init__(
        self,
        # Provide a docker_environment if you've configured at least
        # one step to run in a container
        docker_environment: DockerConfig = None,
    ):
        self.prepare_steps = []
        self.active_steps = []
        self.cleanup_steps = []
        self._docker_workdirs = []
        self.docker_environment = docker_environment

        if docker_environment:
            self.prepare_steps.append(
                CleanupDockerResources(name="previous", config=docker_environment)
            )
            self.prepare_steps.append(FetchContainerImage(config=docker_environment))
            self.prepare_steps.append(TagContainerImage(config=docker_environment))

    def get_prepare_steps(self) -> Iterable[IBuildStep]:
        return (
            self.prepare_steps
            + [CleanupWorkerDir("previous")]
            + self._create_docker_workdirs()
        )

    def get_active_steps(self) -> Iterable[IBuildStep]:
        return self.active_steps

    def get_cleanup_steps(self) -> Iterable[IBuildStep]:
        return self.cleanup_steps + [CleanupWorkerDir("current")]

    def _add_docker_workdirs(self, workdir: PurePath):
        # All created paths should be relative to the base container workdir
        if str(workdir) not in self._docker_workdirs and not workdir.is_absolute():
            self._docker_workdirs.append(str(workdir))

    def _create_docker_workdirs(self):
        if self.docker_environment:
            return [
                steps.ShellCommand(
                    name=f"Prepare in container ({self.docker_environment.image_tag}) workdirs",
                    command=(
                        "docker run --rm "
                        f"--mount{self.docker_environment.volumemount} "
                        f"{self.docker_environment.image} mkdir -p . {' '.join(self._docker_workdirs)} "
                    ),
                    haltOnFailure=True,
                )
            ]
        return []

    def add_step(self, step: IBuildStep):
        if step.run_in_container:
            if not self.docker_environment:
                raise ValueError(
                    "Running in container steps requires a docker_environment to be set"
                )
            self._add_in_container_step(self.docker_environment, step)
        else:
            self.active_steps.append(step.generate())

    def _add_in_container_step(
        self,
        config: DockerConfig,
        step: PrefixableStep,
    ):

        if step.command.workdir:
            self._add_docker_workdirs(step.command.workdir)

        result = []
        step.add_cmd_prefix(
            [
                "docker",
                "run",
                "--init",
                "--name",
                f"{config.container_name}",
                "-u",
                f"{step.command.user}",
            ]
        )

        if not step.container_commit:
            step.add_cmd_prefix(["--rm"])

        # Mandatory volume mount for state sharing between steps
        step.add_cmd_prefix(
            [
                "--mount",
                config.volumemount,
            ]
        )
        # User defined bind mounts
        for src, dst in config.bind_mounts:
            step.add_cmd_prefix(
                [
                    "--mount",
                    f"type=bind,src={src},dst={dst}",
                ]
            )

        # Global variables form the base
        env_vars = dict(config.env_vars)
        # Step variables override global variables
        env_vars.update(step.env_vars)
        for variable, value in env_vars.items():
            step.add_cmd_prefix(["-e", util.Interpolate(f"{variable}={value}")])

        step.add_cmd_prefix([f"--shm-size={config.shm_size}"])

        path = config.workdir / step.command.workdir
        # Absolute command workdir overrides basedir.
        if step.command.workdir.is_absolute():
            path = step.command.workdir

        step.add_cmd_prefix(["-w", path.as_posix()])

        step.add_cmd_prefix([config.image])

        if step.container_commit:
            result.append(
                steps.ShellCommand(
                    name=f"Checkpoint {step.name}",
                    command=[
                        "bash",
                        "-c",
                        (
                            "docker container commit "
                            f"--message {step.name} {config.container_name} "
                            f"buildbot:{config.container_name} && "
                            f"docker rm {config.container_name}"
                        ),
                    ],
                    haltOnFailure=True,
                )
            )
        result.append(step.generate())
        for step in result:
            self.active_steps.append(step)
