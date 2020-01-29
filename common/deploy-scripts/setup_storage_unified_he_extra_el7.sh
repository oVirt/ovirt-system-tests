#!/bin/bash -xe
set -xe
HE_DEV="disk/by-id/scsi-0QEMU_QEMU_HARDDISK_4"


setup_device() {
    local device=$1
    local mountpath=$2
    local exportpath=$3
    mkdir -p "${mountpath}"
    mkfs.xfs -K "/dev/${device}"
    echo "/dev/${device} ${mountpath} xfs defaults 0 0" >> /etc/fstab
    mount "/dev/${device}" "${mountpath}"
    mkdir -p "${exportpath}"
    chmod a+rwx "${exportpath}"
    echo "${exportpath} *(rw,sync,anonuid=36,anongid=36,all_squash)" >> /etc/exports
    exportfs -a
}

setup_he_lun() {
    local lun_name="he_lun0_bdev"

    lvcreate --zero n -L80G -n $lun_name vg1_storage
    targetcli \
        /backstores/block \
        create name=$lun_name dev=/dev/vg1_storage/$lun_name
    targetcli \
        /backstores/block/$lun_name \
        set attribute emulate_tpu=1
    targetcli \
        /iscsi/iqn.2014-07.org.ovirt:storage/tpg1/luns/ \
        create /backstores/block/$lun_name
}

setup_he() {
    setup_device "${HE_DEV}" /exports/nfs_he /exports/nfs_he
    setup_he_lun
}

main() {
    systemctl stop firewalld || true
    systemctl disable firewalld || true
    setup_he
    rm -rf /var/cache/yum/* /var/cache/dnf/*
}

main
