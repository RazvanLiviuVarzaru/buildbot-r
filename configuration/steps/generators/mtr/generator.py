from typing import Iterable

from configuration.steps.generators.base.generator import BaseGenerator
from configuration.steps.generators.mtr.options import MTR, MTROption, TestSuiteCollection


class MTRGenerator(BaseGenerator):
    def __init__(self, flags: Iterable[MTROption]):
        super().__init__(
            base_cmd=["perl", "mariadb-test-run.pl"], flags=flags, allow_duplicates=True
        )

    def set_test_suites(self, suites: TestSuiteCollection):
        self.append_flags([MTROption(MTR.SUITE, str(suites))])
