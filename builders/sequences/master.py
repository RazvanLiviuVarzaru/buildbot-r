
from builders.infra.runtime import OnMasterBuildSequence

def set_property():
    return OnMasterBuildSequence()

def trigger_builder():
    return OnMasterBuildSequence()

def master_command(): # example: import from steps what is required to create an S3 bucket
    return OnMasterBuildSequence()