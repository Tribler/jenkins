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
from __future__ import print_function

import os
import time

from deployment_utils import check_sha256_hash, fetch_latest_build_artifact, init_sentry, print_and_exit, \
    tribler_is_installed

if __name__ == '__main__':
    init_sentry()

    start_time = time.time()

    # Step 1: fetch the latest Tribler installer from Jenkins
    build_type = os.environ.get('BUILD_TYPE', 'Linux')
    job_url = os.environ.get('JENKINS_JOB_URL', None)
    if not job_url:
        print_and_exit('JENKINS_JOB_URL is not set')

    INSTALLER_FILE, HASH = fetch_latest_build_artifact(job_url, build_type)

    # Step 2: check SHA256 hash
    if not check_sha256_hash(INSTALLER_FILE, HASH):
        print_and_exit("SHA256 of file does not match with target hash %s" % HASH)

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
