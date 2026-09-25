import os

from configuration.builders.infra.runtime import (
    BuildSequence,
    DockerConfig,
    InContainer,
)
from configuration.steps.base import StepOptions
from configuration.steps.commands import trigger
from configuration.steps.commands.base import BashCommand
from configuration.steps.commands.download import GitInitFromCommit
from configuration.steps.commands.foundry import (
    BASE_BRANCH_ENV,
    BRANCH_ENV,
    ArchiveFoundrySource,
    DiscoverFoundryPlugins,
)
from configuration.steps.remote import PropFromShellStep, ShellStep
from git_auth import git_auth_env_vars

# What the discovery step needs to know about the run it was started by.
# "basename" is the pull request's target branch, set on the change by
# buildbot's GitHub hook (www/hooks/github.py) and carried onto the build;
# it is absent on a force build, where the discovery step doesn't need it.
_EVENT_ENV = [
    (BRANCH_ENV, "%(prop:branch)s"),
    (BASE_BRANCH_ENV, "%(prop:basename:-)s"),
]

# Where the dispatcher publishes the Foundry archive for its package builds:
# one directory per dispatcher build, under /packages, which ARTIFACTS_URL
# serves. See ArchiveFoundrySource.
_ARCHIVE = "foundry/sources/%(prop:buildnumber)s/foundry-%(prop:foundry_head)s.tar.gz"


def _clone_foundry_step(config: DockerConfig):
    return InContainer(
        ShellStep(
            # foundry_commit is the one forced through
            # foundry_force_scheduler, if any; without it, fetch the branch
            # tip -- for a pull request, the PR's own refs/pull/<n>/head ref.
            #
            # Full history (depth=0): working out which plugins a pull
            # request touches means diffing against the merge-base with its
            # target branch, which a shallow checkout doesn't have. Foundry
            # is small enough that a full clone costs nothing.
            command=GitInitFromCommit(
                repo_url="%(prop:repository)s",
                commit="%(prop:foundry_commit:~%(prop:branch)s)s",
                depth=0,
            ),
            # Foundry lives on github.com, which answers anonymous clones
            # with a 401. GitInitFromCommit already splices the credential
            # helper's "git -c" flags into the command line; this is the
            # other half -- the PAT itself, reaching git through the
            # environment only. See git_auth.py.
            secret_env_vars=git_auth_env_vars(),
        ),
        docker_environment=config,
    )


def _property_step(
    config: DockerConfig, command, property: str, env_vars=None, options=None
):
    return InContainer(
        PropFromShellStep(
            command=command, property=property, env_vars=env_vars, options=options
        ),
        docker_environment=config,
    )


def _has_plugins(step):
    return bool(step.getProperty("foundry_plugins"))


def trigger_foundry(config: DockerConfig, trigger_specs):
    # The dispatcher is the only one to clone Foundry, and only to find out
    # what to build: which plugins exist (or, for a pull request, which ones
    # it touches). This checkout never builds anything. The package builders
    # get the same commit as an archive instead of cloning it themselves --
    # one fetch from GitHub per run rather than one per package build, and
    # every package build has the same tree, however long after this it
    # starts.
    #
    # trigger_specs: list of per-MariaDB-version dicts -- see
    # configuration/builders/definitions/foundry/builders.py.
    sequence = BuildSequence()
    sequence.add_step(_clone_foundry_step(config))
    # The exact commit that got checked out -- the forced one, or whatever
    # the branch or pull request pointed at just now -- and the short form
    # the package builders file their saved packages and logs under.
    sequence.add_step(
        _property_step(config, BashCommand(cmd="git rev-parse HEAD"), "foundry_head")
    )
    sequence.add_step(
        _property_step(
            config, BashCommand(cmd="git rev-parse --short HEAD"), "foundry_revision"
        )
    )
    sequence.add_step(
        _property_step(
            config, DiscoverFoundryPlugins(), "foundry_plugins", env_vars=_EVENT_ENV
        )
    )
    # Nothing to publish when there is nothing to build.
    sequence.add_step(
        _property_step(
            config,
            ArchiveFoundrySource(archive=f"/packages/{_ARCHIVE}"),
            "foundry_source_sha256",
            options=StepOptions(doStepIf=_has_plugins),
        )
    )
    sequence.add_step(
        trigger.FoundryDispatch(
            trigger_specs, source_url=f"{os.environ['ARTIFACTS_URL']}/{_ARCHIVE}"
        )
    )
    return sequence
