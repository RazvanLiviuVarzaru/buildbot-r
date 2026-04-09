
from buildbot.plugins import steps


class FileUpload:
    def __init__(
        self, workersrc, masterdest, mode, url, doStepIf=True
    ):
        self.workersrc = workersrc
        self.masterdest = masterdest
        self.mode = mode
        self.url = url
        self.doStepIf = doStepIf

    def generate(self):
        return steps.MultipleFileUpload(
            workersrc=self.workersrc,
            masterdest=self.masterdest,
            mode=self.mode,
            url=self.url,
            doStepIf=self.doStepIf,
        )
