#
# Copyright 2019 Red Hat, Inc.
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
from testlib import suite


@suite.skip_suites_below(4.3)
def test_empty_string_on_ovirtmgmt_labels(ovirtmgmt_network):
    """
    Ovirtmgmt has null in label by default (e.g. no labels) and not an empty
    string. No labels is therefore correct state and should be the default
    state right after new deployment. Replacing null with empty string
    leads to problems since it is not a correct form of label.
    """
    network_labels = ovirtmgmt_network.labels()
    assert network_labels == [
        label for label in network_labels if label.id != '']
