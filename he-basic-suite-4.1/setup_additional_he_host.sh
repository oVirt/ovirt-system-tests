#!/bin/bash -x
HOSTEDENGINE="lago-he-basic-suite-4-1-engine"
DOMAIN=`dnsdomainname`
MYADDR=$(\
    /sbin/ip -4 -o addr show dev eth0 \
    | awk '{split($4,a,"."); print a[1] "." a[2] "." a[3] "." a[4]}'\
    | awk -F/ '{print $1}' \
)

MYHOSTNAME="$(hostname | sed s/_/-/g)"
echo "${MYADDR} ${MYHOSTNAME} ${MYHOSTNAME}.${DOMAIN}" >> /etc/hosts

HEADDR=$(\
    /sbin/ip -4 -o addr show dev eth0 \
    | awk '{split($4,a,"."); print a[1] "." a[2] "." a[3] ".99"}'\
    | awk -F/ '{print $1}' \
)
echo "${HEADDR} ${HOSTEDENGINE} ${HOSTEDENGINE}.${DOMAIN}" >> /etc/hosts

fstrim -va
rm -rf /dev/shm/yum
counter=100
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
    exit 1
fi

rm -rf /dev/shm/yum /dev/shm/*.rpm
fstrim -va
