from pathlib import PurePath
from tests.integration_tests.validation.conformance_suite_config import ConformanceSuiteConfig


EXPECTED_FAILURE_IDS = frozenset([
])

config = ConformanceSuiteConfig(
    args=[
        '--disclosureSystem', 'efm-pragmatic',
        '--formula', 'run',
    ],
    cache_version_id='RQmf2PhpD.v21IUDvSq5IxqBjaP3SAPF',
    ci_enabled=False,
    expected_failure_ids=EXPECTED_FAILURE_IDS,
    file='index.xml',
    info_url='N/A',
    local_filepath='efm_reg_dqc.zip',
    name=PurePath(__file__).stem,
    plugins=frozenset({'validate/EFM', 'inlineXbrlDocumentSet'}),
    test_case_result_options='match-any',
    shards=64,
)
