from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from buildbot.interfaces import IBuildStep
from buildbot.plugins import steps, util

from configuration.builders.base import BuildSequence
from configuration.steps.base import PrefixableStep
from configuration.steps.commands.base import Command
from typing import Union

@dataclass
class DockerConfig:
    repository: str  # Repository where the container image is stored
    image_tag: str  # Image tag used to pull the container
    volume_mounts: list[tuple[Path, Path, str]]
    env_vars: list[tuple[str, str]]
    shm_size: str
    memlock_limit: int


class CleanupDockerResources(steps.ShellCommand):
    def __init__(self, name):
        super().__init__(
            name=f"Cleanup Docker resources - {name} run",
            command=[
                "bash",
                "-ec",
                util.Interpolate(
                    f"docker kill %(prop:buildername)s || true && docker volume rm %(prop:buildername)s || true"
                ),
            ],
            alwaysRun=True,
        )


class PrintEnvironmentDetails(steps.ShellCommand):
    def __init__(self):
        super().__init__(
            name="Print Environment Details",
            command=[
                "bash",
                "-c",
                util.Interpolate(
                    """
                            date -u
                            uname -a
                            ulimit -a
                            command -v lscpu >/dev/null && lscpu
                            LD_SHOW_AUXV=1 sleep 0
                            """
                ),
            ],
            haltOnFailure=True,
        )


class FetchContainerImage(steps.ShellCommand):
    def __init__(self, config: DockerConfig):
        self.config = config
        super().__init__(
            name=f"Fetch Container Image - {config.image_tag}",
            command=["docker", "pull", config.repository + config.image_tag],
            haltOnFailure=True,
        )


class RunOnMaster:
    def __init__(self, steps: list[IBuildStep]):
        self.steps = steps

    def generate(self) -> list[IBuildStep]:
        return self.steps


class RunInContainer:
    def __init__(self, container_config: DockerConfig, steps: list[PrefixableStep]):
        self.config = container_config
        self.steps = steps
        self.container_image = container_config.repository + container_config.image_tag

    def generate(self) -> list[IBuildStep]:
        result = []
        # If the workdir doesn't exist, -w option will create it under root, even if the container runs under a different user, causing permission issues.
        # Prepare all workdirs in the Volume before running any commands
        workdirs = []
        for step in self.steps:
            print(step.command.workdir)
            if step.command.workdir and step.command.workdir not in workdirs:
                workdirs.append(step.command.workdir)
        if workdirs:
            print('WOLOLOLO')
            result.append(
                steps.ShellCommand(
                    name=f"Prepare in container ({self.config.image_tag}) workdirs",
                    command=util.Interpolate(
                        f'docker run --rm --mount type=volume,src=%(prop:buildername)s,dst=/home/buildbot {self.container_image} mkdir -p {" ".join(workdirs)}'
                    ),
                    haltOnFailure=True,
                )
            )

        for step in self.steps:
            step.add_cmd_prefix([
                "docker",
                "run",
                "--rm",
                "--init",  # Run an init inside the container that forwards signals and reaps processes. Fixes signal handling when stopping a build (GUI << stop >> or buildmaster shutdown)
                "--name",
                util.Interpolate(f"%(prop:buildername)s"),
                "-u",
                f"{step.command.user}",
            ])
            for src, dst, type in self.config.volume_mounts:
                step.add_cmd_prefix([
                    "--mount",
                    util.Interpolate(f"type={type},src={src},dst={dst}"),
                ])
            for env in self.config.env_vars:  # TODO(Razvan) env[1] might need quoting
                step.add_cmd_prefix(["-e", f"{env[0]}={env[1]}"])
            step.add_cmd_prefix([f"--shm-size={self.config.shm_size}"])
            step.add_cmd_prefix(["-w", f"/home/buildbot/{step.command.workdir}"]) # TODO(cvicentiu) This workdir is hacky.
            step.add_cmd_prefix([self.container_image])
            result.append(step.generate())

        return result


class InContainerBuildSequence(BuildSequence):
    def __init__(self, steps: list[Command], config: DockerConfig):
        if not isinstance(config, DockerConfig):
            raise TypeError("Config must be an instance of DockerConfig")
        self.config = config
        self.steps = steps

    def get_prepare_steps(self) -> Iterable[IBuildStep]:
        return [
            PrintEnvironmentDetails(), # TODO (razvan) # nu trebuie sa ruleze de un trilion de ori per build seq
            CleanupDockerResources(name="previous"),
            FetchContainerImage(self.config),
        ]

    def get_active_steps(self) -> Iterable[IBuildStep]:
        return RunInContainer(
            container_config=self.config, steps=self.steps
        ).generate()

    def get_cleanup_steps(self) -> Iterable[IBuildStep]:
        return [CleanupDockerResources(name="current")]
        # return []


class OnMasterBuildSequence(
    BuildSequence
):  # Steps like: Run Command on Master, setProperty, Trigger another builder
    def __init__(self, steps: list[IBuildStep]):
        self.steps = steps

    def get_prepare_steps(self):
        return []

    def get_active_steps(self):
        return RunOnMaster(self.steps).generate()

    def get_cleanup_steps(self):
        return []


class OnWorkerBuildSequence(
    BuildSequence
):  # for example docker-library builder or other non-latent builder(windows,aix,macos,etc)
    def get_prepare_steps(self):
        pass

    def get_active_steps(self):
        pass

    def get_cleanup_steps(self):
        pass
