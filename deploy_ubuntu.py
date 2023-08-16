#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
This script fetches the latest build executable for Debian/Ubuntu from Jenkins
and installs it with necessary dependencies. It expects the following environment
variable be provided:
- JENKINS_JOB_URL : Jenkins job which builds the Debian package
- BUILD_TYPE : Build type [Win64, Win32, Linux, MacOS]
- WORKSPACE : Jenkins workspace (set by jenkins itself)
- TRIBLER_PASSWORD : Local user password
"""
import os
import time

from deployment_utils import check_sha256_hash, fetch_latest_build_artifact, init_sentry, print_and_exit, \
    tribler_is_installed, compute_sha256_hash

if __name__ == '__main__':
    init_sentry()

    start_time = time.time()

    # Step 1: fetch the latest Tribler installer from Jenkins
    build_type = os.environ.get('BUILD_TYPE', 'Linux')
    job_url = os.environ.get('JENKINS_JOB_URL', None)
    if not job_url:
        print_and_exit('JENKINS_JOB_URL is not set')

    INSTALLER_FILE, EXPECTED_FILE_HASH = fetch_latest_build_artifact(job_url, build_type)

    print(f"Jenkins Job URL: {job_url}")
    print(f"Linux installer file: {INSTALLER_FILE}")
    print(f"Linux installer hash: {EXPECTED_FILE_HASH}")

    # Step 2: check SHA256 hash
    if EXPECTED_FILE_HASH is not None:
        actual_file_hash = compute_sha256_hash(INSTALLER_FILE)
        if actual_file_hash != EXPECTED_FILE_HASH:
            error_message = "SHA256 of the installer file does not match with target hash\n" \
                            f"Actual: {actual_file_hash} != Expected: {EXPECTED_FILE_HASH}"
            print_and_exit(error_message)

    # Step 3: Remove dpkg lock if exists
    TRIBLER_PASSWORD = os.environ.get('TRIBLER_PASSWORD')
    if os.path.exists("/var/lib/dpkg/lock"):
        DPKG_UNLOCK_SCRIPT = "echo %s| sudo -S rm /var/lib/dpkg/lock" % TRIBLER_PASSWORD
        os.system(DPKG_UNLOCK_SCRIPT)

    # One step installation
    INSTALLATION_SCRIPT = "echo %s| sudo -S apt install -y --allow-downgrades %s" % (TRIBLER_PASSWORD, INSTALLER_FILE)
    os.system(INSTALLATION_SCRIPT)

    diff_time = time.time() - start_time
    print('Installed Tribler in Linux in %s seconds' % diff_time)
    time.sleep(1)

    # Step 4: check whether Tribler has been correctly installed
    if not tribler_is_installed():
        print_and_exit('Tribler has not been correctly installed')
