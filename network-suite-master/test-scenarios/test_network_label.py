#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#
from testlib import suite


@suite.skip_suites_below('4.3')
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
