import array
import fcntl
import select
import socket
import sys
import termios
import time
import uuid
import logging

import paramiko

from ost_utils import command_status
from ost_utils import utils

SSH_TIMEOUT_DEFAULT = 100
SSH_TRIES_DEFAULT = 20
LOGGER = logging.getLogger(__name__)
logging.getLogger('paramiko.transport').setLevel(logging.WARNING)

def ssh(
    ip_addr,
    command,
    host_name=None,
    data=None,
    show_output=True,
    tries=None,
    ssh_key=None,
    username='root',
    password='vagrant',
):
    host_name = host_name or ip_addr
    client = get_ssh_client(
        ip_addr=ip_addr,
        host_name=host_name,
        ssh_tries=tries,
        ssh_key=ssh_key,
        username=username,
        password=password,
    )
    transport = client.get_transport()
    channel = transport.open_session()
    joined_command = ' '.join(command)
    command_id = _gen_ssh_command_id()
    LOGGER.debug(
        'Running %s on %s: %s%s',
        command_id,
        host_name,
        joined_command,
        data is not None and (' < "%s"' % data) or '',
    )
    channel.exec_command(joined_command)
    if data is not None:
        channel.send(data)
    channel.shutdown_write()
    return_code, out, err = drain_ssh_channel(
        channel, **(show_output and {} or {
            'stdout': None,
            'stderr': None
        })
    )
    channel.close()
    transport.close()
    client.close()

    LOGGER.debug(
        'Command %s on %s returned with %d',
        command_id,
        host_name,
        return_code,
    )

    if out:
        LOGGER.debug(
            'Command %s on %s output:\n %s',
            command_id,
            host_name,
            out,
        )
    if err:
        LOGGER.debug(
            'Command %s on %s  errors:\n %s',
            command_id,
            host_name,
            err,
        )
    return command_status.CommandStatus(out, err, return_code)


def drain_ssh_channel(chan, stdin=None, stdout=sys.stdout, stderr=sys.stderr):
    chan.settimeout(0)
    out_queue = []
    out_all = []
    err_queue = []
    err_all = []

    try:
        stdout_is_tty = stdout.isatty()
        tty_w = tty_h = -1
    except AttributeError:
        stdout_is_tty = False

    done = False
    while not done:
        if stdout_is_tty:
            arr = array.array('h', range(4))
            if not fcntl.ioctl(stdout.fileno(), termios.TIOCGWINSZ, arr):
                if tty_h != arr[0] or tty_w != arr[1]:
                    tty_h, tty_w = arr[:2]
                    chan.resize_pty(width=tty_w, height=tty_h)

        read_streams = []
        if not chan.closed:
            read_streams.append(chan)

            if stdin and not stdin.closed:
                read_streams.append(stdin)

        write_streams = []
        if stdout and out_queue:
            write_streams.append(stdout)
        if stderr and err_queue:
            write_streams.append(stderr)

        read, write, _ = select.select(
            read_streams,
            write_streams,
            [],
            0.1,
        )

        if stdin in read:
            chunk = utils.read_nonblocking(stdin)
            if chunk:
                chan.send(chunk)
            else:
                chan.shutdown_write()

        try:
            if chan.recv_ready():
                chunk = chan.recv(1024)
                if stdout:
                    out_queue.append(chunk)
                out_all.append(chunk)

            if chan.recv_stderr_ready():
                chunk = chan.recv_stderr(1024)
                if stderr:
                    err_queue.append(chunk)
                err_all.append(chunk)
        except socket.error:
            pass

        if stdout in write:
            out = out_queue.pop(0)
            try:
                stdout.write(out)
            except TypeError:
                stdout.write(out.decode('utf-8'))
            stdout.flush()
        if stderr in write:
            err = err_queue.pop(0)
            try:
                stderr.write(err)
            except TypeError:
                stderr.write(err.decode('utf-8'))
            stderr.flush()

        if chan.closed and not out_queue and not err_queue:
            done = True

    return (chan.exit_status, b''.join(out_all), b''.join(err_all))


def _gen_ssh_command_id():
    return uuid.uuid1().hex[:8]


def get_ssh_client(
    ip_addr,
    ssh_key=None,
    host_name=None,
    ssh_tries=None,
    username='root',
    password='123456',
):
    """
    Get a connected SSH client

    Args:
        ip_addr(str): IP address of the endpoint
        ssh_key(str or list of str): Path to a file which
            contains the private key
        hotname(str): The hostname of the endpoint
        ssh_tries(int): The number of attempts to connect to the endpoint
        username(str): The username to authenticate with
        password(str): Used for password authentication
            or for private key decryption

    Raises:
        :exc:`~OSTSSHTimeoutException`: If the client failed to connect after
            "ssh_tries"
    """
    host_name = host_name or ip_addr
    LOGGER.debug('Get ssh client for %s', host_name)
    ssh_timeout = int(SSH_TIMEOUT_DEFAULT)
    if ssh_tries is None:
        ssh_tries = int(SSH_TRIES_DEFAULT)

    start_time = time.time()
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy(), )
    while ssh_tries > 0:
        try:
            client.connect(
                ip_addr,
                username=username,
                password=password,
                key_filename=ssh_key,
                timeout=ssh_timeout,
            )
            break
        except (socket.error, socket.timeout) as err:
            LOGGER.debug(
                'Socket error connecting to %s: %s',
                host_name,
                err,
            )
        except paramiko.ssh_exception.SSHException as err:
            LOGGER.debug(
                'SSH error connecting to %s: %s',
                host_name,
                err,
            )
        except EOFError as err:
            LOGGER.debug('EOFError connecting to %s: %s', host_name, err)
        ssh_tries -= 1
        LOGGER.debug(
            'Still got %d tries for %s',
            ssh_tries,
            host_name,
        )
        time.sleep(1)
    else:
        end_time = time.time()
        raise OSTSSHTimeoutException(
            'Timed out (in %d s) trying to ssh to %s' %
            (end_time - start_time, host_name)
        )
    return client


class OSTSSHTimeoutException(Exception):
    pass
