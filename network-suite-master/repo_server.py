#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#
from http import server
import os
import threading


def create_repo_server(workdir, lago_env):
    REPO_SERVER_PORT = 8585

    mgmt_net = next(net for net in lago_env.get_nets().values() if
                    net.is_management())
    gw = mgmt_net.gw()

    server = _create_http_server(
        listen_ip=gw,
        listen_port=REPO_SERVER_PORT,
        root_dir=os.path.join(workdir, 'current', 'internal_repo'),
    )
    threading.Thread(target=server.serve_forever).start()
    return server


def _create_http_server(listen_ip, listen_port, root_dir):
    return server.HTTPServer(
        (listen_ip, listen_port),
        _generate_request_handler(root_dir),
    )


def _generate_request_handler(root_dir):
    class _BetterHTTPRequestHandler(server.SimpleHTTPRequestHandler):
        __root_dir = root_dir

        def translate_path(self, path):
            t_path = server.SimpleHTTPRequestHandler.translate_path(self, path)
            short_t_path = t_path[len(os.getcwd()):].lstrip('/')

            return os.path.join(self.__root_dir, short_t_path)

        def log_message(self, *args, **kwargs):
            pass

    return _BetterHTTPRequestHandler
