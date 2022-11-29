from argparse import Namespace
from tests.integration_tests.validation.run_conformance_suites import (
    ARGUMENTS,
    get_download_option,
    get_run_option,
    run_conformance_suites
)


def pytest_addoption(parser):
    for arg in ARGUMENTS:
        parser.addoption(arg["name"], action=arg["action"], help=arg["help"])


def pytest_configure(config):
    """
    Allows plugins and conftest files to perform initial configuration.
    This hook is called for every plugin and initial conftest
    file after command line options have been parsed.
    """
    options = Namespace(
        all=config.getoption('--all'),
        download_missing=config.getoption('--download-missing'),
        download_overwrite=config.getoption('--download-overwrite'),
        offline=config.getoption('--offline'),
        public=config.getoption('--public'),
        name=config.getoption('--name'),
    )
    run_option = get_run_option(options)
    download_option = get_download_option(options)
    run_conformance_suites(
        run_option=run_option,
        download_option=download_option,
        offline_option=options.offline
    )
