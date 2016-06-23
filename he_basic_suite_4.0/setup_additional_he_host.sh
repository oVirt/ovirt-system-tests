#!/bin/bash -e
HOSTEDENGINE="hosted-engine.lago.local"

MYADDR=$(\
    /sbin/ip -4 -o addr show dev eth0 \
    | awk '{split($4,a,"."); print a[1] "." a[2] "." a[3] "." a[4]}'\
    | awk -F/ '{print $1}' \
)
MYHOSTNAME="$(hostname | sed s/_/-/g)"
DOMAIN=".lago.local"
HOSTNUM="${MYHOSTNAME: -1}"
APPHOSTNAME="${MYHOSTNAME//[.-]/_}"

echo "${MYADDR} ${MYHOSTNAME}$DOMAIN" >> /etc/hosts

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
echo "${HEADDR} ${HOSTEDENGINE}" >> /etc/hosts

VMPASS=123456
ENGINEPASS=123

ping -c 220 "${HEADDR}"
sshpass \
    -p "${VMPASS}" \
    ssh -o StrictHostKeyChecking=no "root@${HEADDR}" \
    "echo ${MYADDR}  ${MYHOSTNAME}$DOMAIN >> /etc/hosts"

sed \
    -e "s,@GW@,${HEGW},g" \
    -e "s,@ADDR@,${HEADDR},g" \
    -e "s,@OVAIMAGE@,${OVAIMAGE},g" \
    -e "s,@VMPASS@,${VMPASS},g" \
    -e "s,@ENGINEPASS@,${ENGINEPASS},g" \
    -e "s,@HOSTNAME@,${MYHOSTNAME}$DOMAIN,g" \
    -e "s,@APPHOSTNAME@,${APPHOSTNAME},g" \
    -e "s,@HOSTID@,$((${HOSTNUM}+1)),g" \
    < /root/hosted-engine-deploy-answers-file.conf.in \
    > /root/hosted-engine-deploy-answers-file.conf

systemctl restart network
hosted-engine --deploy --config-append=/root/hosted-engine-deploy-answers-file.conf
