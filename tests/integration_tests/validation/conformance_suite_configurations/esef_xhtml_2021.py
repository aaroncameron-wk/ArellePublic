import os
from tests.integration_tests.validation.conformance_suite_config import ConformanceSuiteConfig

config = ConformanceSuiteConfig(
    args=[
        '--disclosureSystem', 'esef-unconsolidated',
        '--formula', 'none',
        '--plugins', 'validate/ESEF',
    ],
    file='esef_conformance_suite_2021/esef_conformance_suite_2021/index_pure_xhtml.xml',
    info_url='https://www.esma.europa.eu/document/conformance-suite-2021',
    local_filepath='tests/resources/conformance_suites/esef_conformance_suite_2021.zip',
    name=os.path.splitext(os.path.basename(__file__))[0],
    public_download_url='https://www.esma.europa.eu/sites/default/files/library/esef_conformance_suite_2021.zip',
)
