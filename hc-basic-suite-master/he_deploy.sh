#!/bin/bash

HOST=ost-${SUITE_NAME}-host-
VMPASS=123456
IDENENTITY_KEY="/etc/ssh/ssh_host_rsa_key"
cd $PREFIX

lago shell \
    ${HOST}0 \
    sshpass \
    -p "${VMPASS}" \
    ssh-copy-id -o StrictHostKeyChecking=no \
    -i ${IDENENTITY_KEY}.pub ${HOST}0

lago shell \
    ${HOST}0 \
    sshpass \
    -p "${VMPASS}" \
    ssh-copy-id -o StrictHostKeyChecking=no \
    -i ${IDENENTITY_KEY}.pub ${HOST}1

lago shell \
    ${HOST}0 \
    sshpass \
    -p "${VMPASS}" \
    ssh-copy-id -o StrictHostKeyChecking=no \
    -i ${IDENENTITY_KEY}.pub ${HOST}2

lago shell \
    ${HOST}0 \
    mkdir \
    /etc/ovirt-host-deploy.conf.d/

lago shell \
    ${HOST}1 \
    mkdir \
    /etc/ovirt-host-deploy.conf.d/

lago shell \
    ${HOST}2 \
    mkdir \
    /etc/ovirt-host-deploy.conf.d/

echo "#########################"
echo "Running ansible playbook on ${HOST}0"
if [[ -e "${SUITE}/gluster_inventory.yml.in" ]]; then
    lago copy-to-vm \
        ${HOST}0 \
        "${SUITE}/gluster_inventory.yml.in" \
        /root/gluster_inventory.yml.in
fi
if [[ -e "${SUITE}/ohc_gluster_inventory.yml.in" ]]; then
    lago copy-to-vm \
        ${HOST}0 \
        "${SUITE}/ohc_gluster_inventory.yml.in" \
        /root/ohc_gluster_inventory.yml.in
fi

lago copy-to-vm \
    ${HOST}0 \
    "${SUITE}/ohc_he_gluster_vars.json.in" \
    /root/ohc_he_gluster_vars.json.in

lago copy-to-vm \
    ${HOST}0 \
    "${SUITE}/exec_playbook.sh" \
    /root/exec_playbook.sh

lago shell \
    ${HOST}0 \
    /root/exec_playbook.sh ${HOST}0 ${HOST}1 ${HOST}2 ${IDENENTITY_KEY}

RET_CODE=$?
if [ ${RET_CODE} -ne 0 ]; then
    echo "ansible setup on ${HOST}0 failed with status ${RET_CODE}."
    exit ${RET_CODE}
fi

lago shell \
    ${HOST}0 \
    "fstrim -va"

lago shell \
    ${HOST}1 \
    "fstrim -va"

lago shell \
    ${HOST}2 \
    "fstrim -va"
cd -
