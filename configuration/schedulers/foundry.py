import configuration.builders.definitions.foundry.builders as foundry_builders
from buildbot.plugins import schedulers, util


FOUNDRY_SCHEDULERS = []
FOUNDRY_SCHEDULERS.append(
    schedulers.ForceScheduler(
        name="foundry_force_scheduler",
        builderNames=[foundry_builders.DISPATCHER_BUILDER.name],
        codebases=[
            util.CodebaseParameter(
                codebase="",
                branch=util.FixedParameter(name="branch", default="main"),
                revision=util.FixedParameter(name="revision", default=""),
                repository=util.FixedParameter(name="repository", default="https://github.com/vuvova/foundry"),
                project=util.FixedParameter(name="project", default="vuvova/foundry"),
            )
        ]
    )
)