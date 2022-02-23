#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
import ipaddress
import logging
import paramiko
import pytest

from . import syncutil

DEFAULT_USER = 'root'
ROOT_PASSWORD = '123456'
TIMEOUT = 60 * 5
LOGGER = logging.getLogger(__name__)
logging.getLogger('paramiko.transport').setLevel(logging.WARNING)


class SshException(Exception):
    pass


class Node(object):
    """
    A class to collect operations that need to be carried out on a node (host
    or VM) but are not supported by the corresponding oVirt objects.
    """

    def __init__(self, address, password=ROOT_PASSWORD, username=DEFAULT_USER):
        """
        :param address: address of the endpoint
        :param password: the password
        :param username: the username, root if not specified
        """
        self._address = address
        self._username = username
        self._password = password
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.WarningPolicy())

    def exec_command(self, command):
        """
        Execute a ssh command on a host
        :param command: command to be executed
        :returns stdout: the standard output of the command
        :raises exc: Exception: if the command returns a non-zero exit status
        """
        self._connect()
        try:
            _, stdout, stderr = self._client.exec_command(command)
            status = stdout.channel.recv_exit_status()
            stdout_message = stdout.read()
            if status != 0:
                stderr_message = stderr.read()
                raise SshException(
                    f'Ssh command "{command}" exited with '
                    f'status code {status}. '
                    f'Stderr: {stderr_message}. '
                    f'Stdout: {stdout_message}. '
                )
            return stdout_message
        finally:
            self._close()

    def sftp_put(self, local_path, remote_path):
        self._connect()
        sftp = paramiko.SFTPClient.from_transport(self._client.get_transport())
        try:
            sftp.put(local_path, remote_path)
        finally:
            sftp.close()
            self._close()

    def _connect(self):
        self._client.connect(self._address, username=self._username, password=self._password)

    def _close(self):
        self._client.close()

    def set_mtu(self, iface_name, mtu_value):
        self.exec_command('ip link set {iface} mtu {mtu}'.format(iface=iface_name, mtu=mtu_value))

    def change_active_slave(self, bond_name, slave_name):
        """ "
        :param bond_name: str
        :param slave_name: str
        """
        self.exec_command('ip link set {bond} type bond active_slave {slave}'.format(bond=bond_name, slave=slave_name))

    def assert_default_route(self, expected_v6_route_address):
        assert expected_v6_route_address == self.get_default_route_v6()

    def get_default_route_v6(self):
        """
        :return: the v6 default route as string or None
        """
        return self._get_default_route('inet6')

    def _get_default_route(self, family):
        """
        :param family: inet for ipv4 or inet6 for ipv6
        :return: the default route address as string or None
        """
        command = 'ip -o -f ' + family + ' r show default'
        res = self.exec_command(command)
        if res is not None:
            res = res[(res.find('via ') + len('via ')) : res.find(' dev')]
        return res

    def assert_no_ping_from_netns(self, target, from_netns):
        with pytest.raises(SshException, match='100% packet loss'):
            self.ping_from_netns(target=target, from_netns=from_netns)

    def retry_ping_from_netns(self, target, from_netns):
        syncutil.sync(
            exec_func=self.ping_from_netns_successful,
            exec_func_args=(target, from_netns),
            success_criteria=lambda s: s,
            delay_start=1,
            timeout=15,
        )

    def ping_from_netns_successful(self, target, from_netns):
        try:
            self.ping_from_netns(target=target, from_netns=from_netns)
            return True
        except SshException as e:
            LOGGER.debug(e)
            return False

    def assert_ping_from_netns(self, target, from_netns):
        self.ping_from_netns(target=target, from_netns=from_netns)

    def ping_from_netns(self, target, data_size=56, from_netns=None):
        """
        Ping a given destination from source.
        :parameter source: the host which executes the ping command
        :parameter password: the root password for the host source
        :parameter target: the target of the ping command
        :parameter data_size: size of payload without headers
        :parameter netns: optional networking namespace in which to execute
        """
        netns_prefix = f'ip netns exec {from_netns} ' if from_netns else ''
        version = ipaddress.ip_address(target).version
        cmd = netns_prefix + f'ping -{version} -c 1 -M do -W 1 -s {data_size} {target}'
        self.exec_command(cmd)

    def assert_no_ping(self, target, ip_version, data_size=56, pmtudisc='do'):
        with pytest.raises(SshException, match=r'status code 1') as e:
            self.ping(target, ip_version, data_size=data_size, pmtudisc=pmtudisc)
        if e:
            LOGGER.debug(f'sshlib.assert_no_ping raised {e.value.args[0]}')

    def ping_successful(self, target, ip_version, data_size=56, pmtudisc='do'):
        try:
            self.ping(target, ip_version, data_size=data_size, pmtudisc=pmtudisc)
            return True
        except SshException:
            return False

    def ping(self, target, ip_version, iface_name=None, data_size=56, pmtudisc=None):
        """
        Ping an ip address or hostname via the specified interface
        :param str target: ip or hostname
        :param int ip_version: 4 or 6
        :param str iface_name: interface name to ping from
        :param int data_size: size of payload without headers
        :param str pmtudisc: fragmenting policy
        """
        try:
            version = ipaddress.ip_address(target).version
        except ValueError as e:
            if 'does not appear to be an IPv4 or IPv6 address' in str(e):
                # assume target is a hostname
                version = ip_version
            else:
                raise e
        options = [
            f'-{version}',
            '-c 1',
            f'-s {data_size}',
        ]
        if iface_name:
            options.append(f'-I {iface_name}')
        if pmtudisc:
            options.append(f'-M {pmtudisc}')
        cmd = f'ping {" ".join(options)} {target}'
        LOGGER.debug(cmd)
        self.exec_command(cmd)

    def get_global_ip(self, iface_name, ip_version):
        """
        :param str iface_name: interface name
        :param str ip_version: '4' or '6'
        :return: ipv4 or global ipv6 address as string
        """
        cmd = f"ip -{ip_version} -o addr show {iface_name}" f" |awk '{{print $4}}' |cut -d '/' -f 1"
        if ip_version == 6:
            cmd += ' |grep -v fe80'
        return self.exec_command(cmd).decode('utf-8').strip()

    def lookup_ip_address_with_dns_query(self, hostname, ip_version):
        """
        Wait for the ip address to update in the dns lookup
        :param hostname: str
        :param ip_version: int 4 or 6
        :return: ipv4 address as a string
        """
        return syncutil.sync(
            exec_func=self._lookup_ip_address_with_dns_query,
            exec_func_args=(hostname, ip_version),
            success_criteria=lambda ip: ip != '',
            timeout=TIMEOUT,
        )

    def _lookup_ip_address_with_dns_query(self, hostname, ip_version):
        """
        :param hostname: str
        :return: ipv4 address as a string
        """
        record_type = 'AAAA' if ip_version == 6 else 'A'
        cmd = f'dig +short {hostname} {record_type}'
        return self.exec_command(cmd).decode('utf-8').strip()

    def global_replace_str_in_file(self, old, new, filename):
        return self.exec_command(f'sed -i -r "s/{old}/{new}/g" "{filename}"')

    def restart_service(self, service_name):
        return self.exec_command(f'systemctl restart {service_name}')

    def __repr__(self):
        return (
            f'<{self.__class__.__name__}| '
            f'address:{self._address}, '
            f'username:{self._username},'
            f'password:{self._password}>'
        )


class CirrosNode(Node):
    """
    A class to collect operations that need to be carried out via ssh
    on a Cirros machine
    """

    def assign_ip_with_dhcp_client(self, iface_name):
        """
        run dhcp client to assign an ip addresses for the specified interface
        :param str iface_name: interface name
        """
        self.exec_command(f'sudo /sbin/cirros-dhcpc up {iface_name}')
