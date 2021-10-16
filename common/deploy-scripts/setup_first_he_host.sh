#!/bin/bash -x
HOSTEDENGINE="$1"
shift
HE_MAC_ADDRESS="$1"
shift
HEADDR="$1"
shift

DOMAIN=$(dnsdomainname)
MYHOSTNAME="$(hostname | sed s/_/-/g)"
HE_SETUP_HOOKS_DIR="/usr/share/ansible/collections/ansible_collections/ovirt/ovirt/roles/hosted_engine_setup/hooks"

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

# Use repositories from the host-0 so that we can actually update HE to the same custom repos
dnf_update() {
    cat << EOF > ${HE_SETUP_HOOKS_DIR}/enginevm_before_engine_setup/replace_repos.yml
---
- name: Create systemd service for IPv6 to IPv4 proxy
  lineinfile:
    path: /etc/systemd/system/socks-proxy.service
    create: yes
    line: |
      [Unit]
      Description=socks proxy
      After=network-online.target
      Wants=network-online.target
      [Service]
      ExecStart=sshpass -p $(grep adminPassword hosted-engine-deploy-answers-file.conf  | cut -d: -f2) ssh -D 1234 -N -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null $(hostname -f)
      [Install]
      WantedBy=multi-user.target
- name: Start IPv6 to IPv4 proxy
  systemd:
    name: socks-proxy
    daemon_reload: yes
    enabled: yes
    state: started
- name: Configure DNF to use the proxy
  lineinfile:
    path: /etc/dnf/dnf.conf
    line: |
      proxy=socks5://localhost:1234
      ip_resolve=4
- name: Remove all repositories
  file:
    path: /etc/yum.repos.d
    state: absent
- name: Copy host-0 repositories
  copy:
    src: /etc/yum.repos.d
    dest: /etc
- name: DNF update the system
  dnf:
    name:  "*"
    state: latest
    exclude:
      - ovirt-release-master
      - ovirt-release-master-tested
EOF

}

copy_dependencies() {
    cat << EOF > ${HE_SETUP_HOOKS_DIR}/enginevm_before_engine_setup/copy_dependencies.yml
---
- name: Copy cirros image to HE VM
  copy:
    src: /var/tmp/cirros.img
    dest: /var/tmp/cirros.img
- name: Copy sysstat rpm package to HE VM
  copy:
    src: "{{ item }}"
    dest: /var/tmp/sysstat.rpm
  with_fileglob:
    - "/var/tmp/sysstat-*"
- name: Copy sysstat dependencies to HE VM
  copy:
    src: "{{ item }}"
    dest: /var/tmp/lm_sensors.rpm
  with_fileglob:
    - "/var/tmp/lm_sensors-*"
- name: Copy imageio-client to HE VM
  copy:
    src: /usr/lib64/python3.6/site-packages/ovirt_imageio/client
    dest: /usr/lib64/python3.6/site-packages/ovirt_imageio/
EOF

}

add_he_to_hosts() {
    echo "${HEADDR} ${HOSTEDENGINE}.${DOMAIN} ${HOSTEDENGINE}" >> /etc/hosts
}

# workaround for NM dropping IPv6 routes and prioritize IPv6 resolving in java and imageio since IPv4 routes are missing in dual and ipv6-only modes
fix_ipv6() {
    VIRBR0_SUBNET="--ansible-extra-vars=he_ipv6_subnet_prefix='fd00:1234:5678:900'"
    cat << EOF > ${HE_SETUP_HOOKS_DIR}/enginevm_before_engine_setup/fix_routes.yml
---
- name: Fix IPv6 routes
  shell: |
    sed -i "17i\- name: Fix IPv6 routes\n  shell: ip -6 r add fd00:1234:5678:900::/64 dev virbr0 || true\n" /usr/share/ovirt-engine/ansible-runner-service-project/project/roles/ovirt-host-deploy-vdsm/tasks/restart_services.yml
- name: Resolve IPv6 in engine
  lineinfile:
    path: /etc/ovirt-engine/engine.conf.d/99-ipv6-pref.conf
    create: yes
    line: ENGINE_PROPERTIES="\${ENGINE_PROPERTIES} java.net.preferIPv6Addresses=true"
- name: Resolve IPv6 in imageio
  lineinfile:
    path: /etc/ovirt-imageio/conf.d/01-ipv6-pref.conf
    create: yes
    line: |
      [control]
      prefer_ipv4 = False
EOF

}

copy_ssh_key

dnf_update

copy_dependencies

add_he_to_hosts

ip -6 -o addr show dev eth0 scope global | grep -q eth0 && fix_ipv6

# https://gerrit.ovirt.org/c/ovirt-hosted-engine-setup/+/116925
sed -i "141c\        for amatch in (addressmatchs6list + addressmatchs4list):" /usr/share/ovirt-hosted-engine-setup//plugins/gr-he-common/vm/cloud_init.py

fstrim -va
rm -rf /var/cache/yum/*
hosted-engine --deploy --config-append=/root/hosted-engine-deploy-answers-file.conf ${VIRBR0_SUBNET}
RET_CODE=$?
if [ ${RET_CODE} -ne 0 ]; then
    echo "hosted-engine deploy on ${MYHOSTNAME} failed with status ${RET_CODE}."
    exit ${RET_CODE}
fi
rm -rf /var/cache/yum/*
fstrim -va
