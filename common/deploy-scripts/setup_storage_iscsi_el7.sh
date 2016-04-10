#!/bin/bash -e
set -xe

NUM_LUNS=5

yum install -y deltarpm

yum install -y \
    qemu-guest-agent lvm2 targetcli iscsi-initiator-utils \
    device-mapper-multipath

echo noop > /sys/block/vdb/queue/scheduler
pvcreate /dev/vdb
vgcreate vg1_storage /dev/vdb
extents=$(vgdisplay vg1_storage | grep 'Total PE' | awk '{print $NF;}')
lvcreate -Zn -l$(($extents - 50)) -T vg1_storage/thinpool

targetcli /iscsi create iqn.2014-07.org.ovirt:storage

create_lun () {
    local ID=$1
    lvcreate \
        vg1_storage -V100G --thinpool vg1_storage/thinpool  -n lun${ID}_bdev
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
sed -i /etc/lvm/lvm.conf \
    -e 's/^\s*# global_filter.*/global_filter = \["r\|\/dev\/vg1_storage\/\*\|" \]/'


systemctl start multipathd
systemctl enable multipathd
systemctl stop firewalld
systemctl disable firewalld
