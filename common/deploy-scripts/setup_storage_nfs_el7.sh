#!/bin/bash -xe
set -xe
EXPORTED_DEV="/dev/vdc"
MAIN_NFS_DEV="/dev/vdb"

init_disk() {
    local disk_dev="${1?}"
    local cyls i
    parted -s "$disk_dev" mktable msdos
    cyls=$(\
        parted -s "$disk_dev" unit cyl print \
        | grep 'Disk /' \
        | sed -r 's/.*: ([0-9]+)cyl/\1/' \
    )
    parted -s -a optimal "$disk_dev" mkpart primary 0cyl ${cyls}cyl
    for i in {1..10}; do
        partprobe \
        && break \
        || sleep 2
        i=$(($i + 1))
    done
    if [[ "$i" == "11" ]]; then
        echo "Failed to run partprobe"
        return 1
    fi
    return 0
}


setup_export() {
    local device="${1?}"
    init_disk "$device" \
    || exit 1
    sleep 5
    mkfs.xfs -r extsize=1m "${device}1"
    echo "${device}1 /exports/nfs_exported xfs defaults,nodiscard 0 0" \
    >> /etc/fstab
}



install_deps() {
    yum install -y deltarpm
    yum install -y nfs-utils lvm2
}


setup_main_nfs() {
    local device="${1?}"
    local volume_group="vg1_storage"
    local extents partition
    init_disk "$device" \
    || exit 1
    partition="${device}1"

    pvcreate "$partition"
    vgcreate "$volume_group" "$partition"
    extents=$(vgdisplay vg1_storage | grep 'Total PE' | awk '{print $NF;}')
    lvcreate -l $(($extents - 50)) -T "$volume_group"/thinpool
    lvcreate "$volume_group" -V100G --thinpool "$volume_group"/thinpool  -n nfs
    mkfs.xfs -r extsize=1m /dev/mapper/"$volume_group"-nfs
    mkdir -p \
        /exports/nfs_clean/ \
        /exports/nfs_exported/
    echo "/dev/mapper/${volume_group}-nfs /exports/nfs_clean xfs defaults,nodiscard 0 0" \
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
    setup_main_nfs "$main_dev"
    if [[ "$exported_dev" != "no exported" ]]; then
        setup_export "$exported_dev"
    fi
    setup_services
}


main "$MAIN_NFS_DEV"
