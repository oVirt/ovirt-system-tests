#!/bin/bash -x
HOSTEDENGINE="$1"
shift

DOMAIN=$(dnsdomainname)
MYHOSTNAME="$(hostname | sed s/_/-/g)"
STORAGEHOSTNAME="${HOSTEDENGINE/engine/storage}"
VMPASS=123456
ENGINEPASS=123

setup_ipv4() {
    MYADDR=$(\
        /sbin/ip -4 -o addr show dev eth0 \
        | awk '{split($4,a,"."); print a[1] "." a[2] "." a[3] "." a[4]}'\
        | awk -F/ '{print $1}' \
    )

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

    INTERFACE=eth0
    PREFIX=24
}

setup_ipv6() {
    IPV6NET="fd8f:1391:3a82:"
    SUBNET=${IPV6_SUBNET}
    HE_SUFFIX=250
    INTERFACE=eth1
    PREFIX=64

    HOSTNAME_PREFIX=$(hostname | awk '{gsub(/[^-]*.[^-]*$/,""); print}')
    HEGW=${IPV6NET}${SUBNET}::1
    HEADDR=${IPV6NET}${SUBNET}::${HE_SUFFIX}

    cat << EOF > /usr/share/ansible/roles/oVirt.hosted-engine-setup/hooks/enginevm_after_engine_setup/ipv6_dns_setup.yml
---
- name: Add /etc/hosts IPv6 entry for host-1
  lineinfile:
    dest: /etc/hosts
    line: "${IPV6NET}${SUBNET}::101 ${HOSTNAME_PREFIX}host-1"
EOF

    cat << EOF > /usr/share/ansible/roles/oVirt.hosted-engine-setup/hooks/enginevm_after_engine_setup/disable_ssh_dns_lookup.yml
---
- name: Disable SSH reverse DNS lookup
  lineinfile:
    path: /etc/ssh/sshd_config
    regex: "^UseDNS"
    line: "UseDNS no"
- name: Restart sshd to make it effective
  systemd:
    state: restarted
    name: sshd
EOF

}

if [[ $(hostname) == *"ipv6"* ]]; then
    setup_ipv6
else
    setup_ipv4
fi

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
    < /root/hosted-engine-deploy-answers-file.conf.in \
    > /root/hosted-engine-deploy-answers-file.conf

fstrim -va
rm -rf /var/cache/yum/*
hosted-engine --deploy --config-append=/root/hosted-engine-deploy-answers-file.conf
RET_CODE=$?
if [ ${RET_CODE} -ne 0 ]; then
    echo "hosted-engine deploy on ${MYHOSTNAME} failed with status ${RET_CODE}."
    exit ${RET_CODE}
fi
rm -rf /var/cache/yum/*
fstrim -va
