import os
from tests.integration_tests.validation.conformance_suite_config import ConformanceSuiteConfig

config = ConformanceSuiteConfig(
    file='extensible-enumerations-CONF-2014-10-29/enumerations-index.xml',
    info_url='https://specifications.xbrl.org/work-product-index-extensible-enumerations-extensible-enumerations-1.0.html',
    local_filepath='tests/resources/conformance_suites/extensible-enumerations-CONF-2014-10-29.zip',
    name=os.path.splitext(os.path.basename(__file__))[0],
    public_download_url='https://www.xbrl.org/2014/extensible-enumerations-CONF-2014-10-29.zip',
)
