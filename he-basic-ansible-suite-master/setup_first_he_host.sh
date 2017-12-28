#!/bin/bash -x
HOSTEDENGINE="lago-he-basic-ansible-suite-master-engine"
DOMAIN=$(dnsdomainname)
MYADDR=$(\
    /sbin/ip -4 -o addr show dev eth0 \
    | awk '{split($4,a,"."); print a[1] "." a[2] "." a[3] "." a[4]}'\
    | awk -F/ '{print $1}' \
)
MYHOSTNAME="$(hostname | sed s/_/-/g)"

echo "${MYADDR} ${MYHOSTNAME} ${MYHOSTNAME}.${DOMAIN}" >> /etc/hosts

HEGW=$(\
    /sbin/ip -4 -o addr show dev eth0 \
    | awk '{split($4,a,"."); print a[1] "." a[2] "." a[3] ".1"}'\
    | awk -F/ '{print $1}' \
)
HEADDR=$(\
    /sbin/ip -4 -o addr show dev eth0 \
    | awk '{split($4,a,"."); print a[1] "." a[2] "." a[3] ".99"}'\
    | awk -F/ '{print $1}' \
)
echo "${HEADDR} ${HOSTEDENGINE}.${DOMAIN} ${HOSTEDENGINE}" >> /etc/hosts
VMPASS=123456
ENGINEPASS=123

OVAIMAGE=$(\
    ls /usr/share/ovirt-engine-appliance/ovirt-engine-appliance-*.ova \
    | tail -11\
)

sed \
    -e "s,@GW@,${HEGW},g" \
    -e "s,@ADDR@,${HEADDR},g" \
    -e "s,@OVAIMAGE@,${OVAIMAGE},g" \
    -e "s,@VMPASS@,${VMPASS},g" \
    -e "s,@ENGINEPASS@,${ENGINEPASS},g" \
    -e "s,@DOMAIN@,${DOMAIN},g" \
    -e "s,@MYHOSTNAME@,${MYHOSTNAME},g" \
    -e "s,@HOSTEDENGINE@,${HOSTEDENGINE},g" \
    < /root/hosted-engine-deploy-answers-file.conf.in \
    > /root/hosted-engine-deploy-answers-file.conf

fstrim -va
rm -rf /dev/shm/yum
if [ -n "$1" ]; then
    ANSIBLE="--ansible"
else
    ANSIBLE=""
fi
hosted-engine --deploy ${ANSIBLE} --config-append=/root/hosted-engine-deploy-answers-file.conf
RET_CODE=$?
if [ ${RET_CODE} -ne 0 ]; then
    echo "hosted-engine deploy on ${MYHOSTNAME} failed with status ${RET_CODE}."
    exit ${RET_CODE}
fi
rm -rf /dev/shm/yum /dev/shm/*.rpm
fstrim -va
