#!/bin/bash -xe
set -ex

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

setup_ipv6() {
    NIC="eth1"
    IPV6NET="fd8f:1391:3a82:"
    SUBNET=${IPV6_SUBNET}
    HOST_LOCAL_PREFIX=10
    ADDR_PREFIX=64
    HOST_LOCAL_SUFFIX=$(hostname | awk '{split($0, a, "-"); print a[length(a)]}')
    HOST_COUNT=2
    DOMAIN=$(dnsdomainname)
    LOCAL_HOSTNAME_PREFIX=$(hostname | awk '{gsub(/[^-]*.[^-]*$/,""); print}')
    HOST_NAME="host"
    STORAGE_NAME="storage"
    STORAGE_IP_SUFFIX=200
    HE_NAME="engine"
    HE_SUFFIX=250

    nmcli con modify ${NIC} ipv6.addresses ${IPV6NET}${SUBNET}::${HOST_LOCAL_PREFIX}${HOST_LOCAL_SUFFIX}/${ADDR_PREFIX} \
    ipv6.gateway ${IPV6NET}${SUBNET}::1 ipv6.method manual

    nmcli con modify ${NIC} ipv4.method disabled

    nmcli con up ${NIC}

    for ((i=0;i<${HOST_COUNT};i++)); do
        echo  "${IPV6NET}${SUBNET}::${HOST_LOCAL_PREFIX}${i} ${LOCAL_HOSTNAME_PREFIX}${HOST_NAME}-${i}.${DOMAIN} ${LOCAL_HOSTNAME_PREFIX}${HOST_NAME}-${i}" >> /etc/hosts
    done

    echo "${IPV6NET}${SUBNET}::${STORAGE_IP_SUFFIX} ${LOCAL_HOSTNAME_PREFIX}${STORAGE_NAME}.${DOMAIN} ${LOCAL_HOSTNAME_PREFIX}${STORAGE_NAME}" >> /etc/hosts
    echo "${IPV6NET}${SUBNET}::${HE_SUFFIX} ${LOCAL_HOSTNAME_PREFIX}${HE_NAME}.${DOMAIN} ${LOCAL_HOSTNAME_PREFIX}${HE_NAME}" >> /etc/hosts
}

if [[ $(hostname) == *"ipv6"* ]]; then
    setup_ipv6
fi

# increase ISCSI timeouts, see setup_storage_unified.sh
rpm -q iscsi-initiator-utils || yum install -y iscsi-initiator-utils
sed -i 's/node.conn\[0\].timeo.noop_out_timeout = 5/node.conn\[0\].timeo.noop_out_timeout = 30/g' /etc/iscsi/iscsid.conf

# unique initiator name
echo "InitiatorName=`/sbin/iscsi-iname`" > /etc/iscsi/initiatorname.iscsi

if [[ ! -r /etc/NetworkManager/conf.d/10-stable-ipv6-addr.conf ]]; then
    cat << EOF > /etc/NetworkManager/conf.d/10-stable-ipv6-addr.conf
[connection]
ipv6.addr-gen-mode=0
ipv6.dhcp-duid=ll
ipv6.dhcp-iaid=mac
EOF

    systemctl restart NetworkManager
fi
