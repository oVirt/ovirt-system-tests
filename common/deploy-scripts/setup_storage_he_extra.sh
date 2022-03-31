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
    chmod +t "${exportpath}"
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

    # The rest of this function is copied from setup_storage.sh. Keep in sync.
    # TODO: Unite or rewrite some day

    # this is ugly, assumes that dedicated storage VMs (ost-[suite]-storage) use their primary network as storage network, and VMs with co-located engine have a dedicated storage network on eth1 (like basic-suite-master).
    if [[ $(hostname) == *"-storage"* ]]; then
        NIC=eth0
    else
        NIC=eth1
    fi
    IP=$(/sbin/ip -o addr show dev $NIC scope global | tac | awk '{split($4,a,"."); print a[1] "." a[2] "." a[3] "." a[4]}'| awk -F/ '{print $1; exit}')

    iscsiadm -m discovery -t sendtargets -p $IP
    iscsiadm -m node -L all
    rescan-scsi-bus.sh
    # let's try explicit settle as rescan-scis-bus.sh may not do that
    /usr/sbin/udevadm settle
    lsscsi -i | awk '/he_lun/ {print $NF; exit}' > /root/he_multipath.txt
    [[ $(wc -l /root/he_multipath.txt | cut -f1 -d " ") == 1 ]] || { echo "We need to see exactly 1 LUN for hosted-engine:"; lsscsi -i; exit 1; }
    iscsiadm -m node -U all
    iscsiadm -m node -o delete
    systemctl disable --now iscsi.service
}

setup_he() {
    setup_device "${HE_DEV}" /exports/nfs_he2 /exports/nfs_he2
    setup_he_lun
}

main() {
    systemctl stop firewalld || true
    systemctl disable firewalld || true
    setup_he
    rm -rf /var/cache/yum/* /var/cache/dnf/*
}

main
