#!bin/bash

_deployment_exists() {
    [[ -d "$PREFIX" ]] || { echo "no deployment"; return 1; }
    return 0
}

_get_uuid() {
    for i in $(virsh net-list --name | grep ^ost); do
        [[ "$PREFIX" = "$(virsh net-dumpxml $i | grep 'ost-working-dir comment' | cut -d \" -f 2)" ]] && { uuid=${i:3:8}; return 0; }
    done
    for i in $(virsh list --name | grep "\-ost-"); do
        [[ "$PREFIX" = "$(virsh dumpxml $i | grep 'ost-working-dir comment' | cut -d \" -f 2)" ]] && { uuid=${i:0:8}; return 0; }
    done
    return 1
}

ost_status() {
    _deployment_exists
    _get_uuid || { echo "no resources running"; return 1; }

    declare -A nets
    for i in $(virsh net-list --name | grep ^ost${uuid}); do
	nets[$i]=$(virsh net-dumpxml $i | if [[ "$1" = "--dump" ]]; then tee -a ${OST_REPO_ROOT}/exported-artifacts/libvirt-nets; else cat; fi | grep "ost-network-type comment" | cut -d \" -f 2)
    done

    echo "Networks:"
    for net in ${!nets[@]}; do echo "  ${nets[$net]}: ${net}"; done
    echo "VMs:"
    for vm_full in $(virsh list --name | grep ^${uuid}); do
        local vm=$(cut -d - -f 2- <<< $vm_full)
        echo "  $vm"
        [[ "$1" = "--dump" ]] && virsh dumpxml $vm_full >> ${OST_REPO_ROOT}/exported-artifacts/libvirt-vms
        vm_nets=$(virsh domiflist $vm_full | grep network | tr -s " " | cut -d " " -f 4)
        echo "   state: $(virsh domstate $vm_full 2>&1)"
        echo "   IP: $(sed -n "/^${vm}/ { s/.*ansible_host=\(.*\) ansible_ssh_p.*/\1/p; q }" $PREFIX/hosts 2>/dev/null || echo unknown)"
        echo -n "   NICs: "
        net_comma=""
        local idx=0
        for net in $vm_nets; do
            echo -en "${net_comma}eth${idx}(${nets[$net]})"
            net_comma=", "
            (( idx++ ))
        done
        echo -ne "\n\n"
    done
    if ! grep -qi 'engine' $PREFIX/hosts && [ -r $PREFIX/ansible_inventory/*engine* ]; then
	echo "Hosted Engine:"
	cat $PREFIX/ansible_inventory/*engine* | sed -n 's/^\([^ ]*\) ansible_host=\([^ ]*\).*/  \1\n   IP: \2/p'
    fi
}

ost_destroy() {
    _get_uuid
    if [[ -n "$uuid" ]]; then
        (
            flock -w 120 9
            virsh net-list --name | grep ^ost${uuid} | xargs -rn1 virsh net-destroy
            virsh list --name | grep ^${uuid} | xargs -rn1 virsh destroy
        ) 9>/tmp/ost.lock
    fi
    [[ -s "$PREFIX/sshd_pid" ]] && { echo "killing IPv6 sshd proxy"; kill $(cat "$PREFIX/sshd_pid"); }
    _deployment_exists && rm -rf "$PREFIX" && echo "removed $PREFIX"
    unset OST_INITIALIZED $(env | grep ^OST_IMAGES_ | cut -d= -f1)
}

# ost_init [-4|-6] [suite] [distro]
ost_init() {

    # _generate_network "host-1-eth1 host-1-eth2 host-2-eth1..."
    # create separate networks for each NIC entry.
    # generate IPs (IPv4, IPv6) on 192.168.$SUBNET.$HOSTIDX where HOSTIDX starts with 2
    # on management network ($management_net) generates DNS entries in form of ost-{suite}-{iface}
    _generate_network() {
        SUBNETHEX=$(printf %x $SUBNET)
        IPV4=
        IPV6=
        HOSTIDX=2
        NET_NAME="ost$UUID-$SUBNET"
        for name in $1; do
            IDXHEX=$(printf "%.2d" ${HOSTIDX})
            nicidx_map[$name]="${HOSTIDX}"
            eth_map[$name]="$NET_TYPE"
            hostname="ost-${SUITE}-${name}"
            ipv4_ip="192.168.${SUBNET}.${HOSTIDX}"
            ipv4_mac="54:52:c0:a8:${SUBNETHEX}:${IDXHEX}"
            ipv6_ip="fd8f:1391:3a82:${SUBNET}::c0a8:${SUBNETHEX}${IDXHEX}"
            ipv6_mac="0:3:0:1:54:52:c0:a8:${SUBNETHEX}:${IDXHEX}"
            [[ -n "$ipv6_only" ]] || dns_entries+="<host ip='${ipv4_ip}'><hostname>${hostname}</hostname></host>"
            [[ -n "$ipv4_only" ]] || dns_entries+="<host ip='${ipv6_ip}'><hostname>${hostname}</hostname></host>"
            nicip_map[$name]="${ipv6_ip}"
            [[ -n "$ipv4_only" ]] && nicip_map[$name]="${ipv4_ip}"
            IPV4+="<host mac='${ipv4_mac}' name='${hostname}' ip='${ipv4_ip}'/>"
            IPV6+="<host id='${ipv6_mac}' name='${hostname}' ip='${ipv6_ip}'/>"
            (( HOSTIDX++ ))
        done
        if [[ "$NET_TYPE" = "$management_net" ]]; then
            # adds all acumulated DNS entries so far, i.e. management network needs to be the last one generated
            DNS="<dns forwardPlainNames='no'>${dns_entries}</dns>"
        else
            DNS="<dns enable='no'/>"
        fi
    }

    # finds unused subnet in the OST range
    _find_free_subnet() {
        SUBNET=$(seq 200 254 | egrep -vw "$(virsh net-list --name | grep ^ost | cut -d- -f2 | tr "\n" '|' | sed 's/^/(/; s/|$/)/')" | head -1)
        [[ -n "$SUBNET" ]] || { echo -e "\nno available subnet"; return 1; }
    }

    # _render <template_file>
    _render() {
        sed "
            s|@UUID@|${UUID}|g;
            s|@PREFIX@|${PREFIX}|g;
            s|@VM_FULLNAME@|${VM_FULLNAME}|g;
            s|@DEPLOY_SCRIPTS@|${DEPLOY_SCRIPTS}|g;
            s|@MEMSIZE@|${MEMSIZE}|g;
            s|@MEMSIZE_NUMA@|$((MEMSIZE/2))|g;
            s|@VCPU_NUM@|${VCPU_NUM}|g;
            s|@CELL_0_VCPUS@|${CELL_0_VCPUS}|g;
            s|@CELL_1_VCPUS@|${CELL_1_VCPUS}|g;
            s|@SERIALLOG@|${SERIALLOG}|g;
            s|@OST_ROOTDISK@|${OST_ROOTDISK}|g;
            s|@DISKS@|${DISKS}|g;
            s|@DISK_DEV@|${DISK_DEV}|g;
            s|@DISK_SERIAL@|${DISK_SERIAL}|g;
            s|@DISK_FILE@|${DISK_FILE}|g;
            s|@NICS@|${NICS}|g;
            s|@NET_NAME@|${NET_NAME}|g;
            s|@NET_TYPE@|${NET_TYPE}|g;
            s|@SUBNET@|${SUBNET}|g;
            s|@SUBNETHEX@|${SUBNETHEX}|g;
            s|@IDXHEX@|${IDXHEX}|g;
            s|@DNS@|${DNS}|g;
            s|@IPV4@|${IPV4}|g;
            s|@IPV6@|${IPV6}|g;
            " "$1"
    }

    # support readable comments in json
    jqr() {
        grep -v '^#' ${ost_conf} | jq -r "$@"
    }

    declare -A net_map=()
    declare -A nicidx_map=()
    declare -A nicip_map=()
    declare -A eth_map=()
    ansible_hosts=
    ipv4_only=; ipv6_only=
    [[ "$1" == "-4" ]] && { ipv4_only=yes; shift; }
    [[ "$1" == "-6" ]] && { ipv6_only=yes; shift; }

    SUITE="${1:-basic-suite-master}"
    OST_IMAGES_DISTRO="${2:-el8stream}"

    [[ -n "$OST_INITIALIZED" ]] || ost_check_dependencies || return $?
    [[ -d "$OST_REPO_ROOT/$SUITE" ]] || { echo "$OST_REPO_ROOT/$SUITE is not a suite directory"; return 1; }

    echo "Suite: $SUITE, distro: $OST_IMAGES_DISTRO, deployment dir: $PREFIX, images:"
    . common/helpers/ost-images.sh

    # TODO: Revert back once rhvh has 8.6 packages
    [[ "$OST_IMAGES_DISTRO" = "rhel8" ]] && OST_IMAGES_NODE="$OST_IMAGES_HOST_INSTALLED"

    [[ -e "$PREFIX" ]] && { echo "deployment already exists"; ost_status; return 1; }
    _get_uuid && { echo "no deployment dir but there is a running environment"; ost_status; return 1; }

    mkdir "$PREFIX"
    mkdir "$PREFIX/logs"
    mkdir "$PREFIX/images"
    chcon -t svirt_image_t "$PREFIX/images" && { echo "SELinux is disabled on the machine"; getenforce; return 1;}

    # generate 8 char UUID common to all resources
    # VMs with name <uuid>-ost-<suite>-<vmname>
    UUID=$(uuidgen | cut -c -8)

    ost_conf="$OST_REPO_ROOT/$SUITE/ost.json"
    [[ -f "$ost_conf" ]] || { echo "no ost.conf in $SUITE"; return 1; }

    # run the whole creation in subshell with a lock so that we do not explode on concurrent network allocation
    [ -f /tmp/ost.lock ] || ( umask 0002; sg qemu "touch /tmp/ost.lock"; )
    (
        flock -w 120 9
        cd "${OST_REPO_ROOT}"

        # parse networks and create them on unused subnets (sorted so that  management is the last one to include all DNS entries)
        dns_entries=
        for NET_TYPE in $(jqr ".networks | to_entries | map ({\"net\":.key} + {\"mgmt\":.value.is_management}) | sort_by(.mgmt==true) | .[].net"); do
            net_template=$(jqr ".networks[\"${NET_TYPE}\"].template")
            [[ "$ipv4_only" ]] && net_template+=".ipv4"
            [[ "$ipv6_only" ]] && net_template+=".ipv6"
            host_nics=$(jqr ".networks[\"${NET_TYPE}\"].nics[]" | tr '\n' ' ')
            [[ -n "$(jqr ".networks[\"${NET_TYPE}\"].is_management // empty")" ]] && management_net=$NET_TYPE
            [[ -r "$net_template" ]] || { echo "net $NET_TYPE: template $net_template does not exist"; return 1; }
            echo -n "Creating network $NET_TYPE, subnet "
            _find_free_subnet || return 1
            echo $SUBNET
            net_map[$NET_TYPE]="$SUBNET"
            _generate_network "$host_nics"
            _render ${net_template} | virsh net-create /dev/stdin || { echo "Network creation failed:"; _render ${net_template}; return 1; }
        done
        [[ -z "$management_net" ]] && { echo "no management network defined"; return 1; }

        # parse VMs and create them
        for VM_NAME in $(jqr ".vms | keys | join(\" \")"); do
            vm_template=$(jqr ".vms[\"${VM_NAME}\"].template")
            echo -n "Creating VM $VM_NAME with NICs "
            [[ -r "$vm_template" ]] || { echo -e "VM $VM_NAME: template $vm_template does not exist"; return 1; }

            # generate VM NICs with network mappings
            NICS=
            for NIC_NAME in $(jqr ".vms[\"${VM_NAME}\"].nics | keys | join(\" \")"); do
                nic_template=$(jqr ".vms[\"${VM_NAME}\"].nics[\"${NIC_NAME}\"].template")
                [[ -r "$nic_template" ]] || { echo -e "\nNIC $NIC_NAME: template $nic_template does not exist"; return 1; }
                net="${eth_map[$NIC_NAME]}"
                echo -n "$NIC_NAME($net) "
                SUBNET="${net_map[$net]}"
                SUBNETHEX=$(printf %x $SUBNET)
                IDXHEX=$(printf %02d ${nicidx_map[$NIC_NAME]})
                [[ "$net" ]] || { echo -e "\nNIC $NIC_NAME not found in list of networks ${eth_map[@]}"; return 1; }
                [[ "$SUBNET" ]] || { echo -e "\nnetwork $net not found in defined networks ${net_map[@]}"; return 1; }
                [[ "$IDXHEX" ]] || { echo -e "\nVM $VM_NAME not found in host ip mappings ${nicidx_map[@]}"; return 1; }
                # ansible IP is on the management network
                [[ "$net" == "$management_net" ]] && ansible_ip="${nicip_map[$NIC_NAME]}"
                NET_NAME="ost$UUID-${SUBNET}"
                NICS+=$(_render ${nic_template} | tr -d "\t\n")
            done

            # deploy scripts
            DEPLOY_SCRIPTS=
            for script in $(jqr ".vms[\"${VM_NAME}\"][\"deploy-scripts\"][]");
                do DEPLOY_SCRIPTS+="<script name=\"${script}\"/>"
            done

            # create root disk
            echo -n " and disks "
            vm_rootdisk_var=$(jqr ".vms[\"${VM_NAME}\"].root_disk_var")
            [[ -r "${!vm_rootdisk_var}" ]] || { echo -e "\nroot disk ${!vm_rootdisk_var} doesn't exist"; return 1; }
            OST_ROOTDISK="${PREFIX}/images/${VM_NAME}-root.qcow2"
            qemu-img create -q -f qcow2 -b ${!vm_rootdisk_var} -F qcow2 $OST_ROOTDISK
            echo -n "root($(basename ${!vm_rootdisk_var})) "

            # create additional empty disks
            DISKS=
            DISK_SERIAL=2
            for DISK_DEV in $(jqr ".vms[\"${VM_NAME}\"].disks | keys | join(\" \")"); do
                disk_template=$(jqr ".vms[\"${VM_NAME}\"].disks[\"${DISK_DEV}\"].template")
                DISK_SIZE=$(jqr ".vms[\"${VM_NAME}\"].disks[\"${DISK_DEV}\"].size")
                [[ -r "${!vm_rootdisk_var}" ]] || { echo -e "\nroot disk ${vm_rootdisk_var}(${!vm_rootdisk_var}) doesn't exist"; return 1; }
                DISK_FILE="$PREFIX/images/${VM_NAME}-${DISK_DEV}.qcow2"
                qemu-img create -q -f qcow2 -o preallocation=metadata "${DISK_FILE}" "${DISK_SIZE}"
                echo -n "${DISK_DEV}(${DISK_SIZE}) "
                DISKS+=$(_render ${disk_template} | tr -d "\t\n")
                (( DISK_SERIAL++ ))
            done

            # create the VM
            VM_FULLNAME="${UUID}-ost-${SUITE}-${VM_NAME}"
            MEMSIZE=$(jqr ".vms[\"${VM_NAME}\"].memory")
            # default to 2 vCPUs and distribute them between NUMA cells
            VCPU_NUM=$(jqr ".vms[\"${VM_NAME}\"].vcpu_num // 2")
            CELL_0_VCPUS="0-$((${VCPU_NUM}/2 - 1))"
            CELL_1_VCPUS="$((${VCPU_NUM}/2))-$((${VCPU_NUM} - 1))"

            SERIALLOG="$PREFIX/logs/$VM_NAME"
            echo
            _render ${vm_template} | virsh create /dev/stdin || { echo "VM creation failed:"; _render ${vm_template}; return 1; }

            # generate ansible inventory line per host:
            # <VM name> ansible_host=<IP> ansible_ssh_private_key_file=<key_file> ansible_ssh_extra_args=<disable updates of known_hosts file>
            ansible_hosts+="ost-${SUITE}-${VM_NAME} ansible_host=${ansible_ip} ansible_ssh_private_key_file=${OST_IMAGES_SSH_KEY} ansible_ssh_extra_args='-o UserKnownHostsFile=/dev/null'\n"

        done

        # final ansible hosts file
        echo -e $ansible_hosts > $PREFIX/hosts

        # start IPv6 SOCKS proxy for DNF in IPv6-only networks
        [[ -n "$ipv6_only" ]] && {
            echo "Starting sshd on ${ssh_addr:=fd8f:1391:3a82:${net_map[$management_net]}::1}"
            sleep 5
            /usr/sbin/sshd -f ${OST_REPO_ROOT}/common/helpers/sshd_config -o PidFile=${PREFIX}/sshd_pid -o AuthorizedKeysFile=${OST_IMAGES_SSH_KEY}.pub -o HostKey=${OST_IMAGES_SSH_KEY} -o AllowUsers=$(id -un) -o ListenAddress=${ssh_addr}
        }

    true ) 9>/tmp/ost.lock || return 1
    ost_status --dump
}

# TODO this can use DNS instead
ost_shell() {
    _deployment_exists || return 1
    if [[ -n "$1" ]]; then
        local ssh=$(sed -n "/^ost/ s/ansible[a-z_]*=//g p" $PREFIX/hosts | while IFS=\  read -r host ip key; do
          [[ "$1" == "${host}" ]] && $(ping -c1 -w1 ${ip} &>/dev/null) && { shift; echo "ssh -t -i ${key} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@${ip} $@"; break; }
          done)
        [ -n "${ssh}" ] || { echo "$1 not running"; return 1; }
        eval ${ssh}
    else
        _get_uuid
        echo -e "ost_shell <host> [command ...]\n"
        virsh list --name | sed -n "/^${uuid}-ost/ s/${uuid}-//p"
    fi
}

ost_console() {
    _get_uuid || return 1
    if [[ -n "$1" ]]; then
        virsh console "${uuid}-$1" --devname serial0
    else
        echo -e "ost_console <host>\n"
        virsh list --name | sed -n "/^${uuid}-ost/ s/${uuid}-//p"
    fi
}

# check dependencies
ost_check_dependencies() {
    ${PYTHON} -V 2>/dev/null | grep -q ^Python || { echo "$PYTHON is not installed"; return 2; }
    mkdir -p "${OST_REPO_ROOT}/exported-artifacts"
    { ${PYTHON} -m pip install --user tox &&
    ${PYTHON} -m tox -r -e deps; } > "${OST_REPO_ROOT}/exported-artifacts/tox-deps.log" || { echo "tox dependencies failed. see tox-deps.log"; return 3; }
    sysctl -ar net.ipv6.conf.\.\*.accept_ra\$ | egrep -q 'accept_ra ?= ?2' || {
        echo 'Missing accept_ra on at least one interface. "sysctl -a|grep ipv6|grep accept_ra\ | sed 's/.$/2/' >> /etc/sysctl.conf", then REBOOT!'
        return 4
    }
    local nested=$(cat /sys/module/kvm_*/parameters/nested)
    [[ "$nested" = 1 ]] || [[ "$nested" = Y ]] || {
        echo "No nesting virtualization support. Fix it!"
        return 5
    }
    virsh -q connect || {
        echo "Can not connect to libvirt. Fix it!"
        return 6
    }
    [[ $(id -G |tr \  "\n" | grep "^$(id -g qemu)$" | wc -l) -ne 1 && $(id -g) -ne 0 ]] && {
        echo "Add your group to qemu's group: \"usermod -a -G qemu $(id -ng)\""
        return 7
    }
    namei -vm $PWD | tail -n+2 | cut -b10 | grep -qv '[xt]' && {
        echo "directory is not accessible to all users"
        namei -vm `pwd`
        return 8
    }
    podman info |grep -A5 '^  search' | grep -q 'docker.io' || {
        sed -i "/^registries.*registry.access.redhat.com/ c registries = ['registry.access.redhat.com', 'registry.redhat.io', 'docker.io', 'quay.io']" /etc/containers/registries.conf
    }
    (source /etc/os-release; [[ $VERSION == 9* ]]) && { ansible-galaxy collection install community.general openstack.cloud >/dev/null || {
        echo "ansible collection failed"
        return 9
    }; }
    export OST_INITIALIZED=yes
    return 0
}

ost_linters() {
    echo "Running linters..."
    [[ -n "$OST_INITIALIZED" ]] || ost_check_dependencies || return $?
    ${PYTHON} -m tox -e docs &>> "${OST_REPO_ROOT}/exported-artifacts/tox-deps.log"
    ${PYTHON} -m tox -q -e flake8,pylint,black,broken-symlinks,copyright-notices
}

# $@ test scenarios .py files, relative to OST_REPO_ROOT e.g. basic-suite-master/test-scenarios/test_002_bootstrap.py
# TC individual test to run
_ost_run_tc () {
    _deployment_exists || return 1
    [[ -n "$OST_INITIALIZED" ]] || ost_check_dependencies || return $?

    local res=0
    local testcase=${@/#/$PWD/}
    local junitxml_file="${OST_REPO_ROOT}/exported-artifacts/junit.xml"
    source "${OST_REPO_ROOT}/.tox/deps/bin/activate"
    PYTHONPATH="${PYTHONPATH}:${OST_REPO_ROOT}:${OST_REPO_ROOT}/${SUITE}" ${PYTHON} -u -B -m pytest \
        -s \
        -v \
        -x \
        ${TC:+-k $TC}\
        --junit-xml="${junitxml_file}" \
        -o junit_family=xunit2 \
        --log-file="${OST_REPO_ROOT}/exported-artifacts/pytest.log" \
        ${CUSTOM_REPOS_ARGS[@]} \
        ${testcase[@]} || res=$?
    [[ "$res" -ne 0 ]] && {
        xmllint --format ${junitxml_file}
        ./common/scripts/parse_junitxml.py ${junitxml_file} "${OST_REPO_ROOT}/exported-artifacts/result.txt"
    }
    which deactivate &> /dev/null && deactivate
    return "$res"
}
# $1 test scenario .py file
# $2 individual test to run, e.g. test_add_direct_lun_vm0
ost_run_tc() {
    local testcase=$(realpath $1)
    TC=$2 _ost_run_tc "$1"
}

# $1=tc file, $2=test name
ost_run_after() {
    { PYTHONPATH="${PYTHONPATH}:${OST_REPO_ROOT}:${OST_REPO_ROOT}/${SUITE}" ${PYTHON} << EOT
exec(open('$1').read())
since=_TEST_LIST.index('$2')
print('%s' % '\n'.join(_TEST_LIST[since+1:]))
EOT
    } | while IFS= read -r i; do
        TC=$i _ost_run_tc $1
        [[ $? -ne 0 ]] && break
    done
}

# ost_run_tests [pytest args ...]
ost_run_tests() {
    ost_linters || return 1

    CUSTOM_REPOS_ARGS="$@"
    TC= _ost_run_tc "${SUITE}/test-scenarios" || { echo "\x1b[31mERROR: Failed running ${SUITE} :-(\x1b[0m"; return 1; }
    echo -e "\x1b[32m ${SUITE} - All tests passed :-) \x1b[0m"
    return 0
}


[[ "${BASH_SOURCE[0]}" -ef "$0" ]] && { echo "Hey, source me instead! Use: . lagofy.sh [OST_REPO_ROOT dir]"; exit 1; }
export OST_REPO_ROOT=$(realpath "$PWD")
export PREFIX="${OST_REPO_ROOT}/deployment"

export SUITE
export OST_IMAGES_DISTRO
export ANSIBLE_NOCOLOR="1"
export ANSIBLE_HOST_KEY_CHECKING="False"
export ANSIBLE_SSH_CONTROL_PATH_DIR="/tmp"
export LIBVIRT_DEFAULT_URI="qemu:///system"
PYTHON=python3.9
PYTHONPATH="${PYTHONPATH}:${OST_REPO_ROOT}"
