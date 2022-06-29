#!/bin/bash -xe

coredump_kill() {
    # From time to time we see problems with systemd-cgroups-agent
    # crashing with SIGABRT and systemd-coredump hanging indefinitely
    # eating 100% cpu while trying to generate a coredump from that crash
    # The process name is trimmed to "systemd-coredum"
    cat > /etc/systemd/system/coredump-kill.service <<EOF
[Service]
Type=oneshot
ExecStart=/bin/sh -c "pkill -e systemd-coredum || true"
RemainAfterExit=yes
[Install]
WantedBy=multi-user.target
EOF
    systemctl enable --now coredump-kill
}

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
echo 'log_outputs="1:file:/var/log/libvirt/libvirt.log"' >> /etc/libvirt/libvirtd.conf
sed -i 's/weekly/daily/' /etc/logrotate.d/libvirtd

# Increase ISCSI timeouts and disable MD5 (FIPS), see setup_storage.sh
rpm -q iscsi-initiator-utils || yum install -y iscsi-initiator-utils
sed -i 's/#node.session.auth.authmethod = CHAP/node.session.auth.authmethod = CHAP/g' /etc/iscsi/iscsid.conf
sed -i 's/#node.session.auth.chap_algs =.*/node.session.auth.chap_algs = SHA3-256,SHA256/g' /etc/iscsi/iscsid.conf
sed -i 's/node.conn\[0\].timeo.noop_out_timeout = .*/node.conn\[0\].timeo.noop_out_timeout = 30/g' /etc/iscsi/iscsid.conf

# Unique initiator name
echo "InitiatorName=`/sbin/iscsi-iname`" > /etc/iscsi/initiatorname.iscsi

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

# Configure vdsm-hook-log-console to log the console of the hosted-engine VM
echo 'log_console_vm_regexp=HostedEngine' >> /etc/sysconfig/vdsm

# Requires https://github.com/oVirt/vdsm/pull/271
echo 'log_firmware_vm_regexp=HostedEngine' >> /etc/sysconfig/vdsm
# TODO: I am using this right now with a custom repo, so already enabled. Fix if we eventually want to merge.
# Probably by adding to ost-images.
dnf install -y vdsm-hook-log-firmware || :

coredump_kill
