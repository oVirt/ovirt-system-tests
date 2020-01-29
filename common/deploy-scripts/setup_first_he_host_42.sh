#!/bin/bash -x
HOSTEDENGINE="$1"
shift

DOMAIN=$(dnsdomainname)
MYADDR=$(\
    /sbin/ip -4 -o addr show dev eth0 \
    | awk '{split($4,a,"."); print a[1] "." a[2] "." a[3] "." a[4]}'\
    | awk -F/ '{print $1}' \
)
MYHOSTNAME="$(hostname | sed s/_/-/g)"
STORAGEHOSTNAME="${HOSTEDENGINE/engine/storage}"

echo "${MYADDR} ${MYHOSTNAME}.${DOMAIN} ${MYHOSTNAME}" >> /etc/hosts

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
INTERFACE=eth0
PREFIX=24

sed \
    -e "s,@GW@,${HEGW},g" \
    -e "s,@ADDR@,${HEADDR},g" \
    -e "s,@VMPASS@,${VMPASS},g" \
    -e "s,@ENGINEPASS@,${ENGINEPASS},g" \
    -e "s,@DOMAIN@,${DOMAIN},g" \
    -e "s,@MYHOSTNAME@,${MYHOSTNAME},g" \
    -e "s,@HOSTEDENGINE@,${HOSTEDENGINE},g" \
    -e "s,@STORAGEHOSTNAME@,${STORAGEHOSTNAME},g" \
    -e "s,@INTERFACE@,${INTERFACE},g" \
    -e "s,@PREFIX@,${PREFIX},g" \
    < /root/hosted-engine-deploy-answers-file.conf.in \
    > /root/hosted-engine-deploy-answers-file.conf

fstrim -va
rm -rf /var/cache/yum/* /var/cache/dnf/*
if [ -n "$1" ]; then
    ANSIBLE="--ansible"
else
    ANSIBLE="--noansible"
fi
hosted-engine --deploy ${ANSIBLE} --config-append=/root/hosted-engine-deploy-answers-file.conf
RET_CODE=$?
if [ ${RET_CODE} -ne 0 ]; then
    echo "hosted-engine deploy on ${MYHOSTNAME} failed with status ${RET_CODE}."
    exit ${RET_CODE}
fi
rm -rf /var/cache/yum/* /var/cache/dnf/*
fstrim -va
