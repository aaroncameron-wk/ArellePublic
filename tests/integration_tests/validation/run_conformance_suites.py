import sys
from argparse import ArgumentParser, Namespace
from tests.integration_tests.validation.validation_util import get_conformance_suite_test_results
from tests.integration_tests.validation.conformance_suite_config import (
    ConformanceSuiteConfig, download_conformance_suite
)
from tests.integration_tests.validation.conformance_suite_configs import (
    ALL_CONFORMANCE_SUITE_CONFIGS,
    PUBLIC_CONFORMANCE_SUITE_CONFIGS
)

ARGUMENTS = [
    {
        "name": "--all",
        "action": "store_true",
        "help": "Run all configured conformance suites."
    },
    {
        "name": "--download-overwrite",
        "action": "store_true",
        "help": "Download (and overwrite) all public conformance suite files."
    },
    {
        "name": "--download-missing",
        "action": "store_true",
        "help": "Download missing public conformance suite files."
    },
    {
        "name": "--list",
        "action": "store_true",
        "help": "List names of all configured conformance suites."
    },
    {
        "name": "--name",
        "action": "store",
        "help": "Run only conformance suites with given names, comma delimited."
    },
    {
        "name": "--offline",
        "action": "store_true",
        "help": "Run without loading anything from the internet (local files and cache only)."
    },
    {
        "name": "--public",
        "action": "store_true",
        "help": "Run all public conformance suites."
    },
]
DOWNLOAD_OPTION_MISSING = 'missing'
DOWNLOAD_OPTION_OVERWRITE = 'overwrite'
RUN_OPTION_ALL = 'all'
RUN_OPTION_PUBLIC = 'public'

ALL_RESULTS = []
DOWNLOADED_URLS = []


def _get_conformance_suite_names(run_option: str) -> list[ConformanceSuiteConfig]:
    if run_option == RUN_OPTION_ALL:
        return ALL_CONFORMANCE_SUITE_CONFIGS.copy()
    elif run_option == RUN_OPTION_PUBLIC:
        return PUBLIC_CONFORMANCE_SUITE_CONFIGS.copy()
    elif run_option:
        filter_list = run_option.split(',')
        return [c for c in ALL_CONFORMANCE_SUITE_CONFIGS if any(c.name == f for f in filter_list)]
    else:
        raise ValueError('Please use --all, --public, or --name to specify which conformance suites to run.')


def run_conformance_suites(
        run_option: str = RUN_OPTION_ALL,
        download_option: str = None,
        log_to_file: bool = False,
        offline_option: bool = False) -> None:
    conformance_suite_configs = _get_conformance_suite_names(run_option)

    if download_option:
        overwrite = download_option == DOWNLOAD_OPTION_OVERWRITE
        for conformance_suite_config in conformance_suite_configs:
            download_conformance_suite(conformance_suite_config, overwrite=overwrite)

    for config in conformance_suite_configs:
        results = get_conformance_suite_test_results(config, log_to_file=log_to_file, offline=offline_option)
        ALL_RESULTS.extend(results)


def get_download_option(options: Namespace) -> str | None:
    if options.download_overwrite:
        return DOWNLOAD_OPTION_OVERWRITE
    elif options.download_missing:
        return DOWNLOAD_OPTION_MISSING
    return None


def get_run_option(options: Namespace) -> str:
    if options.all:
        return RUN_OPTION_ALL
    elif options.public:
        return RUN_OPTION_PUBLIC
    return options.name


def run() -> None:
    parser = ArgumentParser(prog=sys.argv[0])
    for arg in ARGUMENTS:
        parser.add_argument(arg["name"], action=arg["action"], help=arg["help"])
    options = parser.parse_args(sys.argv[1:])
    if options.list:
        for config in ALL_CONFORMANCE_SUITE_CONFIGS:
            print(config.name)
    else:
        run_option = get_run_option(options)
        download_option = get_download_option(options)
        run_conformance_suites(
            run_option=run_option,
            download_option=download_option,
            log_to_file=True,
            offline_option=options.offline
        )


if __name__ == "__main__":
    run()
