#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import contextlib
import ipaddress
import logging
import os
import pty
import signal
import subprocess
import time


LOGGER = logging.getLogger(__name__)


class VmSerialConsole(object):  # pylint: disable=too-many-instance-attributes

    USER_PROMPT = '$ '
    ROOT_PROMPT = '# '

    def __init__(
        self,
        private_key_path,
        vmconsole_proxy_ip,
        vm_user,
        vm_password,
        bash_prompt=USER_PROMPT,
    ):
        self._private_key_path = private_key_path
        self._proxy_ip = vmconsole_proxy_ip
        self._user = vm_user
        self._passwd = vm_password
        self._reader = None
        self._writer = None
        self._prompt = bash_prompt
        self._connected = False
        self._logged_in = False
        self._read_alarm = BlockingIOAlarm('timed out waiting for read', 15)

    @contextlib.contextmanager
    def connect(self, vm_id):
        if not self._connected:
            with self._connect(vm_id):
                if not self._logged_in:
                    with self._login():
                        yield self
        elif not self._logged_in:
            with self._login():
                yield self
        else:
            yield self

    @contextlib.contextmanager
    def _connect(self, vm_id):
        time.sleep(15)
        try:
            master, slave = pty.openpty()
            LOGGER.debug('vmconsole: opened pty')
            args = [
                'ssh',
                '-t',
                '-o',
                'StrictHostKeyChecking=no',
                '-o',
                'UserKnownHostsFile=/dev/null',
                '-i',
                f'{self._private_key_path}',
                '-p',
                '2222',
                f'ovirt-vmconsole@{self._proxy_ip}',
                'connect',
                f'--vm-id={vm_id}',
            ]
            self._reader = subprocess.Popen(
                args,
                stdin=slave,
                stdout=subprocess.PIPE,
                universal_newlines=True,
                bufsize=0,
            )
            LOGGER.debug(f'vmconsole: opened reader with args {args}')
            self._writer = os.fdopen(master, 'w')
            LOGGER.debug('vmconsole: opened writer')
            self._connected = True
            yield
        finally:
            self._disconnect()

    def _disconnect(self):
        LOGGER.debug('vmconsole: disconnecting...')
        self._reader.terminate()
        self._writer.close()
        self._connected = False
        LOGGER.debug('vmconsole: disconnected')

    @contextlib.contextmanager
    def _login(self):
        try:
            signal.signal(signal.SIGALRM, self._read_alarm.handle)
            time.sleep(15)
            self._pre_login()
            self._read_until_prompt('login: ')
            self._write(f'{self._user}\n')
            self._read_until_prompt('Password: ')
            self._write(f'{self._passwd}\n')
            self._read_until_bash_prompt()
            self._logged_in = True
            yield
        finally:
            self._logout()
            signal.signal(signal.SIGALRM, signal.SIG_DFL)

    def _pre_login(self):
        # a single `write('\n')` might be enough but it might prove flaky
        for i in range(15):
            LOGGER.debug(f'vmconsole: pre login {i}')
            self._write('\n')
            ch = self._read()
            if ch == '\n' or len(ch.strip()) != 0:
                break
            time.sleep(2)

    def _logout(self):
        LOGGER.debug('vmconsole: logging out')
        self._write('exit\n')
        self._read_until_prompt('\n\n\n')
        self._logged_in = False

    def add_static_ip(self, vm_id, ip, iface):
        ips = self.shell(vm_id, (Shell.ip_address_add(ip, iface), Shell.get_ips(iface)))
        ip_version = ipaddress.ip_interface(ip).version
        return Shell.next_ip(ips.splitlines(), ip_version)

    def get_ip(self, vm_id, iface, ip_version):
        ips = self.get_ips(vm_id, iface)
        return Shell.next_ip(ips, ip_version)

    def get_ips(self, vm_id, iface):
        return self.shell(vm_id, (Shell.get_ips(iface),)).splitlines()

    def shell(self, vm_id, commands):
        with self.connect(vm_id):
            for cmd in commands:
                entry = f'{cmd}\n'
                self._write(entry)
                res = self._read_until_bash_prompt()
                res = res.replace(entry, '').rsplit(self._prompt)[0]
                LOGGER.debug(f'vmconsole: shell {cmd} returned: {res}')
        return res

    def can_log_in(self, vm_id):
        with self.connect(vm_id) as console:
            logged_in = console.logged_in
        return logged_in

    @property
    def logged_in(self):
        return self._logged_in

    def _read_until_bash_prompt(self):
        return self._read_until_prompt(self._prompt)

    def _read_until_prompt(self, prompt):
        LOGGER.debug(f'vmconsole: reading until {prompt}...')
        time.sleep(2)
        recv = ''
        try:
            while not recv.endswith(prompt):
                recv = ''.join([recv, (self._read())])
        finally:
            LOGGER.debug(f'vmconsole: _read_until_prompt: read so far: [{recv}]')
        LOGGER.debug(f'vmconsole: read until prompt returned: {recv}')
        return recv

    def _read(self):
        signal.alarm(self._read_alarm.seconds)
        c = self._reader.stdout.read(1)
        signal.alarm(0)  # cancel
        return c

    def _write(self, entry):
        time.sleep(2)
        LOGGER.debug(f'vmconsole: writing [{entry}]')
        self._writer.write(entry)
        self._writer.flush()


class CirrosSerialConsole(VmSerialConsole):
    def __init__(self, private_key_path, vmconsole_proxy_ip):
        super(CirrosSerialConsole, self).__init__(private_key_path, vmconsole_proxy_ip, 'cirros', 'gocubsgo')

    def assign_ip4_if_missing(self, vm_id, iface):
        ip = self.get_ip(vm_id, iface, 4)
        return ip if ip else self.assign_ip4(vm_id, iface)

    def assign_ip4(self, vm_id, iface):
        ips = self.shell(vm_id, (Shell.cirros_assign_dhcp_ip(iface), Shell.get_ips(iface)))
        return Shell.next_ip(ips.splitlines(), 4)


class Shell(object):
    @classmethod
    def get_ips(cls, iface):
        return f"ip addr show {iface} | " f"awk '/inet/ {{print $2}}' | " f"awk -F/ '{{print $1}}'"

    @classmethod
    def ip_address_add(cls, ip, iface):
        return f'sudo ip addr add {ip} dev {iface}'

    @classmethod
    def cirros_assign_dhcp_ip(cls, iface):
        return f'sudo /sbin/cirros-dhcpc up {iface}'

    @classmethod
    def next_ip(cls, ips, ip_version):
        return next(
            (ip for ip in ips if ipaddress.ip_address(ip).version == int(ip_version)),
            None,
        )


class BlockingIOAlarm:
    def __init__(self, msg, seconds):
        self._error = BlockingIOError(msg)
        self._seconds = seconds

    def handle(self, sig, frame):
        raise self._error

    @property
    def seconds(self):
        return self._seconds
