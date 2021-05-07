#!/usr/bin/env bash -ex

HE_SETUP_HOOKS_DIR="/usr/share/ansible/collections/ansible_collections/ovirt/ovirt/roles/hosted_engine_setup/hooks"

# This is needed in case we're using prebuilt ost-images.
# In this scenario ssh keys are baked in to the qcows (so lago
# doesn't inject its own ssh keys), but HE VM is built from scratch.
copy_ssh_key() {
    cat << EOF > ${HE_SETUP_HOOKS_DIR}/enginevm_before_engine_setup/copy_ssh_key.yml
---
- name: Copy ssh key for root to HE VM
  authorized_key:
    user: root
    key: "{{ lookup('file', '/root/.ssh/authorized_keys') }}"
EOF

}


yum install -y --nogpgcheck ansible gluster-ansible-roles ovirt-hosted-engine-setup ovirt-ansible-hosted-engine-setup ovirt-ansible-repositories ovirt-ansible-engine-setup

rm -rf /var/cache/yum/*

## temporary check
echo "Check install package - gluster-ansible"
rpm -qa| grep gluster-ansible

#DISK_DEV=disk/by-id/0QEMU_QEMU_HARDDISK_4
DISK_DEV=sdc

mkfs.xfs -K /dev/${DISK_DEV}
mount /dev/${DISK_DEV} /var/tmp
chmod 1777 /var/tmp
echo -e "/dev/${DISK_DEV}\t/var/tmp\t\t\txfs\tdefaults\t0 0" >> /etc/fstab

copy_ssh_key
