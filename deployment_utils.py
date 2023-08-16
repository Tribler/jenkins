"""
Utility script to fetch the latest build artifact from Jenkins. It expects the following environment
Not it expects following environment variables:
- WORKSPACE : Jenkins workspace (set by jenkins itself)
"""
import hashlib
import json
import os
import sys
from urllib.parse import urlparse, ParseResult

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


def compute_sha256_hash(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read and update hash string value in blocks of 4K
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()


def check_sha256_hash(file_path, target_sha256_hash):
    computed_sha256_hash = compute_sha256_hash(file_path)
    return computed_sha256_hash == target_sha256_hash


def get_artifact_extension(build_type):
    build_type = build_type.lower()
    return '_x64.exe' if build_type == 'win64' \
        else 'x86.exe' if build_type == 'win32' \
        else '.deb' if build_type == 'linux' \
        else '.dmg' if build_type == 'macos' \
        else None


def is_valid_artifact_url(parsed_url: ParseResult, build_type: str) -> bool:
    scheme = parsed_url.scheme
    if parsed_url.netloc and scheme and (scheme == 'http' or scheme == 'https'):
        extension = get_artifact_extension(build_type)
        if extension and parsed_url.path.endswith(extension):
            return True
    return False


def is_valid_jenkins_url(parsed_url: ParseResult) -> bool:
    location = parsed_url.netloc
    scheme = parsed_url.scheme
    return scheme and scheme == 'https' and location \
           and location in ['jenkins.tribler.org', 'jenkins-ci.tribler.org']


def get_artifact_name_from_url(parsed_url: ParseResult) -> str:
    parsed_path = parsed_url.path
    parsed_path = parsed_path[:-1] if parsed_path[-1] == '/' else parsed_path
    splited_paths = parsed_path.split("/")
    return splited_paths[-1] if splited_paths else None


def get_jenkins_job_build_url(job_url):
    build_json = json.loads(requests.get(f'{job_url}/api/json').text)
    build_number = build_json['lastCompletedBuild']['number']
    return f'{job_url}/{build_number}'


def get_jenkins_build_artifacts(build_url):
    build_json = json.loads(requests.get('%s/api/json' % build_url).text)
    return build_json['artifacts'] if build_json and 'artifacts' in build_json else None


def get_jenkins_build_artifact_hash(build_url, extension):
    sha256_file_url = f'{build_url}/artifact/SHA256.txt'
    sha256_file_path = save_artifact_to_workspace(sha256_file_url, 'SHA256.txt')
    sha256_hash = get_sha256_for_type(sha256_file_path, extension)
    return sha256_hash


def fetch_latest_build_artifact(job_url, build_type):
    job_url = job_url[:-1] if job_url[-1] == '/' else job_url
    parsed_url = urlparse(job_url)

    if is_valid_artifact_url(parsed_url, build_type):
        artifact_name = get_artifact_name_from_url(parsed_url)
        artifact_hash = None  # No separate hash is made mandatory for external URLs
        return save_artifact_to_workspace(job_url, artifact_name),  artifact_hash

    elif is_valid_jenkins_url(parsed_url):
        return fetch_latest_jenkins_build_artifact_and_hash(job_url, build_type)

    print_and_exit("Did not find valid artifact URL")


def fetch_latest_jenkins_build_artifact_and_hash(job_url, build_type):
    build_url = get_jenkins_job_build_url(job_url)
    artifacts = get_jenkins_build_artifacts(build_url)
    if not artifacts:
        print_and_exit('No artifacts found!')

    expected_artifact_ext = get_artifact_extension(build_type)
    if expected_artifact_ext:
        selected_artifacts = [artifact for artifact in artifacts if expected_artifact_ext in artifact['fileName']]
        if not selected_artifacts:
            print_and_exit(f"{expected_artifact_ext} is not present in the artifact list")

        # Save the artifact
        artifact_url = f"{build_url}/artifact/{selected_artifacts[0]['relativePath']}"
        saved_artifact_path = save_artifact_to_workspace(artifact_url, selected_artifacts[0]['fileName'])

        # Get the hash from SHA256 file
        sha256_hash = get_jenkins_build_artifact_hash(build_url, expected_artifact_ext)
        return saved_artifact_path, sha256_hash

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
    sentry_sdk.init(os.environ.get('SENTRY_URL'), traces_sample_rate=1.0, debug=True)
