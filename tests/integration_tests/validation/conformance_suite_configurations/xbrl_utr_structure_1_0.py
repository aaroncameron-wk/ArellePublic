import os
from tests.integration_tests.validation.conformance_suite_config import ConformanceSuiteConfig

ZIP_PATH = 'tests/resources/conformance_suites/utr/structure/utr-structure-conf-cr-2013-11-18.zip'
config = ConformanceSuiteConfig(
    args=[
        '--utrUrl', os.path.join(ZIP_PATH, 'conf/utr-structure/utr-for-structure-conformance-tests.xml'),
        '--utr',
    ],
    file='conf/utr-structure/index.xml',
    info_url='https://specifications.xbrl.org/work-product-index-registries-units-registry-1.0.html',
    local_filepath=ZIP_PATH,
    name=os.path.splitext(os.path.basename(__file__))[0],
    public_download_url='https://www.xbrl.org/2013/utr-structure-conf-cr-2013-11-18.zip'
)
