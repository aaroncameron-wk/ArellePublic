import os
from tests.integration_tests.validation.conformance_suite_config import ConformanceSuiteConfig

config = ConformanceSuiteConfig(
    args=[
        '--utrUrl', 'tests/resources/conformance_suites/utr/registry/utr.xml',
        '--utr',
    ],
    file='utr-conf-cr-2013-05-17/2013-05-17/index.xml',
    info_url='https://specifications.xbrl.org/work-product-index-registries-units-registry-1.0.html',
    local_filepath='tests/resources/conformance_suites/utr/registry/utr-conf-cr-2013-05-17.zip',
    name=os.path.splitext(os.path.basename(__file__))[0],
    public_download_url='https://www.xbrl.org/utr/utr-conf-cr-2013-05-17.zip'
)
