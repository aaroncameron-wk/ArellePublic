from tests.integration_tests.validation.conformance_suite_config import download_conformance_suite
from tests.integration_tests.validation.conformance_suite_configs import ALL_CONFORMANCE_SUITE_CONFIGS


if __name__ == "__main__":
    for config in ALL_CONFORMANCE_SUITE_CONFIGS:
        download_conformance_suite(config)
