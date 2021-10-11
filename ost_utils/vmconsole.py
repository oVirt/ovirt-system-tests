#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import contextlib
import logging
import os
import pty
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

    @contextlib.contextmanager
    def connect(self, vm_id):
        with self._connect(vm_id):
            with self._login():
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
            time.sleep(15)
            self._pre_login()
            self._read_until_prompt('login: ')
            self._write(f'{self._user}\n')
            self._read_until_prompt('Password: ')
            self._shell(f'{self._passwd}')
            self._logged_in = True
            yield
        finally:
            self._logout()

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
        with self.connect(vm_id):
            self.shell(f'sudo ip addr add {ip} dev {iface}')
            ip_addr_show = self.shell(f'ip addr show {iface}')
        return ip_addr_show

    def shell(self, cmd):
        if not self._connected or not self._logged_in:
            raise RuntimeError('vmconsole not connected or not logged in')
        return self._shell(cmd)

    def _shell(self, cmd):
        self._write(f'{cmd}\n')
        return self._read_until_bash_prompt()

    def _read_until_bash_prompt(self):
        return self._read_until_prompt(self._prompt)

    def _read_until_prompt(self, prompt):
        LOGGER.debug(f'vmconsole: reading until {prompt}...')
        time.sleep(2)
        recv = ''
        while not recv.endswith(prompt):
            recv = ''.join([recv, (self._read())])
        LOGGER.debug(recv)
        return recv

    def _read(self):
        return self._reader.stdout.read(1)

    def _write(self, entry):
        time.sleep(2)
        LOGGER.debug(f'vmconsole: writing [{entry}]')
        self._writer.write(entry)
        self._writer.flush()


class CirrosSerialConsole(VmSerialConsole):
    def __init__(self, private_key_path, vmconsole_proxy_ip):
        super(CirrosSerialConsole, self).__init__(
            private_key_path, vmconsole_proxy_ip, 'cirros', 'gocubsgo'
        )

    def get_ip(self, vm_id, iface):
        with self.connect(vm_id):
            self.shell(f'sudo /sbin/cirros-dhcpc up {iface}')
            ip_addr_show = self.shell(f'ip addr show {iface}')
        return ip_addr_show
