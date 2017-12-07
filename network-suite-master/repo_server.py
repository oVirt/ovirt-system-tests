#
# Copyright 2017 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA
#
# Refer to the README and COPYING files for full details of the license
#
import BaseHTTPServer
import os
import threading
from SimpleHTTPServer import SimpleHTTPRequestHandler


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
    return BaseHTTPServer.HTTPServer(
        (listen_ip, listen_port),
        _generate_request_handler(root_dir),
    )


def _generate_request_handler(root_dir):
    class _BetterHTTPRequestHandler(SimpleHTTPRequestHandler):
        __root_dir = root_dir

        def translate_path(self, path):
            t_path = SimpleHTTPRequestHandler.translate_path(self, path)
            short_t_path = t_path[len(os.getcwd()):].lstrip('/')

            return os.path.join(self.__root_dir, short_t_path)

        def log_message(self, *args, **kwargs):
            pass

    return _BetterHTTPRequestHandler
