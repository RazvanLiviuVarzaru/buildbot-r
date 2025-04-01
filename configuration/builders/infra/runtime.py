import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from buildbot.interfaces import IBuildStep
from buildbot.plugins import steps, util

from configuration.builders.base import BuildSequence
from configuration.steps.base import PrefixableStep
from configuration.steps.commands.base import Command


@dataclass
class DockerConfig:
    repository: str  # e.g. quay/ghcr + org/repo
    image_tag: str
    volume_mounts: list[tuple[Path, Path, str]]
    env_vars: list[tuple[str, str]]
    shm_size: str
    memlock_limit: int
    basedir: str


class CleanupDockerResources(steps.ShellCommand):
    def __init__(self, name, config: DockerConfig, buildername: str):
        self.buildername = buildername
        self.config = config
        super().__init__(
            name=f"Cleanup Docker resources - {name} run",
            command=[
                "bash",
                "-ec",
                util.Interpolate(
                    f"docker kill {self.buildername} || true && docker volume rm {self.buildername} || true && docker image rm checkpoint:{self.buildername} || true"
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
    def __init__(
        self,
        container_config: DockerConfig,
        steps: list[PrefixableStep],
        buildername: str,
    ):
        self.config = container_config
        self.steps = steps
        self.container_image = container_config.repository + container_config.image_tag
        self.buildername = buildername

    def generate(self) -> list[IBuildStep]:
        result = []
        # Create workdirs. Only relative paths
        workdirs = []
        for step in self.steps:
            if (
                step.command.workdir
                and step.command.workdir not in workdirs
                and not os.path.isabs(step.command.workdir)
            ):
                workdirs.append(step.command.workdir)
        if workdirs:
            result.append(
                steps.ShellCommand(
                    name=f"Prepare in container ({self.config.image_tag}) workdirs",
                    command=util.Interpolate(
                        (
                            "docker run --rm "
                            f"--mount type=volume,src={self.buildername},dst=/home/buildbot "
                            f"-w {self.config.basedir} "
                            f'{self.container_image} mkdir -p {" ".join(workdirs)}'
                        )
                    ),
                    haltOnFailure=True,
                )
            )
        for step in self.steps:
            step.add_cmd_prefix(
                [
                    "docker",
                    "run",
                    "--init",  # To proper handle signals
                    "--name",
                    util.Interpolate(f"{self.buildername}"),
                    "-u",
                    f"{step.command.user}",
                ]
            )

            if not hasattr(step, "checkpoint") or not step.checkpoint:
                step.add_cmd_prefix(["--rm"])

            for src, dst, type in self.config.volume_mounts:
                step.add_cmd_prefix(
                    [
                        "--mount",
                        util.Interpolate(f"type={type},src={src},dst={dst}"),
                    ]
                )

            # TODO(Razvan) env[1] might need quoting
            for env in self.config.env_vars:
                step.add_cmd_prefix(["-e", util.Interpolate(f"{env[0]}={env[1]}")])
            step.add_cmd_prefix([f"--shm-size={self.config.shm_size}"])

            # Ignore basedir when an absolute path is given
            if os.path.isabs(step.command.workdir):
                step.add_cmd_prefix(["-w", f"{step.command.workdir}"])
            else:
                # (TODO: Razvan) No gurarantee that this is a valid relative path
                step.add_cmd_prefix(
                    ["-w", f"{self.config.basedir}/{step.command.workdir}"]
                )

            step.add_cmd_prefix([self.container_image])

            # User defined step to run in the container
            result.append(step.generate())

            # Create a checkpoint
            if hasattr(step, "checkpoint") and step.checkpoint:
                checkpoint = f"checkpoint:{self.buildername}"
                result.append(
                    steps.ShellCommand(
                        name=f"Checkpoint {step.name}",
                        command=[
                            "bash",
                            "-c",
                            util.Interpolate(
                                f"docker commit {self.buildername} {checkpoint} && docker rm {self.buildername}"
                            ),
                        ],
                        haltOnFailure=True,
                    )
                )
                # Next steps will start from the checkpoint
                self.container_image = checkpoint

        return result


class InContainerBuildSequence(BuildSequence):
    def __init__(self, steps: list[Command], config: DockerConfig, buildername: str):
        if not isinstance(config, DockerConfig):
            raise TypeError("Config must be an instance of DockerConfig")
        self.config = config
        self.steps = steps
        self.buildername = buildername

    def get_prepare_steps(self) -> Iterable[IBuildStep]:
        return [
            PrintEnvironmentDetails(),
            CleanupDockerResources(
                name="previous", buildername=self.buildername, config=self.config
            ),
            FetchContainerImage(self.config),
        ]

    def get_active_steps(self) -> Iterable[IBuildStep]:
        return RunInContainer(
            container_config=self.config, steps=self.steps, buildername=self.buildername
        ).generate()

    def get_cleanup_steps(self) -> Iterable[IBuildStep]:
        return [
            CleanupDockerResources(
                name="current", buildername=self.buildername, config=self.config
            )
        ]
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
