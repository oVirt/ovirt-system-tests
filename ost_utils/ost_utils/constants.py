#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

DEFAULT_OVN_PROVIDER_NAME = 'ovirt-provider-ovn'
# Used to be 20 minutes, but wasn't enough in certain conditions - basically,
# the time installation took + 600 seconds hard-coded delay by the engine
# waiting for the host to reboot. TODO: Make the engine poll the host in a
# loop instead of waiting a constant time and revert here to 20 minutes.
ADD_HOST_TIMEOUT = 30 * 60
ENGINE_VM_RESTART_TIMEOUT = 20 * 60
FLOATING_DISK_NAME = 'floating_disk'
