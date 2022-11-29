import os
from tests.integration_tests.validation.conformance_suite_config import ConformanceSuiteConfig

config = ConformanceSuiteConfig(
    file='60111 AssertionSeverity-2.0-Processing/60111 Assertion Severity 2.0 Processing.xml',
    info_url='https://specifications.xbrl.org/release-history-formula-1.0-formula-conf.html',
    local_filepath='tests/resources/conformance_suites/60111 AssertionSeverity-2.0-Processing.zip',
    name=os.path.splitext(os.path.basename(__file__))[0],
)
