#!/bin/bash -e
HOSTEDENGINE="hosted-engine.lago.local"

MYADDR=$(\
    /sbin/ip -4 -o addr show dev eth0 \
    | awk '{split($4,a,"."); print a[1] "." a[2] "." a[3] "." a[4]}'\
    | awk -F/ '{print $1}'\
)
MYHOSTNAME=$(hostname | sed s/_/-/g).lago.local

echo "${MYADDR} ${MYHOSTNAME}$DOMAIN" >> /etc/hosts

HEGW=$(\
    /sbin/ip -4 -o addr show dev eth0 \
    | awk '{split($4,a,"."); print a[1] "." a[2] "." a[3] ".1"}'\
    | awk -F/ '{print $1}'\
)
HEADDR=$(\
    /sbin/ip -4 -o addr show dev eth0 \
    | awk '{split($4,a,"."); print a[1] "." a[2] "." a[3] ".99"}'\
    | awk -F/ '{print $1}'\
)

TARGET=iqn.2016-07.org.ovirt-he:storage
STORAGEADDR=$(\
    /sbin/ip -4 -o addr show dev eth0 \
    | awk '{split($4,a,"."); print a[1] "." a[2] "." a[3] ".4"}'\
    | awk -F/ '{print $1}'\
)

echo "${HEADDR} ${HOSTEDENGINE}" >> /etc/hosts

OVAIMAGE=$(\
    ls /usr/share/ovirt-engine-appliance/ovirt-engine-appliance-*.ova \
    | tail -11\
)
VMPASS=123456
ENGINEPASS=123

iscsiadm -m discovery -t sendtargets -p ${STORAGEADDR}
iscsiadm -m node -T ${TARGET} -l
sleep 10
DEV=$(realpath /dev/disk/by-path/ip-${STORAGEADDR}:3260-iscsi-${TARGET}-lun-0)
echo "iSCSI device: ${DEV}"
echo '' >> /etc/multipath.conf
systemctl start multipathd
multipath -l ${DEV}
LUNID=$(multipath -l ${DEV} | head -1 | awk '{ print $1 }')
systemctl stop multipathd

iscsiadm -m node -T ${TARGET} -u

sed \
    -e "s,@GW@,${HEGW},g" \
    -e "s,@ADDR@,${HEADDR},g" \
    -e "s,@OVAIMAGE@,${OVAIMAGE},g" \
    -e "s,@VMPASS@,${VMPASS},g" \
    -e "s,@ENGINEPASS@,${ENGINEPASS},g" \
    -e "s,@STORAGEADDR@,${STORAGEADDR},g" \
    -e "s,@LUNID@,${LUNID},g" \
    < /root/hosted-engine-deploy-answers-file.conf.in \
    > /root/hosted-engine-deploy-answers-file.conf

hosted-engine --deploy --config-append=/root/hosted-engine-deploy-answers-file.conf
