from pathlib import PurePath
from tests.integration_tests.validation.conformance_suite_config import ConformanceSuiteConfig

config = ConformanceSuiteConfig(
    args=[
        '--disclosureSystem', 'efm-pragmatic',
        '--formula', 'run',
    ],
    cache_version_id='F3BNGfVAc7XKtWIwszoxv3QWVsDPlail',
    ci_enabled=False,
    file='index.xml',
    info_url='N/A',
    local_filepath='efm_reg_pragmatic.zip',
    name=PurePath(__file__).stem,
    plugins=frozenset({'validate/EFM', 'inlineXbrlDocumentSet'}),
    test_case_result_options='match-any',
)
