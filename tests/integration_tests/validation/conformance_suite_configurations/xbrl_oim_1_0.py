import os
from tests.integration_tests.validation.conformance_suite_config import ConformanceSuiteConfig

config = ConformanceSuiteConfig(
    args=[
        '--formula', 'run',
        '--httpsRedirectCache',
        '--plugins', 'loadFromOIM',
    ],
    file='oim-index.xml',
    info_url='https://specifications.xbrl.org/work-product-index-open-information-model-open-information-model.html',
    local_filepath='tests/resources/conformance_suites/oim-conf-2021-10-13.zip',
    membership_url='https://www.xbrl.org/join',
    name=os.path.splitext(os.path.basename(__file__))[0],
)
