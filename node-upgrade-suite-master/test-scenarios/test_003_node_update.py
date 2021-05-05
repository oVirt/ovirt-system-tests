from pprint import pprint
from ost_utils import engine_utils
from ost_utils import general_utils
from ost_utils.pytest import order_by
import ovirtsdk4.types as types
import logging

LOGGER = logging.getLogger(__name__)
DC_NAME = 'test-dc'

@pytest.fixture(scope='module')
def updates_available():
    return {'node': 'no'}


@pytest.fixture(scope='module')
def versions_available():
    return {'node': ''}


# duplicated from bootstrap
def _host_status_to_print(hosts_service, hosts_list):
    dump_hosts = ''
    for host in hosts_list:
        host_service_info = hosts_service.host_service(host.id)
        dump_hosts += '%s: %s\n' % (host.name, host_service_info.get().status)
    return dump_hosts


# duplicated from bootstrap
def _wait_for_status(hosts_service, dc_name, status):
    up_status_seen = False
    for _ in general_utils.linear_retrier(attempts=12, iteration_sleeptime=10):
        all_hosts = hosts_service.list(search='datacenter={}'.format(dc_name))
        up_hosts = [host for host in all_hosts if host.status == status]
        LOGGER.info(_host_status_to_print(hosts_service, all_hosts))
        # we use up_status_seen because we make sure the status is not flapping
        if up_hosts:
            if up_status_seen:
                break
            up_status_seen = True
        else:
            up_status_seen = False
    return all_hosts


"""
1)
can be done in a more anisble oriented way
if fixture to be set temporarily with check_mode
and getting all info at once
e.g using
- name: global
  connection: local
  hosts: localhost
  check_mode: yes
  tasks:
    - name: yum check | Check for updates
      yum:
        name: "ovirt-node-ng-image-update"
        state: latest
      register: stat_yum_check_output
   "results": [
       "Installed: ovirt-node-ng-image-update-4.4.4-1.el8.noarch",
       "Removed: ovirt-node-ng-image-update-placeholder-4.4.3-2.el8.noarch"
   ]
  current ansible implementation does not enable temporary setting for
  check_mode: yes
  and none of such is available in yum.

2)
  using host_service.upgrade_check() requires gathering and parsing of
  engine's /var/log/ovirt-engine/ansible-runner-service.log
  grep placeholder  /var/log/ovirt-engine/ansible-runner-service.log  | \
  tail -n1 |  grep -Po "(?<=placeholder).*" | tail -1 | \
  grep -Po "(?<=version': ')(\d+\.){2}\d+"
  and
  grep placeholder  /var/log/ovirt-engine/ansible-runner-service.log  | \
  tail -n1 |  grep -Po "(?<=placeholder).*" | tail -1 | \
  grep -Po "(?<=release': ')\d+\.\w+"
  or
  grep placeholder  /var/log/ovirt-engine/ansible-runner-service.log  | \
  tail -n1 |  grep -Po "(?<=placeholder).*" | tail -1 | \
  grep -Po "'(?=release|version)[^,]+'" | head -n2
"""
def test_update_check(engine_api, ansible_hosts, ansible_host0_facts,
                      updates_available, versions_available):
    installed = ansible_hosts.shell(
        "rpm -q ovirt-node-ng-image-update-placeholder "
        "--queryformat '%{RPMTAG_VERSION}-%{RPMTAG_RELEASE}\n'")
    available = ansible_hosts.shell(
        "yum list available | grep ovirt-node-ng-image-update.noarch |"
        "awk '{print $2}'")
    LOGGER.info("{} installed\n"
          "{} available".format(installed['stdout'],
                                available['stdout']))
    if available['stdout'] and available['stdout'] != installed['stdout']:
        versions_available['node'] = available['stdout']
        updates_available['node'] = 'yes'


def test_update_host(engine_api, ansible_by_hostname, updates_available,
                     versions_available):
    if updates_available['node'] == 'yes':
        engine = engine_api.system_service()
        hosts = engine_api.system_service().hosts_service()
        total_hosts = len(hosts.list(search='datacenter={}'.format(DC_NAME)))
        _timeout = 40*60*total_hosts

        def _perform_update():
            host_list = hosts.list()
            LOGGER.info(
                "_perform_update called with timout {}".format(host_list))

            for host in host_list:
                host_service = hosts.host_service(host.id)
                LOGGER.info("_perform_update on host id:{}".format(host.id))
                with engine_utils.wait_for_event(engine, [884, 885], _timeout):
                    LOGGER.info("upgrade check")
                    # HOST_AVAILABLE_UPDATES_STARTED(884)
                    # HOST_AVAILABLE_UPDATES_FINISHED(885)
                    # HOST_AVAILABLE_UPDATES_SKIPPED_UNSUPPORTED_STATUS(887)
                    host_service.upgrade_check()

                with engine_utils.wait_for_event(engine,
                                                 [15, 840, 888], _timeout):
                    LOGGER.info("update")
                    # HOST_UPGRADE_FINISHED_AND_WILL_BE_REBOOTED(888)
                    # HOST_UPGRADE_STARTED(840)
                    # VDS_MAINTENANCE(15)
                    host_service.upgrade(reboot=True)

            LOGGER.info("updrade process finished")
            _wait_for_status(hosts, DC_NAME, types.HostStatus.UP)
            LOGGER.info("host are up after upgrade")

            for host in host_list:
                ansible_host = ansible_by_hostname(host.name)
                new_ver = ansible_host.shell(
                    "cat /var/imgbased/.image-updated |"
                    "grep -Po '(?<=update-).*(?=.squashfs.img)'")
                LOGGER.info(
                    "{} upgraded to: {}".format(host.name,
                                                new_ver['stdout_lines']))
                assert new_ver['stdout_lines'] == [versions_available['node']]
            return True

        _perform_update()
