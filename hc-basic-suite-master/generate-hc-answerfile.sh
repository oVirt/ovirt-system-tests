#!/bin/bash -e
HOST1IP=$1
HOST2IP=$2
HOST3IP=$3
HOSTEDENGINE=$4
DOMAIN=$5

MYADDR=$(\
    /sbin/ip -4 -o addr show dev eth0 \
    | awk '{split($4,a,"."); print a[1] "." a[2] "." a[3] "." a[4]}'\
    | awk -F/ '{print $1}'\
)
MYHOSTNAME=$(hostname | sed s/_/-/g)

echo "${MYADDR} ${MYHOSTNAME}.${DOMAIN} ${MYHOSTNAME}" >> /etc/hosts

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
echo "${HEADDR} ${HOSTEDENGINE}.${DOMAIN} ${HOSTEDENGINE}" >> /etc/hosts

OVAIMAGE=$(\
    ls /usr/share/ovirt-engine-appliance/ovirt-engine-appliance-*.ova \
    | tail -11\
)
VMPASS=123456
ENGINEPASS=123

sed \
    -e "s,@GW@,${HEGW},g" \
    -e "s,@ADDR@,${HEADDR},g" \
    -e "s,@OVAIMAGE@,${OVAIMAGE},g" \
    -e "s,@VMPASS@,${VMPASS},g" \
    -e "s,@ENGINEPASS@,${ENGINEPASS},g" \
    -e "s,@HOSTEDENGINE@,${HOSTEDENGINE},g" \
    -e "s,@DOMAIN@,${DOMAIN},g" \
    -e "s,@HOST1-IP@,${HOST1IP},g" \
    -e "s,@HOST2-IP@,${HOST2IP},g" \
    -e "s,@HOST3-IP@,${HOST3IP},g" \
    < /root/hc-answers.conf.in \
    > /root/hc-answers.conf
