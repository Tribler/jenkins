"""
Utility script to fetch the latest build artifact from Jenkins. It expects the following environment
Not it expects following environment variables:
- WORKSPACE : Jenkins workspace (set by jenkins itself)
"""
from __future__ import print_function

import hashlib
import json
import os
import sys

import requests
import sentry_sdk


def print_and_exit(msg):
    print('ERROR: %s' % msg)
    sys.exit(1)


def save_artifact_to_workspace(artifact_url, filename):
    file_path = os.path.join(os.environ.get('WORKSPACE'), filename)
    download_response = requests.get(artifact_url)
    download_response.raise_for_status()

    with open(file_path, 'wb') as handle:
        handle.write(download_response.content)
    return file_path


def get_sha256_for_type(sha256_file_path, type_selector):
    with open(sha256_file_path, "r") as sha256_file:
        lines = sha256_file.readlines()
        for line in lines:
            parts = line.split("  ")
            if type_selector in parts[1]:
                return parts[0]
    return None


def check_sha256_hash(file_path, target_sha256_hash):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read and update hash string value in blocks of 4K
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
        hex_sha256_hash = sha256_hash.hexdigest()

    return hex_sha256_hash == target_sha256_hash


def fetch_latest_build_number(job_url):
    build_json = json.loads(requests.get('%s/api/json' % job_url).text)
    return build_json['lastCompletedBuild']['number']


def fetch_latest_build_artifact(job_url, build_type):
    job_url = job_url[:-1] if job_url[-1] == '/' else job_url
    build_number = fetch_latest_build_number(job_url)
    build_url = '%s/%d' % (job_url, build_number)
    last_build_json = json.loads(requests.get('%s/api/json' % build_url).text)
    if not last_build_json['artifacts']:
        print_and_exit('No artifacts found!')

    type_selector = '_x64.exe' if build_type == 'Win64' \
        else 'x86.exe' if build_type == 'Win32' \
        else '.deb' if build_type == 'Linux' \
        else '.dmg' if build_type == 'MacOS' \
        else None

    if type_selector:
        artifacts = [artifact for artifact in last_build_json['artifacts'] if type_selector in artifact['fileName']]
        if not artifacts:
            print_and_exit("%s is not present in the artifact list" % type_selector)
        artifact_url = '%s/artifact/%s' % (build_url, artifacts[0]['relativePath'])

        # Download the SHA256 file
        sha256_file_url = '%s/artifact/SHA256.txt' % build_url
        sha256_file_path = save_artifact_to_workspace(sha256_file_url, 'SHA256.txt')
        sha256_hash = get_sha256_for_type(sha256_file_path, type_selector)
        if not sha256_hash:
            print_and_exit("Could not find SHA256 hash for type %s" % type_selector)

        return save_artifact_to_workspace(artifact_url, artifacts[0]['fileName']), sha256_hash

    print_and_exit("Artifact type not selected. Supported types are [Win64, Win32, Linux, MacOS]")


def tribler_is_installed():
    """
    Check whether Tribler has been correctly installed on the various platforms.
    """
    WORKSPACE_DIR = os.environ.get('WORKSPACE', '')
    if sys.platform == 'win32':
        TRIBLER_DIR = r"C:\Program Files\Tribler"
        TRIBLER_EXECUTABLE = r"C:\Program Files\Tribler\tribler.exe"
    elif sys.platform.startswith('linux'):
        TRIBLER_DIR = r"/usr/share/tribler"
        TRIBLER_EXECUTABLE = r"/usr/bin/tribler"
    elif sys.platform == 'darwin':
        TRIBLER_DIR = os.path.join(WORKSPACE_DIR, "Tribler.app")
        TRIBLER_EXECUTABLE = os.path.join(TRIBLER_DIR, "Contents", "MacOS", "tribler")
    else:
        return False

    if not os.path.exists(TRIBLER_DIR) or not os.path.exists(TRIBLER_EXECUTABLE):
        return False

    return True


def init_sentry():
    """ Inits the sentry sdk by setting up a URL and a trace sample rate

    To change the URL, please specify a corresponding ENV variable.

    If `SENTRY_URL` is not set, then Sentry error reporting will be disabled.
    """
    sentry_sdk.init(os.environ.get('SENTRY_URL'), traces_sample_rate=1.0)
