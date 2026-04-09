# MultipleFileUpload

from buildbot.plugins import steps
from buildbot.process.properties import Property


class MultipleFileUpload:
    def __init__(
        self, workersrcs, masterdest, mode, url, doStepIf=True, properties=None
    ):
        self.workersrcs = workersrcs
        self.masterdest = masterdest
        self.mode = mode
        self.url = url
        self.doStepIf = doStepIf

    def generate(self):
        return steps.MultipleFileUpload(
            workersrcs=self.workersrcs,
            masterdest=self.masterdest,
            mode=self.mode,
            url=self.url,
            doStepIf=self.doStepIf,
        )
