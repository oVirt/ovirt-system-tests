#!/bin/bash -x
HOSTEDENGINE="$1"
TARGETHOST="$2"
shift

DOMAIN=$(dnsdomainname)
MYHOSTNAME="$(echo ${TARGETHOST} | cut -d. -f1 | sed s/_/-/g)"
STORAGEHOSTNAME="${HOSTEDENGINE/engine/storage}"

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
VMPASS=123456
ENGINEPASS=123

sed \
    -e "s,@GW@,${HEGW},g" \
    -e "s,@ADDR@,${HEADDR},g" \
    -e "s,@VMPASS@,${VMPASS},g" \
    -e "s,@ENGINEPASS@,${ENGINEPASS},g" \
    -e "s,@DOMAIN@,${DOMAIN},g" \
    -e "s,@MYHOSTNAME@,${MYHOSTNAME},g" \
    -e "s,@HOSTEDENGINE@,${HOSTEDENGINE},g" \
    -e "s,@STORAGEHOSTNAME@,${STORAGEHOSTNAME},g" \
    -e "s,@TARGETHOST@,${TARGETHOST},g" \
    < /root/he_deployment.json.in \
    > /root/he_deployment.json

sed \
    -e "s,@TARGETHOST@,${TARGETHOST},g" \
    < /root/hosted_engine_deploy.yml.in \
    > /root/hosted_engine_deploy.yml

fstrim -va
rm -rf /dev/shm/yum
ANSIBLE_SSH_ARGS="-C -o ControlMaster=auto -o ControlPersist=60m" \
    ANSIBLE_SSH_CONTROL_PATH_DIR="~/.ansible/cp" \
    ANSIBLE_SSH_CONTROL_PATH="%(directory)s/ansible-ssh-%%h-%%p-%%r" \
    ANSIBLE_SSH_PIPELINING=True \
    ansible-playbook -i ${TARGETHOST}, /root/hosted_engine_deploy.yml --extra-vars='@/root/he_deployment.json'
RET_CODE=$?
if [ ${RET_CODE} -ne 0 ]; then
    echo "hosted-engine deploy on ${TARGETHOST} failed with status ${RET_CODE}."
    exit ${RET_CODE}
fi
rm -rf /dev/shm/yum /dev/shm/*.rpm
fstrim -va
