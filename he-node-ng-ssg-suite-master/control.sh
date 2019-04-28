#!/bin/bash -xe
set -o pipefail

HE_ANSIBLE=1

export SSG_PROFILE="xccdf_org.ssgproject.content_profile_standard"

. "${OST_REPO_ROOT}"/he-basic-suite-master/control.sh

prep_suite() {
    local suite="${SUITE?}"

    render_jinja_templates

    rm -rf ovirt-node-ng-image "${suite}/images" "${HOME}/ovirt-node"
    mkdir -p "${suite}/images"

    # Download node rpm
    reposync -q -n -c "${suite}/reposync-node.repo" -r ovirt-node-ng-master-el7
    local node_rpm=$(find . -name "*image-update*.rpm" -exec realpath {} \;)
    local node_url="file://${node_rpm}"
    local vm_name="ovirt-ngn"

    # Install node-ng rpm to a VM
    git clone https://gerrit.ovirt.org/ovirt-node-ng-image
    ./ovirt-node-ng-image/scripts/node-setup/setup-node-appliance.sh -p ovirt \
                                                               -n ${node_url} \
                                                               -m ${vm_name} -s

    # Give the installed qcow to lago and delete the install-vm
    mv "${HOME}/ovirt-node/${vm_name}.qcow2" "${suite}/images/${vm_name}.qcow2"
    virsh undefine ${vm_name}
    rm -rf "${HOME}/ovirt-node"
}
