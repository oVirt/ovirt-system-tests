#!/bin/bash -e
HOST1IP=$1
HOST2IP=$2
HOST3IP=$3
HOSTEDENGINE="hc-engine"
DOMAIN=$(dnsdomainname)
PLAYBOOK_PATH="/etc/ansible/roles/gluster.ansible/playbooks/hc-ansible-deployment"

sed \
    -e "s,@HOST0@,${HOST1IP},g" \
    -e "s,@HOST1@,${HOST2IP},g" \
    -e "s,@HOST2@,${HOST3IP},g" \
    -e "s,@HOSTEDENGINE@,${HOSTEDENGINE},g" \
    -e "s,@DOMAIN@,${DOMAIN},g" \
    < /root/ohc_gluster_inventory.yml.in \
    > ${PLAYBOOK_PATH}/ohc_gluster_inventory.yml


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

# Update the engine address in other hosts too, for auto-addition to work
ssh root@${HOST2IP} "echo "${HEADDR} ${HOSTEDENGINE}.${DOMAIN} ${HOSTEDENGINE}" >> /etc/hosts"
ssh root@${HOST3IP} "echo "${HEADDR} ${HOSTEDENGINE}.${DOMAIN} ${HOSTEDENGINE}" >> /etc/hosts"

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
    -e "s,@HOST0@,${MYHOSTNAME},g" \
    < /root/ohc_he_gluster_vars.json.in \
    > ${PLAYBOOK_PATH}/ohc_he_gluster_vars.json

# Temporary hack till gluster-ansible is updated
sed -i '/gather_facts: no/d'  ${PLAYBOOK_PATH}/tasks/gluster_deployment.yml

cd ${PLAYBOOK_PATH}
export ANSIBLE_HOST_KEY_CHECKING=False
ansible-playbook -i ohc_gluster_inventory.yml hc_deployment.yml --extra-vars='@ohc_he_gluster_vars.json'

RET_CODE=$?
if [ ${RET_CODE} -ne 0 ]; then
    echo "ansible deployment failed with status ${RET_CODE}."
    exit ${RET_CODE}
fi

rm -rf /dev/shm/*.rpm /dev/shm/yum
