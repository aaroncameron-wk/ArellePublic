import pytest
from tests.integration_tests.validation.run_conformance_suites import ALL_RESULTS


@pytest.mark.parametrize("results", ALL_RESULTS)
def test_conformance_suite(results):
    assert results.get('status') == 'pass', \
        'Expected these validation suffixes: {}, but received these validations: {}'.format(
            results.get('expected'), results.get('actual')
        )
