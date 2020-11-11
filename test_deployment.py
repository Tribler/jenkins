#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
This script performs the following deployment tests for Tribler:
- Checks if Tribler is properly installed & necessary files exists
- Checks Tribler starts properly
- Check Tribler Core is running
- Checks .Tribler state directory is created
- Takes screenshots of the running state
- Copies log files
- Kills Tribler at the end
"""
from __future__ import print_function

import errno
import json
import logging
import os
import shutil
import signal
import subprocess
import sys
import time

import mss
import requests
from requests import ConnectionError

from deployment_utils import init_sentry


def error(msg):
    """ Prints error and exits """
    print('ERROR: %s' % msg)
    sys.exit(-1)


# Assuming the defaults
DEFAULT_PORT = 8085
WORKSPACE_DIR = os.environ.get('WORKSPACE', '')
WORKSPACE_SCREENSHOT_DIR = os.path.join(WORKSPACE_DIR, 'screenshots')

if sys.platform == 'win32':
    TRIBLER_DIR = r"C:\Program Files\Tribler"
    TRIBLER_EXECUTABLE = r"C:\Program Files\Tribler\tribler.exe"
    TRIBLER_DOT_DIR = os.path.join(os.getenv('APPDATA'), '.Tribler')
    TRIBLER_PROCESS = 'tribler.exe'
elif sys.platform == 'linux2':
    TRIBLER_DIR = r"/usr/share/tribler"
    TRIBLER_EXECUTABLE = r"/usr/bin/tribler"
    TRIBLER_DOT_DIR = os.path.expanduser('~/.Tribler')
    TRIBLER_PROCESS = r"/usr/bin/tribler"
elif sys.platform == 'darwin':
    TRIBLER_DIR = os.path.join(WORKSPACE_DIR, "Tribler.app")
    TRIBLER_EXECUTABLE = os.path.join(TRIBLER_DIR, "Contents", "MacOS", "tribler")
    TRIBLER_DOT_DIR = os.path.expanduser('~/.Tribler')
    TRIBLER_PROCESS = os.path.join(TRIBLER_DIR, "Contents", "MacOS", "tribler")
else:
    error("Unknown platform. Exiting...")


def get_tribler_pid():
    """ Returns the pid of running Tribler python process """
    if sys.platform == 'linux2':
        pids = []
        for proc in subprocess.check_output(['ps', '-ef']).splitlines():
            if 'python' in proc and 'run_tribler.py' in proc:
                pids += [int(proc.split()[1])]
        return pids
    elif sys.platform == 'win32':
        return [item.split()[1] for item in os.popen('tasklist').read().splitlines()[4:] if
                'tribler.exe' in item.split()]
    elif sys.platform == 'darwin':
        pids = []
        for proc in subprocess.check_output(['ps', '-ef']).splitlines():
            if TRIBLER_EXECUTABLE in proc:
                pids += [int(proc.split()[1])]
        return pids


def kill_tribler():
    """ Kills the running Tribler process """
    pids = get_tribler_pid()
    for pid in pids:
        os.kill(int(pid), signal.SIGTERM)


def check_tribler_directory():
    """ Checks if Tribler installation directory is present or not """
    if not os.path.exists(TRIBLER_DIR):
        error('Default tribler installation directory (%s) does not exist. '
              'Tribler is probably not installed' % TRIBLER_DIR)
    if not os.path.exists(TRIBLER_EXECUTABLE):
        error('Tribler executable file not found: %s' % TRIBLER_EXECUTABLE)


def run_tribler():
    """ Runs Tribler """
    if not get_tribler_pid():
        print('Starting Tribler executable [%s]...' % TRIBLER_EXECUTABLE)
        subprocess.Popen([TRIBLER_EXECUTABLE])
        # wait few seconds before it starts
        time.sleep(30)
        # check pid if tribler has started
        if not get_tribler_pid():
            copy_log_files()
            error('Tribler could not start properly')
    else:
        print('Tribler is already running')


def remove_dot_tribler_directory():
    """ Remove .Tribler directory if exists """
    if os.path.exists(TRIBLER_DOT_DIR):
        shutil.rmtree(TRIBLER_DOT_DIR)


def check_dot_tribler_dir():
    """ Checks if .Tribler directory is present """
    print('Checking if .Tribler directory exists')
    if not os.path.exists(TRIBLER_DOT_DIR):
        error('.Tribler directory does not exist. Installation was not successful')


def check_tribler_core_is_running():
    """ Checks if Tribler core is running """

    backoff = 2  # backup factor
    delay = 0.1  # 100ms
    timeout = 120  # 120 seconds

    starttime = time.time()
    for _ in range(10):  # 10 attempts
        try:
            state_url = 'http://localhost:%d/state' % DEFAULT_PORT
            response_json = json.loads(requests.get(state_url).text)
            print("Tribler state: ", response_json)

            try:
                if response_json[u'state'] == u'STARTED' and not response_json[u'last_exception']:
                    print('Tribler core has started fine')
                else:
                    error('Unexpected state response. Tribler core has not started yet.')
            except KeyError:
                # copy_log_files()
                error('KeyError: Unknown key in Tribler state response')

            return

        except ConnectionError as exception:
            logging.error(exception)

        duration = time.time() - starttime
        if duration > timeout:
            break
        else:
            time.sleep(delay)
            delay = delay * backoff  # back off exponentially

    # Fail the test if there is any pending exception
    pending_exception = sys.exc_info()[1]
    if pending_exception is not None:
        error(pending_exception.message)


def take_screenshots():
    """ Takes screenshots of the screen """
    if not os.path.exists(WORKSPACE_SCREENSHOT_DIR):
        print('Creating screenshot directory')
        os.makedirs(WORKSPACE_SCREENSHOT_DIR)

    with mss.mss() as sct:
        original_width = sct.monitors[1]['width']
        original_height = sct.monitors[1]['height']

        for i in range(1, 11):
            print('Taking screenshot %d/%d' % (i, 10))
            file_path = os.path.join(WORKSPACE_SCREENSHOT_DIR,
                                     'screenshot-' + time.strftime('%Y%m%d%H%M%S-')
                                     + str(i) + '.png')
            try:
                sct.monitors[1]['width'] = original_width
                sct.monitors[1]['height'] = original_height
                sct.shot(output=file_path)
            except mss.exception.ScreenShotError:
                print("Failed to take screenshot in %s. Continuing anyway" % sys.platform)

            # wait 10 seconds before new screenshot

            time.sleep(10)


def copy_log_files():
    """ Copies the tribler log files form .Tribler directory to Jenkins workspace"""
    source_log_dir = os.path.join(TRIBLER_DOT_DIR, "logs")
    if os.path.exists(source_log_dir):
        target_log_dir = os.path.join(WORKSPACE_DIR, "logs")
        try:
            shutil.copytree(source_log_dir, target_log_dir)
        except OSError as exc:  # python >2.5
            if exc.errno == errno.ENOTDIR:
                shutil.copy(source_log_dir, target_log_dir)
            else:
                error("Could not copy log files")


def check_error_logs():
    """ Checks if any error is logged """
    error_log_file = os.path.join(TRIBLER_DOT_DIR, "logs", "tribler-error.log")
    if os.path.isfile(error_log_file) and os.path.getsize(error_log_file) > 0:
        with open(error_log_file, 'r') as f:
            for line in f:
                if 'Traceback' in line:
                    error("There are some logged errors. Check log files")


if __name__ == '__main__':
    init_sentry()

    # check if the directory & executable exists
    check_tribler_directory()

    # Remove .Tribler directory
    remove_dot_tribler_directory()

    # Run Tribler
    run_tribler()

    # Check tribler core is running
    check_tribler_core_is_running()

    # Check if .Tribler directory is present
    check_dot_tribler_dir()

    # Wait few seconds
    time.sleep(30)

    # take few screenshots of the running application state
    take_screenshots()

    # Copy log files
    copy_log_files()

    # Check for error logs
    check_error_logs()

    # Kill tribler
    kill_tribler()
