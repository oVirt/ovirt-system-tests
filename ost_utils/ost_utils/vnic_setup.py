#
# Copyright 2017-2021 Red Hat, Inc.
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

from ovirtsdk4.types import (
    VnicProfile,
    Network,
    RegistrationConfiguration,
    RegistrationVnicProfileMapping,
)

from ost_utils import network_utils as nu


class VnicSetup(object):
    def __init__(self):
        self._engine = None
        self._profiles = None
        self._networks = None
        self._registration_configuration = None
        self._nics = None

    @staticmethod
    def vnic_setup():
        return _vnic_setup

    @property
    def engine(self):
        return self._engine

    @property
    def profiles(self):
        return self._profiles

    @property
    def networks(self):
        return self._networks

    @property
    def nics(self):
        return self._nics

    @property
    def registration_configuration(self):
        return self._registration_configuration

    def init(self, engine, vm_name, dc_name, cluster_name):
        self._engine = engine
        self._networks = nu.add_networks(
            engine, dc_name, cluster_name, NETS.values()
        )
        nu.assign_networks_to_cluster(
            engine, cluster_name, self._networks, False
        )
        self._profiles = nu.get_profiles_for(engine, self._networks)
        nu.create_nics_on_vm(engine, vm_name, self._profiles)
        self.create_registration_configuration()

    def remove_some_profiles_and_networks(self):
        nu.remove_profiles(self.engine, self._profiles, FILTERS['profiles'])
        nu.remove_networks(self.engine, self._networks, FILTERS['networks'])

    def _create_mappings(self):
        target_same_as_source = self._create_mapping(
            NETS['target_same_as_source'], NETS['target_same_as_source']
        )

        ovirtmgmt_target = self._create_mapping(
            NETS['to_ovirtmgmt'], 'ovirtmgmt'
        )

        other_target = self._create_mapping(NETS['n4'], NETS['n5'])

        no_profile_target = self._create_mapping(NETS['to_no_profile'], '')

        source_not_exists = self._create_mapping(
            OVF['not_on_engine'], OVF['not_on_engine']
        )

        source_deleted_profile_with_target = self._create_mapping(
            NETS['deleted_profile_with_target'], 'ovirtmgmt'
        )

        source_deleted_network_with_target = self._create_mapping(
            NETS['deleted_network_with_target'], 'ovirtmgmt'
        )

        source_deleted_target_profile_empty_string = self._create_mapping(
            NETS['deleted_profile_to_no_profile'], ''
        )

        source_deleted_target_network_empty_string = self._create_mapping(
            NETS['deleted_network_to_no_profile'], ''
        )

        not_on_engine = self._create_mapping(
            OVF['not_on_engine'], OVF['not_on_engine']
        )

        no_source = self._create_mapping_no_source(OVF['no_source'])

        no_target = self._create_mapping_no_target(NETS['no_target'])

        p4 = next(p for p in self._profiles if p.name == NETS['n4'])
        target_by_id = self._create_mapping_target_id(NETS['n5'], p4.id)

        empty_mapping = RegistrationVnicProfileMapping()

        return (
            target_same_as_source,
            other_target,
            ovirtmgmt_target,
            no_profile_target,
            no_target,
            not_on_engine,
            no_source,
            source_not_exists,
            source_deleted_profile_with_target,
            source_deleted_network_with_target,
            source_deleted_target_profile_empty_string,
            source_deleted_target_network_empty_string,
            target_by_id,
            empty_mapping,
        )

    def _create_mapping_no_source(self, to_name):
        return RegistrationVnicProfileMapping(
            from_=None,
            to=VnicProfile(name=to_name, network=Network(name=to_name)),
        )

    def _create_mapping_no_target(self, from_name):
        return RegistrationVnicProfileMapping(
            from_=VnicProfile(name=from_name, network=Network(name=from_name)),
            to=None,
        )

    def _create_mapping(self, from_name, to_name):
        return RegistrationVnicProfileMapping(
            from_=VnicProfile(name=from_name, network=Network(name=from_name)),
            to=VnicProfile(name=to_name, network=Network(name=to_name)),
        )

    def _create_mapping_target_id(self, from_name, to_id):
        return RegistrationVnicProfileMapping(
            from_=VnicProfile(name=from_name, network=Network(name=from_name)),
            to=VnicProfile(id=to_id),
        )

    def create_registration_configuration(self):
        vnic_profile_mappings = self._create_mappings()
        self._registration_configuration = self._create_registration_config(
            vnic_profile_mappings
        )

    def _create_registration_config(self, vnic_profile_mappings):
        return RegistrationConfiguration(
            vnic_profile_mappings=vnic_profile_mappings
        )

    def assert_results(self, vm_name, cluster_name):
        # get under test entities
        self._nics = nu.get_nics_on(self.engine, vm_name)
        ovirtmgmt_profile = nu.get_profile(
            self.engine, cluster_name, 'ovirtmgmt'
        )

        # assert
        self._assert_profile_on_nic(NETS['n5'], NETS['n4'])
        self._assert_profile_on_nic(NETS['n4'], NETS['n5'])
        self._assert_profile_on_nic(NETS['no_target'], NETS['no_target'])

        self._assert_profile_on_nic(
            NETS['target_same_as_source'], NETS['target_same_as_source']
        )
        self._assert_profile_on_nic(
            NETS['not_in_mapping'], NETS['not_in_mapping']
        )

        self._assert_a_profile_on_nic(NETS['to_ovirtmgmt'], ovirtmgmt_profile)
        self._assert_a_profile_on_nic(
            NETS['deleted_network_with_target'], ovirtmgmt_profile
        )
        self._assert_a_profile_on_nic(
            NETS['deleted_profile_with_target'], ovirtmgmt_profile
        )

        self._assert_no_profile_on_nic(NETS['deleted_profile_to_no_profile'])
        self._assert_no_profile_on_nic(NETS['deleted_network_to_no_profile'])
        self._assert_no_profile_on_nic(NETS['to_no_profile'])

        self._assert_not_found_on_nics(OVF['not_on_engine'])
        self._assert_not_found_on_nics(OVF['no_source'])

    def _assert_profile_on_nic(self, nic_name, profile_name):
        nic = self._filter_named_item(nic_name, self._nics)
        profile = self._filter_named_item(profile_name, self._profiles)
        assert nic.vnic_profile.id == profile.id

    def _assert_a_profile_on_nic(self, nic_name, profile):
        nic = self._filter_named_item(nic_name, self._nics)
        assert nic.vnic_profile.id == profile.id

    def _assert_no_profile_on_nic(self, nic_name):
        nic = self._filter_named_item(nic_name, self._nics)
        assert nic.vnic_profile is None
        assert nic.network is None

    def _assert_not_found_on_nics(self, profile_name):
        nics_with_profiles = nu.filter_nics_with_profiles(self._nics)
        for nic in nics_with_profiles:
            profile = nu.get_profile_for_id(self.engine, nic.vnic_profile.id)
            assert profile.name != profile_name

    def _filter_named_item(self, name, collection):
        return next(item for item in collection if item.name == name)


# network/profile names
NETS = {
    'target_same_as_source': 'TARGET_SAME_AS_SOURCE',
    'to_ovirtmgmt': 'TO_OVIRTMGMT',
    'to_no_profile': 'TO_NO_PROFILE',
    'no_target': 'NO_TARGET',
    'n4': 'N4',
    'n5': 'N5',
    'deleted_profile_with_target': 'DELETED_PROFILE_WITH_TARGET',
    'deleted_network_with_target': 'DELETED_NETWORK_WITH_TARGET',
    'deleted_profile_to_no_profile': 'DELETED_PROFILE_TO_NO_PROFILE',
    'deleted_network_to_no_profile': 'DELETED_NETWORK_TO_NO_PROFILE',
    'not_in_mapping': 'NOT_IN_MAPPING',
}

OVF = {'not_on_engine': 'NOT_ON_ENGINE', 'no_source': 'NO_SOURCE'}

FILTERS = {
    'profiles': lambda p: p.name
    in [
        NETS['deleted_profile_with_target'],
        NETS['deleted_profile_to_no_profile'],
    ],
    'networks': lambda n: n.name
    in [
        NETS['deleted_network_with_target'],
        NETS['deleted_network_to_no_profile'],
    ],
}

_vnic_setup = VnicSetup()
