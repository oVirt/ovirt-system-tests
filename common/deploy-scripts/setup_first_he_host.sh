#!/bin/bash -x

# FIXME Workaround for https://bugzilla.redhat.com/2020620
umask 022

HOSTEDENGINE="$1"
shift
HE_MAC_ADDRESS="$1"
shift
HEADDR="$1"
shift

DOMAIN=$(dnsdomainname)
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
    FWD_PARAM="-D 1234" # when host-0 can access IPv4
    ip -4 -o addr show dev eth0 scope global | grep -q eth0 || FWD_PARAM="-L1234:localhost:1234" # when we need to tunnel further to the SOCKS proxy on OST executor
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
      ExecStart=sshpass -p 123456 ssh ${FWD_PARAM} -N -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null $(hostname -f)
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
- name: DNF update the system. TODO remove baseos&appstream once RHV appliance is regularly up to date.
  dnf:
    name:  "*"
    state: latest
    enablerepo: "rhel*-baseos,rhel*-appstream"
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
- name: TODO create empty OpenSCAP profile for now
  copy:
    content: ""
    dest: /root/ost_images_openscap_profile
- name: Stat ost_images_openscap_profile
  stat:
    path: /root/ost_images_openscap_profile
  register: profile_stat
- block:
    - name: Copy RHEL8 OpenSCAP data
      copy:
        src: /root/security-data-oval-com.redhat.rhsa-RHEL8.xml
        dest: /root
    - name: Copy updated RHEL8 OpenSCAP datastream
      copy:
        src: /root/ssg-rhel8-ds.xml
        dest: /root
  when: profile_stat.stat.exists and profile_stat.stat.size > 0
EOF

}

add_he_to_hosts() {
    echo "${HEADDR} ${HOSTEDENGINE}.${DOMAIN} ${HOSTEDENGINE}" >> /etc/hosts
}

# prioritize IPv6 resolving in java and imageio since IPv4 routes are missing in dual and ipv6-only modes
fix_ipv6() {
    cat << EOF > ${HE_SETUP_HOOKS_DIR}/enginevm_before_engine_setup/fix_routes.yml
---
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

# need to block updating appliance. excludepkgs doesn't help since HE code does "dnf install ovirt-engine-appliance"
# and if the package is excluded it fails, we need to convince DNF that current version is good enough.
dnf config-manager --setopt=best=False --save

fstrim -va
rm -rf /var/cache/yum/*
hosted-engine --deploy --config-append=/root/hosted-engine-deploy-answers-file.conf
RET_CODE=$?
if [ ${RET_CODE} -ne 0 ]; then
    echo "hosted-engine deploy on ${HOSTNAME} failed with status ${RET_CODE}."
    exit ${RET_CODE}
fi
rm -rf /var/cache/yum/*
fstrim -va
