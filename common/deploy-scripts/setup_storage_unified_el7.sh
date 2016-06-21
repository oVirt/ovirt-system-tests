#!/bin/bash -xe
set -xe
MAIN_NFS_DEV="vdb"
EXPORTED_DEV="vdc"
ISCSI_DEV="vdd"
NUM_LUNS=5


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
    systemctl stop kdump.service
    systemctl disable kdump.service
    yum install -y --disablerepo=base --disablerepo=updates --disablerepo=extras \
                   deltarpm
    yum install -y --disablerepo=base --disablerepo=updates --disablerepo=extras \
                   device-mapper-multipath \
                   nfs-utils \
                   lvm2 \
                   targetcli \
                   sg3_utils \
                   iscsi-initiator-utils
}


setup_iso() {
    mkdir -p /exports/iso
    chmod a+rwx /exports/iso
    echo '/exports/iso/ *(rw,sync,no_root_squash,no_all_squash)' \
    >> /etc/exports
    exportfs -a
}


setup_iscsi() {
    echo noop > /sys/block/${ISCSI_DEV}/queue/scheduler
    pvcreate /dev/${ISCSI_DEV}
    vgcreate vg1_storage /dev/${ISCSI_DEV}
    targetcli /iscsi create iqn.2014-07.org.ovirt:storage

    create_lun () {
       local ID=$1
        lvcreate -L20G -n lun${ID}_bdev vg1_storage
        targetcli \
            /backstores/block \
            create name=lun${ID}_bdev dev=/dev/vg1_storage/lun${ID}_bdev
        targetcli \
            /iscsi/iqn.2014-07.org.ovirt:storage/tpg1/luns/ \
            create /backstores/block/lun${ID}_bdev
    }


    for I in $(seq $NUM_LUNS);
    do
        create_lun $(($I - 1));
    done;

    targetcli /iscsi/iqn.2014-07.org.ovirt:storage/tpg1 \
        set attribute authentication=0 demo_mode_write_protect=0 generate_node_acls=1 cache_dynamic_acls=1
    targetcli saveconfig

    systemctl enable target
    systemctl start target

    iscsiadm -m discovery -t sendtargets -p 127.0.0.1
    iscsiadm -m node -L all

    cat >> /etc/multipath.conf <<EOC
### Based on vdsm configuration
defaults {
    polling_interval            5
    no_path_retry               fail
    user_friendly_names         no
    flush_on_last_del           yes
    fast_io_fail_tmo            5
    dev_loss_tmo                30
    max_fds                     4096
}
blacklist {
    devnode "^vd[a-z]"
}
# Remove devices entries when overrides section is available.
devices {
    device {
        # These settings overrides built-in devices settings. It does not apply
        # to devices without built-in settings (these use the settings in the
        # "defaults" section), or to devices defined in the "devices" section.
        # Note: This is not available yet on Fedora 21. For more info see
        # https://bugzilla.redhat.com/1253799
        all_devs                yes
        no_path_retry           fail
    }
}
EOC

    # this is needed so lvm does not use the iscsi volumes
    #sed -i /etc/lvm/lvm.conf \
    #    -e 's/^\s*# global_filter.*/global_filter = \["r\|\/dev\/vg1_storage\/\*\|" \]/'
}


setup_services() {
    systemctl stop postfix
    systemctl disable postfix
    systemctl stop wpa_supplicant
    systemctl disable wpa_supplicant
    modprobe dm_multipath
    systemctl disable firewalld
    systemctl stop firewalld
    systemctl start rpcbind.service
    systemctl start nfs-server.service
    systemctl start nfs-lock.service
    systemctl start nfs-idmap.service
    systemctl enable rpcbind.service
    systemctl enable nfs-server.service
}


enable_multipath() {
    systemctl enable multipathd
    systemctl start multipathd
}

ipa_install_deps() {
    yum --enablerepo=base install -y deltarpm pm-utils
    yum --enablerepo=base --enablerepo=updates install -y ipa-server
}

ipa_setup_freeipa() {
    DOMAIN=lago.local
    PASSWORD=12345678
    HOSTNAME=$(hostname | sed s/_/-/g)."$DOMAIN"
    REALM=$(echo $DOMAIN | awk '{print toupper($0)}')
    ADDR=$(\
      /sbin/ip -4 -o addr show dev eth0 \
      | awk '{split($4,a,"."); print a[1] "." a[2] "." a[3] "." a[4]}'\
      | awk -F/ '{print $1}'\
    )

    hostname $HOSTNAME
    echo "$ADDR $HOSTNAME" >> /etc/hosts
    ipa-server-install -a $PASSWORD --hostname=$HOSTNAME -r $REALM -p $PASSWORD -n $DOMAIN -U
}

main() {
    # Prepare storage
    install_deps
    setup_services
    setup_main_nfs
    setup_export
    setup_iso
    setup_iscsi
    enable_multipath

    # Prepare FreeIPA
    ipa_install_deps
    ipa_setup_freeipa
}


main
