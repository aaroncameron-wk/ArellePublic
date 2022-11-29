import os
from tests.integration_tests.validation.conformance_suite_config import ConformanceSuiteConfig

ZIP_PATH = 'tests/resources/conformance_suites/inlineXBRL-1.1-conformanceSuite-2020-04-08.zip'
# needs to be extracted because arelle can't load a taxonomy package ZIP from within a ZIP
EXTRACTED_PATH = ZIP_PATH.replace('.zip', '')
config = ConformanceSuiteConfig(
    args=[
        '--packages', os.path.join(EXTRACTED_PATH, 'schemas/www.example.com.zip'),
        '--plugins', 'inlineXbrlDocumentSet.py|../examples/plugin/testcaseIxExpectedHtmlFixup.py',
    ],
    extract=True,
    file='index.xml',
    info_url='https://specifications.xbrl.org/work-product-index-inline-xbrl-inline-xbrl-1.1.html',
    local_filepath=ZIP_PATH,
    name=os.path.splitext(os.path.basename(__file__))[0],
    public_download_url='https://www.xbrl.org/2020/inlineXBRL-1.1-conformanceSuite-2020-04-08.zip',
)
