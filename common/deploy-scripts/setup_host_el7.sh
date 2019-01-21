#!/bin/bash -xe
set -ex

HUGEPAGES=3

yum update -y iptables

# Reserving port 54322 for ovirt-imageio-daemon service
# ToDo: this workaround can be removed once either of
# the following bugs are resolved:
# https://bugzilla.redhat.com/show_bug.cgi?id=1528971
# https://bugzilla.redhat.com/show_bug.cgi?id=1528972
sysctl -w net.ipv4.ip_local_reserved_ports=54322

for node in /sys/devices/system/node/node*; do
    echo $HUGEPAGES > $node/hugepages/hugepages-2048kB/nr_hugepages;
done

# Configure libvirtd log
mkdir -p /etc/libvirt
echo 'log_outputs="2:file:/var/log/libvirt.log"' >> /etc/libvirt/libvirtd.conf

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
