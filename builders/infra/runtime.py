from typing import Iterable
from dataclasses import dataclass
from pathlib import Path

from buildbot.interfaces import IBuildStep
from buildbot.plugins import steps, util
from steps.base_step import Command
from builders.base import BuildSequence


@dataclass
class DockerConfig:
    image_tag: str               # Image tag used to pull the container
    volume_mounts: list[tuple[Path, Path, str]]
    env_vars: list[tuple[str, str]]
    shm_size: str
    memlock_limit: int

class CleanupDockerResources(steps.ShellCommand):
    def __init__(self, name):
        super().__init__(name=f"Cleanup Docker resources - {name} run",
                         command=[
                             'bash',
                             '-ec',
                            util.Interpolate(f'docker kill %(prop:buildername)s || true && docker volume rm %(prop:buildername)s || true')
                            ],
                         )

class FetchContainerImage(steps.ShellCommand):
    def __init__(self, config: DockerConfig):
        self.config = config
        super().__init__(name=f"Fetch Container Image",
                         command=['docker', 'pull', config.image_tag],
                         haltOnFailure=True)
        
class RunOnMaster:
    def __init__(self, steps: list[IBuildStep]):
        self.steps = steps

    def generate(self) -> list[IBuildStep]:
        return self.steps
    

class RunInContainer:
    def __init__(self,
                 container_config: DockerConfig,
                 commands: list[Command]):
        self.config = container_config
        self.commands = commands

    def generate(self) -> list[IBuildStep]:
        result = []
        # If the workdir doesn't exist, -w option will create it under root, even if the container runs under a different user, causing permission issues.
        # Prepare all workdirs in the Volume before running any commands
        workdirs = []
        for command in self.commands:
            if command.workdir and command.workdir not in workdirs:
                workdirs.append(command.workdir)
        if workdirs:
            result.append(steps.ShellCommand(name='Prepare in container workdirs',
                               command=util.Interpolate(
                                   f'docker run --rm --mount type=volume,src=%(prop:buildername)s,dst=/home/buildbot {self.config.image_tag} mkdir -p {" ".join(workdirs)}'),
                                   haltOnFailure=True))
  
        print(self.config.env_vars)
        
        for command in self.commands:
            r_command = [
                'docker',
                'run',
                '--rm',
                # '-u', 'root', # TODO (razvan) add possibility to specify user
                '--init', # Run an init inside the container that forwards signals and reaps processes. Fixes signal handling when stopping a build (GUI << stop >> or buildmaster shutdown)
                '--name',
                util.Interpolate(f'%(prop:buildername)s'),
            ]
            for src, dst, type in self.config.volume_mounts:
                r_command += [
                    '--mount',
                    util.Interpolate(f'type={type},src={src},dst={dst}')
                ]
            # Add environment variables
            # TODO(Razvan) env[1] might need quoting
            for env in self.config.env_vars:
                r_command += ['-e', f'{env[0]}={env[1]}']
            
            r_command += [f'--shm-size={self.config.shm_size}']
            # TODO(cvicentiu) This workdir is hacky.
            r_command += ['-w', f'/home/buildbot/{command.workdir}']
            r_command += [
                self.config.image_tag
            ]
            # r_command += ['dumb-init']
            r_command += command.as_cmd_arg()

            print(r_command)
            print(command.name)

            result.append(steps.ShellCommand(
                                             name=command.name,
                                             command=r_command,
                                             interruptSignal="TERM", # init process does not respond to SIGKILL
                                             **command.options,
                                             ),)
        return result


class InContainerBuildSequence(BuildSequence):
    def __init__(self, steps: list[Command], config: DockerConfig):
        if not isinstance(config, DockerConfig):
            raise TypeError("Config must be an instance of DockerConfig")
        self.config = config
        self.steps = steps

    def get_prepare_steps(self) -> Iterable[IBuildStep]:
        return [CleanupDockerResources(name="previous"),FetchContainerImage(self.config)]

    def get_active_steps(self) -> Iterable[IBuildStep]:
        return RunInContainer(container_config=self.config,
                              commands=self.steps).generate()

    def get_cleanup_steps(self) -> Iterable[IBuildStep]:
        return [CleanupDockerResources(name="current")]
    

class OnMasterBuildSequence(BuildSequence): # Steps like: Run Command on Master, setProperty, Trigger another builder
    def __init__(self, steps: list[IBuildStep]):
        self.steps = steps
    def get_prepare_steps(self):
        return []
    def get_active_steps(self):
        return RunOnMaster(self.steps).generate()
    def get_cleanup_steps(self):
        return []

class OnWorkerBuildSequence(BuildSequence): # for example docker-library builder or other non-latent builder(windows,aix,macos,etc)
    def get_prepare_steps(self):
        pass
    def get_active_steps(self):
        pass
    def get_cleanup_steps(self):
        pass