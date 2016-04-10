#!/bin/bash -xe
set -xe
EXPORTED_DEV="vdc"
MAIN_NFS_DEV="vdb"

setup_export() {
    echo noop > /sys/block/${EXPORTED_DEV}/queue/scheduler
    mkfs.xfs -K -r extsize=1m /dev/"${EXPORTED_DEV}"
    echo "/dev/${EXPORTED_DEV} /exports/nfs_exported xfs defaults 0 0" \
    >> /etc/fstab
}


install_deps() {
    yum install -y deltarpm
    yum install -y nfs-utils lvm2
}


setup_main_nfs() {
    mkdir -p \
        /exports/nfs_clean/ \
        /exports/nfs_exported/
    echo noop > /sys/block/${MAIN_NFS_DEV}/queue/scheduler
    mkfs.xfs -K -r extsize=1m /dev/${MAIN_NFS_DEV}
    echo "/dev/${MAIN_NFS_DEV} /exports/nfs_clean xfs defaults 0 0" \
    >> /etc/fstab

    mount -a
    mkdir -p \
        /exports/nfs_clean/share1/ \
        /exports/nfs_clean/iso/ \
        /exports/iso/

    chmod a+rwx \
        /exports/nfs_clean/share1/ \
        /exports/nfs_clean/iso/ \
        /exports/iso/

    echo '/exports/nfs_clean/share1 *(rw,sync,no_root_squash,no_all_squash)' \
    >> /etc/exports
    echo '/exports/nfs_exported/ *(rw,sync,no_root_squash,no_all_squash)' \
    >> /etc/exports
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
    local main_dev="${1?}"
    local exported_dev="${2:-no exported}"
    install_deps
    setup_main_nfs
    if [[ "$exported_dev" != "no exported" ]]; then
        setup_export
    fi
    setup_services
}


main "$MAIN_NFS_DEV"
