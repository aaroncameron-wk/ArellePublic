import os
import urllib.request
import zipfile
from dataclasses import dataclass


@dataclass(frozen=True)
class ConformanceSuiteConfig:
    args: list[str] = frozenset()
    expected_empty_testcases: frozenset[str] = frozenset()
    expected_failure_ids: frozenset[str] = frozenset()
    extract: bool = False
    file: str = None
    info_url: str = None
    local_filepath: str = None
    membership_url: str = None
    name: str = None
    public_download_url: str = None
    url_replace: str = None  # TODO


DOWNLOADED_URLS = []


def download_conformance_suite(config: ConformanceSuiteConfig, overwrite: bool = False):
    zip_directory = os.path.dirname(config.local_filepath)
    os.makedirs(zip_directory, exist_ok=True)
    if config.public_download_url:
        if config.public_download_url in DOWNLOADED_URLS:
            print(f"[{config.name}] Already downloaded {config.public_download_url}")
            return
        if not overwrite and os.path.exists(config.local_filepath):
            print(f"[{config.name}] File already exists: {config.local_filepath}")
            return
        print(f"[{config.name}] Downloading public conformance suite file.\n\tFrom: {config.public_download_url}\n\tTo: {config.local_filepath}")
        urllib.request.urlretrieve(config.public_download_url, config.local_filepath)

        if config.extract:
            print(f"[{config.name}] Extracting conformance suite file.")
            extract_path = config.local_filepath.replace('.zip', '')
            with zipfile.ZipFile(config.local_filepath, 'r') as zip_ref:
                zip_ref.extractall(extract_path)

        DOWNLOADED_URLS.append(config.public_download_url)
    else:
        membership_message = ''
        if config.membership_url:
            membership_message = f" \n\tMembership required (Join here: {config.membership_url})."
        print(f"[{config.name}] No public download available.{membership_message} \n\tMore info: {config.info_url}")
