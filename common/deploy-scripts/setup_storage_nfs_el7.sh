#!/bin/bash -xe
set -xe
EXPORTED_DEV="vdc"
MAIN_NFS_DEV="vdb"

setup_device() {
    local device=$1
    local mountpath=$2
    local exportpath=$3
    mkdir -p ${mountpath}
    echo noop > /sys/block/${device}/queue/scheduler
    mkfs.xfs -K -r extsize=1m /dev/${device}
    echo "/dev/${device} ${mountpath} xfs defaults 0 0" >> /etc/fstab
    mount /dev/${device} ${mountpath}
    mkdir -p ${exportpath}
    chmod a+rwx ${exportpath}
    echo "${exportpath} *(rw,sync,no_root_squash,no_all_squash)" >> /etc/exports
    exportfs -a
}

setup_main_nfs() {
    setup_device ${MAIN_NFS_DEV} /exports/nfs_clean /exports/nfs_clean/share1
}


setup_export() {
    setup_device ${EXPORTED_DEV} /exports/nfs_exported /exports/nfs_exported
}


install_deps() {
    yum install -y deltarpm
    yum install -y nfs-utils
}


setup_iso() {
    mkdir -p /exports/iso
    chmod a+rwx /exports/iso
    echo '/exports/iso/ *(rw,sync,no_root_squash,no_all_squash)' \
    >> /etc/exports
    exportfs -a
}


setup_services() {
    systemctl stop firewalld
    systemctl disable firewalld
    systemctl start rpcbind.service
    systemctl start nfs-server.service
    systemctl start nfs-lock.service
    systemctl start nfs-idmap.service
    systemctl enable rpcbind.service
    systemctl enable nfs-server.service
}

main() {
    install_deps
    setup_services
    setup_main_nfs
    setup_export
    setup_iso
}


main
