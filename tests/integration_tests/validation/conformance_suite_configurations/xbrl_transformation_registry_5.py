import os
from tests.integration_tests.validation.conformance_suite_config import ConformanceSuiteConfig

config = ConformanceSuiteConfig(
    args=[
        '--formula', 'run',
    ],
    file='testcase.xml',
    info_url='https://specifications.xbrl.org/work-product-index-inline-xbrl-transformation-registry-5.html',
    local_filepath='tests/resources/conformance_suites/trr-5.0.zip',
    membership_url='https://www.xbrl.org/join',
    name=os.path.splitext(os.path.basename(__file__))[0],
)
