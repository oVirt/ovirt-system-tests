#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
import pytest

from ovirtlib import templatelib
from ovirtlib.sdkentity import EntityNotFoundError

from ost_utils.ansible import collection

# cirros image is baked into engine and HE ost images, can be found in
# the ost-images project: mk/engine-installed.mk and mk/he-installed.mk
CIRROS_IMAGE_PATH = '/usr/share/ovirt-system-tests/cirros.img'
ENGINE_CA_PEM = '/etc/pki/ovirt-engine/ca.pem'
ONE_GIG = '1GiB'


@pytest.fixture(scope='session')
def cirros_template(
    system,
    default_cluster,
    default_storage_domain,
    ansible_engine,
    ansible_inventory,
    engine_full_username,
    engine_password,
    cirros_image_template_name,
    engine_facts,
    ssh_key_file,
):
    try:
        templatelib.get_template(system, cirros_image_template_name)
    except EntityNotFoundError:
        collection.image_template(
            ansible_engine,
            ansible_inventory,
            ssh_key_path=ssh_key_file,
            engine_hostname=engine_facts.hostname,
            engine_fqdn=engine_facts.fqdn,
            engine_user=engine_full_username,
            engine_password=engine_password,
            engine_cafile=ENGINE_CA_PEM,
            qcow_url=f'file://{CIRROS_IMAGE_PATH}',
            template_cluster=default_cluster.name,
            template_name=cirros_image_template_name,
            template_memory=ONE_GIG,
            template_cpu='1',
            template_disk_size=ONE_GIG,
            template_disk_storage=default_storage_domain.name,
            template_seal=False,
            template_nics=[],
        )
        templatelib.wait_for_template_ok_status(system, cirros_image_template_name)
    return cirros_image_template_name
