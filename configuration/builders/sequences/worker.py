from configuration.builders.infra.runtime import OnWorkerBuildSequence

def dockerlibrary():
    return OnWorkerBuildSequence()

def windows():
     return OnWorkerBuildSequence()

def windows_packages():
     return OnWorkerBuildSequence()

def macos():
     return OnWorkerBuildSequence()

def freebsd():
     return OnWorkerBuildSequence()

### ... and so on