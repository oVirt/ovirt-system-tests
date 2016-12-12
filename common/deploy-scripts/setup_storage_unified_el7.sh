#!/bin/bash -xe
set -xe
MAIN_NFS_DEV="disk/by-id/scsi-0QEMU_QEMU_HARDDISK_2"
EXPORTED_DEV="disk/by-id/scsi-0QEMU_QEMU_HARDDISK_3"
ISCSI_DEV="disk/by-id/scsi-0QEMU_QEMU_HARDDISK_4"
NUM_LUNS=5


setup_device() {
    local device=$1
    local mountpath=$2
    local exportpath=$3
    mkdir -p ${mountpath}
    mkfs.xfs -K /dev/${device}
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
    yum install -y --downloaddir=/dev/shm \
                   nfs-utils \
                   rpcbind \
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
    pvcreate /dev/${ISCSI_DEV}
    vgcreate vg1_storage /dev/${ISCSI_DEV}
    targetcli /iscsi create iqn.2014-07.org.ovirt:storage
    targetcli /iscsi/iqn.2014-07.org.ovirt:storage/tpg1/portals \
        delete 0.0.0.0 3260
    targetcli /iscsi/iqn.2014-07.org.ovirt:storage/tpg1/portals \
        create ::0

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
        set auth userid=username password=password
    targetcli /iscsi/iqn.2014-07.org.ovirt:storage/tpg1 \
        set attribute demo_mode_write_protect=0 generate_node_acls=1 cache_dynamic_acls=1 default_cmdsn_depth=64
    targetcli saveconfig

    systemctl enable target
    systemctl start target
    sed -i 's/#node.session.auth.authmethod = CHAP/node.session.auth.authmethod = CHAP/g' /etc/iscsi/iscsid.conf
    sed -i 's/#node.session.auth.username = username/node.session.auth.username = username/g' /etc/iscsi/iscsid.conf
    sed -i 's/#node.session.auth.password = password/node.session.auth.password = password/g' /etc/iscsi/iscsid.conf

    iscsiadm -m discovery -t sendtargets -p 127.0.0.1
    iscsiadm -m node -L all
    rescan-scsi-bus.sh
    lsscsi -i |grep 36 |awk '{print $NF}' |sort > /root/multipath.txt
    iscsiadm -m node -U all
    iscsiadm -m node -o delete
    systemctl stop iscsi.service
    systemctl disable iscsi.service

}

disable_firewalld() {
    if rpm -q firewalld > /dev/null; then
        {
            systemctl disable firewalld
            systemctl stop firewalld
        }
    fi
}

setup_services() {
    systemctl stop postfix
    systemctl disable postfix
    systemctl stop wpa_supplicant
    systemctl disable wpa_supplicant
    disable_firewalld
    systemctl start rpcbind.service
    systemctl start nfs-server.service
    systemctl start nfs-lock.service
    systemctl start nfs-idmap.service
    systemctl enable rpcbind.service
    systemctl enable nfs-server.service
}


install_deps_389ds() {
    yum install -y --downloaddir=/dev/shm 389-ds-base
}

setup_389ds() {
    DOMAIN=lago.local
    PASSWORD=12345678
    HOSTNAME=$(hostname | sed s/_/-/g)."$DOMAIN"
    ADDR=$(\
      /sbin/ip -4 -o addr show dev eth0 \
      | awk '{split($4,a,"."); print a[1] "." a[2] "." a[3] "." a[4]}'\
      | awk -F/ '{print $1}'\
    )
    cat >> answer_file.inf <<EOC
[General]
FullMachineName= @HOSTNAME@
SuiteSpotUserID= root
SuiteSpotGroup= root
ConfigDirectoryLdapURL= ldap://@HOSTNAME@:389/o=NetscapeRoot
ConfigDirectoryAdminID= admin
ConfigDirectoryAdminPwd= @PASSWORD@
AdminDomain= @DOMAIN@

[slapd]
ServerIdentifier= lago
ServerPort= 389
Suffix= dc=lago, dc=local
RootDN= cn=Directory Manager
RootDNPwd= @PASSWORD@

[admin]
ServerAdminID= admin
ServerAdminPwd= @PASSWORD@
SysUser= dirsrv
EOC

    sed -i 's/@HOSTNAME@/'"$HOSTNAME"'/g' answer_file.inf
    sed -i 's/@PASSWORD@/'"$PASSWORD"'/g' answer_file.inf
    sed -i 's/@DOMAIN@/'"$DOMAIN"'/g' answer_file.inf

    cat >> add_user.ldif <<EOC
dn: uid=user1,ou=People,dc=lago,dc=local
uid: user1
givenName: user1
objectClass: top
objectClass: person
objectClass: organizationalPerson
objectClass: inetorgperson
objectclass: inetuser
sn: user1
cn: user1 user1
userPassword: {SSHA}1e/GY7pCEhoL5yMR8HvjI7+3me6PQtxZ
# Password is 123456
EOC

    /usr/sbin/setup-ds.pl --silent --file=answer_file.inf
    ldapadd -x -H ldap://localhost -D 'cn=Directory Manager' -w $PASSWORD -f add_user.ldif
    systemctl stop dirsrv@lago
}

main() {
    # Prepare storage
    install_deps
    setup_services
    setup_main_nfs
    setup_export
    setup_iso
    setup_iscsi

    # Prepare 389ds
    install_deps_389ds
    setup_389ds

    fstrim -va
}


main
