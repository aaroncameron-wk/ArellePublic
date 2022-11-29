import os
import zipfile
from tests.integration_tests.validation.conformance_suite_config import (
    ConformanceSuiteConfig, download_conformance_suite
)
from tests.integration_tests.validation.conformance_suite_configurations.xbrl_utr_structure_1_0 import config as structure_config


def gen_malformed_utr_paths():
    download_conformance_suite(structure_config)
    with zipfile.ZipFile(structure_config.local_filepath, 'r') as zipf:
        for f in zipfile.Path(zipf, 'conf/utr-structure/malformed-utrs/').iterdir():
            if f.is_file() and f.name.endswith('.xml'):
                yield f.at


def generate_configs():
    return [
        ConformanceSuiteConfig(
            args=[
                '--utrUrl', os.path.join(structure_config.local_filepath, malformed_utr_file),
                '--utr',
            ],
            file='conf/utr-structure/tests/01-simple/simpleValid.xml',
            info_url='https://specifications.xbrl.org/work-product-index-registries-units-registry-1.0.html',
            local_filepath=structure_config.local_filepath,
            name=os.path.splitext(os.path.basename(__file__))[0],
            public_download_url=structure_config.public_download_url,
        )
        for malformed_utr_file in gen_malformed_utr_paths()
    ]
