import os
from tests.integration_tests.validation.conformance_suite_config import ConformanceSuiteConfig

config = ConformanceSuiteConfig(
    file='index.xml',
    info_url='https://specifications.xbrl.org/work-product-index-registries-lrr-1.0.html',
    local_filepath='tests/resources/conformance_suites/lrr-conf-pwd-2005-06-21.zip',
    membership_url='https://www.xbrl.org/join',
    name=os.path.splitext(os.path.basename(__file__))[0],
    url_replace='file:///c:/temp/conf/'
)
