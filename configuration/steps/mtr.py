from dataclasses import dataclass
from buildbot.plugins import util
from configuration.steps.generators.mtr.generator import MTRGenerator
from configuration.steps.generators.mtr.options import MTR, SUITE, MTROption,TestSuiteCollection, StrEnum
from configuration.steps.base import Command, CommandOptions


@dataclass
class TestCases:
    vardir: str

    @property
    def normal(self) -> MTRGenerator:
        return MTRGenerator(
                flags=[
                    MTROption(MTR.FORCE, True),
                    MTROption(MTR.MAX_TEST_FAIL, 5),
                    MTROption(MTR.PARALLEL, 4),
                    MTROption(MTR.VARDIR, f"{self.vardir}/nm"),
                ],
            )
    
    @property
    def main(self) -> MTRGenerator:
        return MTRGenerator(
                flags=[
                    MTROption(MTR.FORCE, True),
                    MTROption(MTR.MAX_TEST_FAIL, 5),
                    MTROption(MTR.PARALLEL, 4),
                    MTROption(MTR.VARDIR, f"{self.vardir}/main"),
                    MTROption(MTR.SUITE, SUITE.MAIN),
                ],
            )

class MTRTest(Command):
    def __init__(self,name: str,testcase: MTRGenerator,workdir: str = "mysql-test", options: CommandOptions = None):
        name = f"MTR - {name}"
        if options is None:
            options = CommandOptions()
        super().__init__(name=name, workdir=workdir, options=options)
        assert isinstance(testcase, MTRGenerator)
        self.testcase = testcase

    def as_cmd_arg(self) -> list[str]:
        return self.testcase.generate()