from dataclasses import dataclass
from configuration.steps.generators.mtr.generator import MTRGenerator
from configuration.steps.generators.mtr.options import MTR, SUITE, MTROption,TestSuiteCollection
from configuration.steps.commands.base import Command


@dataclass
class TestCases:
    vardir: str
    jobs: int

    @property
    def normal(self) -> MTRGenerator:
        return MTRGenerator(
                flags=[
                    MTROption(MTR.VERBOSE_RESTART, True),
                    MTROption(MTR.FORCE, True),
                    MTROption(MTR.RETRY, 3),
                    MTROption(MTR.MAX_SAVE_CORE, 2),
                    MTROption(MTR.MAX_SAVE_DATADIR, 1),
                    MTROption(MTR.MAX_TEST_FAIL, 20),
                    MTROption(MTR.PARALLEL, self.jobs),
                    MTROption(MTR.VARDIR, self.vardir),
                ],
            )
    
    @property
    def main(self) -> MTRGenerator:
        return MTRGenerator(
                flags=[
                    MTROption(MTR.VERBOSE_RESTART, True),
                    MTROption(MTR.FORCE, True),
                    MTROption(MTR.RETRY, 3),
                    MTROption(MTR.MAX_SAVE_CORE, 2),
                    MTROption(MTR.MAX_SAVE_DATADIR, 1),
                    MTROption(MTR.MAX_TEST_FAIL, 20),
                    MTROption(MTR.PARALLEL, self.jobs),
                    MTROption(MTR.VARDIR, self.vardir),
                    MTROption(MTR.SUITE, SUITE.MAIN),
                ],
            )
    
    @property
    def galera(self) -> MTRGenerator:
        generator = MTRGenerator(
                flags=[
                    MTROption(MTR.VERBOSE_RESTART, True),
                    MTROption(MTR.FORCE, True),
                    MTROption(MTR.RETRY, 3),
                    MTROption(MTR.MAX_SAVE_CORE, 2),
                    MTROption(MTR.MAX_SAVE_DATADIR, 10),
                    MTROption(MTR.MAX_TEST_FAIL, 20),
                    MTROption(MTR.BIG_TEST, True),
                    MTROption(MTR.PARALLEL, self.jobs),
                    MTROption(MTR.VARDIR, self.vardir),

                ],
            )
        suites = TestSuiteCollection([SUITE.WSREP, SUITE.GALERA, SUITE.GALERA_3NODES, SUITE.GALERA_3NODES_SR])
        generator.set_test_suites(suites)
        return generator

class MTRTest(Command):
    def __init__(self,name: str,testcase: MTRGenerator,workdir: str = "mysql-test"):
        name = f"MTR - {name}"
        super().__init__(name=name, workdir=workdir)
        assert isinstance(testcase, MTRGenerator)
        self.testcase = testcase

    def as_cmd_arg(self) -> list[str]:
        return self.testcase.generate()