import os
from tests.integration_tests.validation.conformance_suite_config import ConformanceSuiteConfig

config = ConformanceSuiteConfig(
    args=[
        '--plugin', 'formulaXPathChecker|functionsMath',
        '--check-formula-restricted-XPath',
        '--noValidateTestcaseSchema',
    ],
    file='formula/function-registry/registry-index.xml',
    info_url='https://specifications.xbrl.org/release-history-formula-1.0-formula-conf.html',
    local_filepath='tests/resources/conformance_suites/formula.zip',
    name=os.path.splitext(os.path.basename(__file__))[0],
)
