#!/bin/bash -x
HOSTEDENGINE="$1"
shift
HE_MAC_ADDRESS="$1"
shift
HEADDR="$1"
shift

DOMAIN=$(dnsdomainname)
MYHOSTNAME="$(hostname | sed s/_/-/g)"
STORAGEHOSTNAME="${HOSTEDENGINE/engine/storage}"
VMPASS=123456
ENGINEPASS=123
HE_SETUP_HOOKS_DIR="/usr/share/ansible/collections/ansible_collections/ovirt/ovirt/roles/hosted_engine_setup/hooks"
INTERFACE=eth0
PREFIX=24
HEGW=$(\
    /sbin/ip -4 -o addr show dev ${INTERFACE} scope global \
    | awk '{split($4,a,"."); print a[1] "." a[2] "." a[3] ".1"}'\
    | awk -F/ '{print $1}' \
)

# This is needed in case we're using prebuilt ost-images.
# In this scenario ssh keys are baked in to the qcows (so lago
# doesn't inject its own ssh keys), but HE VM is built from scratch.
copy_ssh_key() {
    cat << EOF > ${HE_SETUP_HOOKS_DIR}/enginevm_before_engine_setup/copy_ssh_key.yml
---
- name: Copy ssh key for root to HE VM
  authorized_key:
    user: root
    key: "{{ lookup('file', '/root/.ssh/authorized_keys') }}"
EOF

}

copy_cirros_image() {
    cat << EOF > ${HE_SETUP_HOOKS_DIR}/enginevm_before_engine_setup/copy_cirros_image.yml
---
- name: Copy cirros image to HE VM
  copy:
    src: /var/tmp/cirros.img
    dest: /var/tmp/cirros.img
EOF

}

add_he_to_hosts() {
    echo "${HEADDR} ${HOSTEDENGINE}.${DOMAIN} ${HOSTEDENGINE}" >> /etc/hosts
}

copy_ssh_key

copy_cirros_image

add_he_to_hosts

sed \
    -e "s,@GW@,${HEGW},g" \
    -e "s,@ADDR@,${HEADDR},g" \
    -e "s,@VMPASS@,${VMPASS},g" \
    -e "s,@ENGINEPASS@,${ENGINEPASS},g" \
    -e "s,@DOMAIN@,${DOMAIN},g" \
    -e "s,@MYHOSTNAME@,${MYHOSTNAME}.${DOMAIN},g" \
    -e "s,@HOSTEDENGINE@,${HOSTEDENGINE},g" \
    -e "s,@STORAGEHOSTNAME@,${STORAGEHOSTNAME},g" \
    -e "s,@INTERFACE@,${INTERFACE},g" \
    -e "s,@PREFIX@,${PREFIX},g" \
    -e "s,@HE_MAC_ADDRESS@,${HE_MAC_ADDRESS},g" \
    < /root/hosted-engine-deploy-answers-file.conf.in \
    > /root/hosted-engine-deploy-answers-file.conf

fstrim -va
rm -rf /var/cache/yum/*
# TODO currently we only pass IPv4 for HE and that breaks on dual stack since host-0 resolves to IPv6 and the setup code gets confused
hosted-engine --deploy --config-append=/root/hosted-engine-deploy-answers-file.conf --ansible-extra-vars=he_force_ip4=true
RET_CODE=$?
if [ ${RET_CODE} -ne 0 ]; then
    echo "hosted-engine deploy on ${MYHOSTNAME} failed with status ${RET_CODE}."
    exit ${RET_CODE}
fi
rm -rf /var/cache/yum/*
fstrim -va
