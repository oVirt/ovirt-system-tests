#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
from pprint import pprint

import pytest

from ost_utils import engine_utils
from ost_utils import general_utils
from ost_utils.pytest import order_by
from ovirtsdk4 import types
import logging
import time

LOGGER = logging.getLogger(__name__)

base_url = "https://resources.ovirt.org/pub/ovirt-4.4/rpm/el8/noarch/"
ver_package = "ovirt-node-ng-image-update-placeholder"
cmd_for_base_count = "imgbase layout | grep -v "+" | wc -l"
cmd_for_rollbackt = "imgbase rollback"
cmd_for_getting_unactive_layer = "imgbase layout | grep ^[a-z] |" \
    " grep -v $(imgbase w | grep -o 'ovirt[^+]*')"
cmd_for_removing_layer = "imgbase base --remove {}"
cmd_for_getting_current_version = r'imgbase w | grep -Po "(\d+\.){2,}\d+-"'


def _check_if_other_layer_exists(ansible_host):
    return ansible_host.shell(cmd_for_base_count)


def _rollback_to_previous_layer_and_reboot(engine, ansible_host):
    LOGGER.info("return to previous release")
    ansible_host.shell("imgbase rollback")
    # consider replacing that with moving to maintainance and reboot
    # and host is in a state engine cannot check updates
    try:
        LOGGER.info("rebooting host")
        ansible_host.shell("systemctl reboot")
    except Exception:
        with engine_utils.wait_for_event(engine, [13]):
            # VDS_DETECTED 13
            LOGGER.info("waiting for host to be up..")


def _remove_layer(ansible_host):
    base_to_remove = ansible_host.shell(
        cmd_for_getting_unactive_layer)['stdout']
    ansible_host.shell(cmd_for_removing_layer.format(base_to_remove))


def _revert_yum_status(ansible_host):
    cur_ver = ansible_host.shell(
            cmd_for_getting_current_version)['stdout']
    cmd = 'curl ' + base_url +\
          ' | grep -Po "{}-{}.[^ \'<]*"| tail -n1'.\
          format(ver_package, cur_ver)
    ver = ansible_host.shell(f"{cmd} | tail -n1")['stdout']
    LOGGER.info(f"{ver} is the best suitable version")
    full_ver = (f"curl -L -O {base_url}/{ver}")
    LOGGER.info(f"{full_ver} will be downloaded")
    ansible_host.shell(f"curl -L -O {full_ver}")
    LOGGER.info("removing ovirt-node-ng-image-update-placeholder")
    ansible_host.shell(
        "yum remove -y ovirt-node-ng-image-update-placeholder")
    ansible_host.shell(f"rpm -i --nodeps {ver}")


@pytest.mark.skip(' [2021-08-08] Skip ovirt-node downgrade')
def test_downgrade_host(engine_api, ansible_by_hostname):

    engine = engine_api.system_service()
    hosts = engine_api.system_service().hosts_service()

    host_list = hosts.list()

    for host in host_list:
        ansible_host = ansible_by_hostname(host.name)
        if not _check_if_other_layer_exists(ansible_host):
            LOGGER.info(f"{host.name} does not have where to rollback")

        _rollback_to_previous_layer_and_reboot(engine, ansible_host)

        # useless when not performed from engine side
        # _wait_for_status(hosts, DC_NAME, types.HostStatus.UP)

        LOGGER.info("clear updated release (lvm, grubby, etc..)")
        _remove_layer(ansible_host)

        LOGGER.info("revert yum status")
        _revert_yum_status(ansible_host)
