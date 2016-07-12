#!/bin/bash -xe
set -xe
HE_DEV="vde"

setup_he_iscsi() {
    echo noop > /sys/block/${HE_DEV}/queue/scheduler
    pvcreate /dev/${HE_DEV}
    vgcreate vg_he_storage /dev/${HE_DEV}
    targetcli /iscsi create iqn.2016-07.org.ovirt-he:storage

    lvcreate -L60G -n lun_he_bdev vg_he_storage
    targetcli \
        /backstores/block \
        create name=lun_he_bdev dev=/dev/vg_he_storage/lun_he_bdev
    targetcli \
        /iscsi/iqn.2016-07.org.ovirt-he:storage/tpg1/luns/ \
        create /backstores/block/lun_he_bdev

    targetcli /iscsi/iqn.2016-07.org.ovirt-he:storage/tpg1 \
        set attribute authentication=0 demo_mode_write_protect=0 generate_node_acls=1 cache_dynamic_acls=1
    targetcli saveconfig

    systemctl restart target

    iscsiadm -m discovery -t sendtargets -p 127.0.0.1
    iscsiadm -m node -L all
}

main() {
    setup_he_iscsi
}

main
