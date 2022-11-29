import os
from tests.integration_tests.validation.conformance_suite_config import ConformanceSuiteConfig

config = ConformanceSuiteConfig(
    args=[
        '--formula', 'run',
    ],
    file='index.xml',
    info_url='https://specifications.xbrl.org/work-product-index-taxonomy-packages-taxonomy-packages-1.0.html',
    local_filepath='tests/resources/conformance_suites/taxonomy-package-conformance.zip',
    membership_url='https://www.xbrl.org/join',
    name=os.path.splitext(os.path.basename(__file__))[0],
)
