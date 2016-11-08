#!/bin/bash -x
HOSTEDENGINE="lago-he-basic-suite-4-0-engine"
DOMAIN=`dnsdomainname`
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
echo "${HEADDR} ${HOSTEDENGINE} ${HOSTEDENGINE}.${DOMAIN}" >> /etc/hosts
VMPASS=123456
ENGINEPASS=123

HOSTNUM="${MYHOSTNAME: -1}"

sed \
    -e "s,@GW@,${HEGW},g" \
    -e "s,@ADDR@,${HEADDR},g" \
    -e "s,@OVAIMAGE@,${OVAIMAGE},g" \
    -e "s,@VMPASS@,${VMPASS},g" \
    -e "s,@ENGINEPASS@,${ENGINEPASS},g" \
    -e "s,@DOMAIN@,${DOMAIN},g" \
    -e "s,@MYHOSTNAME@,${MYHOSTNAME},g" \
    -e "s,@HOSTEDENGINE@,${HOSTEDENGINE},g" \
    -e "s,@HOSTID@,$((${HOSTNUM}+1)),g" \
    < /root/hosted-engine-deploy-answers-file.conf.in \
    > /root/hosted-engine-deploy-answers-file.conf

fstrim -va

counter=200
while [ $counter -gt 0 ]
do
    code=`curl --insecure --silent --output /dev/null --write-out '%{http_code}' https://${HOSTEDENGINE}.${DOMAIN}/ovirt-engine/services/health`
    if [ "${code}" == 200 ]; then
        break
    fi
    counter=$(( $counter - 1 ))
    sleep 3
done
if [ ${counter} -eq 0 ]; then
    echo "Could not verify HE health"
    exit ${code}
fi

sshpass -p "${VMPASS}" \
    ssh -o StrictHostKeyChecking=no -o CheckHostIP=no -o ConnectionAttempts=200 \
    root@${HOSTEDENGINE}.${DOMAIN} "echo ${MYADDR} ${MYHOSTNAME} ${MYHOSTNAME}.${DOMAIN} >> /etc/hosts"

hosted-engine --deploy --config-append=/root/hosted-engine-deploy-answers-file.conf
RET_CODE=$?
if [ ${RET_CODE} -ne 0 ]; then
    echo "hosted-engine deploy on ${MYHOSTNAME} failed with status ${RET_CODE}."
    exit ${RET_CODE}
fi
rm -rf /dev/shm/yum /dev/shm/*.rpm
fstrim -va
