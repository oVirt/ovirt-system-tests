#!/bin/bash -xe

# TODO ugly hack until vdsm works on RHEL 8.5
if [[ $(uname -r | cut -d- -f2 | cut -d. -f1) -ge 337 ]]; then
sed -i "285c\                        'version': mi['version']," /usr/lib/python3.6/site-packages/vdsm/osinfo.py
sed -i "286c\                        'release': mi['release']," /usr/lib/python3.6/site-packages/vdsm/osinfo.py
fi

# Only on ovirt-node
if [[ $(which nodectl) ]]; then
    nodectl check
    echo 3 > /proc/sys/vm/drop_caches
fi

# Set up hugepages
HUGEPAGES=3
for node in /sys/devices/system/node/node*; do
    echo $HUGEPAGES > $node/hugepages/hugepages-2048kB/nr_hugepages;
done

# Configure libvirtd log
mkdir -p /etc/libvirt
# Libvirt logging for debugging qemu vms
# https://www.libvirt.org/kbase/debuglogs.html#targeted-logging-for-debugging-qemu-vms
# NOTE: filter order matters, util must be last to avoid noisy object logs.
echo 'log_filters="1:libvirt 1:qemu 1:conf 1:security 3:event 3:json 3:file 3:object 1:util"' >> /etc/libvirt/libvirtd.conf
echo 'log_outputs="1:file:/var/log/libvirt.log"' >> /etc/libvirt/libvirtd.conf

# Increase ISCSI timeouts and disable MD5 (FIPS), see setup_storage.sh
rpm -q iscsi-initiator-utils || yum install -y iscsi-initiator-utils
sed -i 's/#node.session.auth.authmethod = CHAP/node.session.auth.authmethod = CHAP/g' /etc/iscsi/iscsid.conf
sed -i 's/#node.session.auth.chap_algs =.*/node.session.auth.chap_algs = SHA3-256,SHA256/g' /etc/iscsi/iscsid.conf
sed -i 's/node.conn\[0\].timeo.noop_out_timeout = .*/node.conn\[0\].timeo.noop_out_timeout = 30/g' /etc/iscsi/iscsid.conf

# Unique initiator name
echo "InitiatorName=`/sbin/iscsi-iname`" > /etc/iscsi/initiatorname.iscsi


## add repo for node upgrade suite
source /etc/os-release
if [[ "$VARIANT_ID" =~ "ovirt-node" ]]; then
    cat >/etc/yum.repos.d/latest-node.repo <<EOL
[Latest-Ovirt-Node]
name=Latest ovirt node
baseurl=https://jenkins.ovirt.org/job/ovirt-node-ng-image_master_build-artifacts-el8-x86_64/lastSuccessfulBuild/artifact/exported-artifacts
gpgcheck=0
enabled=1
EOL
fi

# FIPS setup for encrypted VNC
# FIXME this just duplicates what ovirt-vnc-sasl.yml does
if [[ $(cat /proc/sys/crypto/fips_enabled) == 1 ]]; then
    cat > /etc/sasl2/qemu.conf << EOF
mech_list: scram-sha-1
sasldb_path: /etc/sasl2/vnc_passwd.db
EOF
    echo dummy_password | saslpasswd2 -a dummy_db -f /etc/sasl2/vnc_passwd.db dummy_user -p
    chown qemu:qemu /etc/sasl2/vnc_passwd.db
    sed -i "s/^#vnc_sasl =.*/vnc_sasl = 1/" /etc/libvirt/qemu.conf
fi
