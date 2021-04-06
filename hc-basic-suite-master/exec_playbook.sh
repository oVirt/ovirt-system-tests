#!/bin/bash -e
HOST1IP=$1
HOST2IP=$2
HOST3IP=$3
OST_SSH_KEY=$4
HOSTEDENGINE="hc-engine"
DOMAIN=$(dnsdomainname)
MYHOSTNAME=$(hostname | sed s/_/-/g)
PLAYBOOK_PATH="/etc/ansible/roles/gluster.ansible/playbooks/hc-ansible-deployment"
VMPASS=123456
ENGINEPASS=123

sed \
    -e "s,@HOST0@,${HOST1IP},g" \
    -e "s,@HOST1@,${HOST2IP},g" \
    -e "s,@HOST2@,${HOST3IP},g" \
    -e "s,@HOSTEDENGINE@,${HOSTEDENGINE},g" \
    -e "s,@DOMAIN@,${DOMAIN},g" \
    < /root/gluster_inventory.yml.in \
    > ${PLAYBOOK_PATH}/gluster_inventory.yml


MYADDR=$(\
    /sbin/ip -4 -o addr show dev eth0 \
    | awk '{split($4,a,"."); print a[1] "." a[2] "." a[3] "." a[4]}'\
    | awk -F/ '{print $1}'\
)

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
ssh -i ${OST_SSH_KEY} root@${HOST2IP} \
    "echo "${HEADDR} ${HOSTEDENGINE}.${DOMAIN} ${HOSTEDENGINE}" >> /etc/hosts"
ssh -i ${OST_SSH_KEY} root@${HOST3IP} \
    "echo "${HEADDR} ${HOSTEDENGINE}.${DOMAIN} ${HOSTEDENGINE}" >> /etc/hosts"

sed \
    -e "s,@GW@,${HEGW},g" \
    -e "s,@ADDR@,${HEADDR},g" \
    -e "s,@VMPASS@,${VMPASS},g" \
    -e "s,@ENGINEPASS@,${ENGINEPASS},g" \
    -e "s,@HOSTEDENGINE@,${HOSTEDENGINE},g" \
    -e "s,@DOMAIN@,${DOMAIN},g" \
    -e "s,@HOST1-IP@,${HOST1IP},g" \
    -e "s,@HOST2-IP@,${HOST2IP},g" \
    -e "s,@HOST3-IP@,${HOST3IP},g" \
    -e "s,@MYHOSTNAME@,${MYHOSTNAME},g" \
    < /root/ohc_he_gluster_vars.json.in \
    > ${PLAYBOOK_PATH}/ohc_he_gluster_vars.json

# Temporary hack till gluster-ansible is updated
sed -i '/gather_facts: no/d'  ${PLAYBOOK_PATH}/tasks/gluster_deployment.yml

cd ${PLAYBOOK_PATH}
export ANSIBLE_HOST_KEY_CHECKING=False
ansible-playbook -i gluster_inventory.yml \
    hc_deployment.yml \
    --private-key ${OST_SSH_KEY} \
    --extra-vars='@ohc_he_gluster_vars.json'

RET_CODE=$?
if [ ${RET_CODE} -ne 0 ]; then
    echo "ansible deployment failed with status ${RET_CODE}."
    exit ${RET_CODE}
fi

rm -rf /var/cache/yum/* /var/cache/dnf/*
