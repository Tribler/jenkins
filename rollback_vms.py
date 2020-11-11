"""
This script rollbacks specific VMs.
"""
from __future__ import print_function

import os
import sys
import time

from pyproxmox import prox_auth, pyproxmox

from deployment_utils import init_sentry


def print_env_variables():
    """ Print environment variables for debugging purposes """
    host = os.environ.get("PROXMOX_HOST")
    user = os.environ.get("PROXMOX_USER")
    password = os.environ.get("PROXMOX_PASS")
    rollback_state = os.environ.get("PROXMOX_ROLLBACK_STATE")
    vmids = os.environ.get("PROXMOX_VMIDS")

    print("Host: %s" % host)
    print("User: %s" % user)
    print("Password: %s" % password)
    print("Rollback State : %s" % rollback_state)
    print("VM IDs: %s" % vmids)


def rollback_vm(vm_id):
    """ Rollback and restart the virtual machine """
    auth = prox_auth(os.environ.get("PROXMOX_HOST"), os.environ.get("PROXMOX_USER"),
                     os.environ.get("PROXMOX_PASS"))
    proxmox = pyproxmox(auth)

    # Rollback the machine and wait until the machine is stopped
    print("Initiating rollback to state['%s']" % os.environ.get("PROXMOX_ROLLBACK_STATE"))
    rollback_upid = proxmox.rollbackVirtualMachine("proxmox", vm_id,
                                                   os.environ.get("PROXMOX_ROLLBACK_STATE"))['data']
    status = proxmox.getNodeTaskStatusByUPID("proxmox", rollback_upid)['data']['status']
    while status == u"running":
        time.sleep(1)
        status = proxmox.getNodeTaskStatusByUPID("proxmox", rollback_upid)['data']['status']
        print("Waiting for machine to shutdown")

    # Start the machine again and wait until it is running again
    print("Rollback complete, restarting machine")
    proxmox.startVirtualMachine("proxmox", vm_id)
    status = proxmox.getVirtualStatus("proxmox", vm_id)['data']['status']
    while status == u"stopped":
        time.sleep(1)
        status = proxmox.getVirtualStatus("proxmox", vm_id)['data']['status']
        print("Waiting for machine to come online")


if __name__ == '__main__':
    init_sentry()

    if len(sys.argv) > 1 and sys.argv[1] == "show_env":
        # Print environment variables for debugging
        print_env_variables()

    # Rollback the vm state
    for vm_id_str in os.environ.get("PROXMOX_VMIDS").split(','):
        rollback_vm(int(vm_id_str))
