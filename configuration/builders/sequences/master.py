from configuration.builders.infra.runtime import OnMasterBuildSequence
from configuration.steps.trigger import DockerLibrary, Install, Upgrade


def set_property():
    return OnMasterBuildSequence()


def schedulers(schedulers, RHEL=False):
    steps = []
    for scheduler in schedulers:
        if scheduler == "install":
            steps.append(Install().generate())
        elif scheduler == "upgrade":
            steps.append(Upgrade().generate())
        elif scheduler == "dockerlibrary":
            steps.append(DockerLibrary(RHEL).generate())
        else:
            raise ValueError(f"Unknown scheduler type: {scheduler}")
    return OnMasterBuildSequence(steps)


def master_command():  # example: import from steps what is required to create an S3 bucket
    return OnMasterBuildSequence()
