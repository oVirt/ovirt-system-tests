#!/bin/bash
[[ "${BASH_SOURCE[0]}" -ef "$0" ]] && { echo "Hey, source me instead! Use: . lagofy.sh [suite]"; exit 1; }

# check dependencies
check_dependencies() {
    [[ -d "$SUITE" ]] || { echo "$SUITE is not a suite directory"; return 2; }
    python3 -m pip install --user -q tox
    python3 -m tox -r -e deps >/dev/null || { echo "tox dependencies failed. try \"tox -e deps\"."; return 3; }
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
    [[ $(id -G |tr \  "\n" | grep "^$(id -g qemu)$" | wc -l) -ne 1 ]] && {
        echo "Add your group to qemu's group: \"usermod -a -G qemu $(id -ng)\""
        return 7
    }
    namei -vm $PWD | tail -n+2 | cut -b10 | grep -qv x && {
        echo "directory is not accessible to all users"
        namei -vm `pwd`
        return 8
    }
    rpm --quiet -q lago python3-ovirt-engine-sdk4 python3-paramiko ansible python3-ansible-runner openssl || {
        echo Missing mandatory rpm
        return 9
    }
    podman info |grep -A5 '^  search' | grep -q 'docker.io' || {
        sed -i "/^registries.*registry.access.redhat.com/ c registries = ['registry.access.redhat.com', 'registry.redhat.io', 'docker.io', 'quay.io']" /etc/containers/registries.conf
    }
    return 0
}

# init workspace and spin up the VMs
# lago_init [-s repo1 repo2 ...]
lago_init() {
    # does not have to be in /var/lib/lago/store
    QCOW=$(realpath "$1")
    [ -n "$QCOW" -a -e "$QCOW" ] || { echo "Image file $1 doesn't exist"; return 1; }
    local engine_image=${QCOW/-host/-engine}
    local node_image=${QCOW%/*}/node-base.qcow2
    local host_image=${QCOW/-engine/-host}
    local upgrade_image=${host_image/-host-installed/-upgrade}
    local he_image=${host_image/-host/-he}
    local ssh_key=${he_image/-he-installed*/_id_rsa}

    # We need this to make ansible suite working.
    # Remove once we expose the ssh key with the backend
    export OST_IMAGES_SSH_KEY="${ssh_key}"

    local comma="Using images "
    for i in $engine_image $host_image $he_image, $node_image; do echo -n $([ -e $i ] && { echo -n "$comma"; rpm -qf $i &>/dev/null && rpm -qf $i || echo $i; }); comma=", "; done
    echo " containing"
    egrep -sh '(^ovirt-engine-4|^vdsm-4).*' ${engine_image/.qcow2/-pkglist-diff.txt} ${host_image/.qcow2/-pkglist-diff.txt} ${node_image/.qcow2/-pkglist.txt}

    # set pytest arguments for using custom repositories
    CUSTOM_REPOS_ARGS=()
    [[ "$2" = "-n" ]] && { shift; CUSTOM_REPOS_ARGS+=('--skip-custom-repos-check'); }
    if [[ "$2" = "-s" ]]; then # inject additional repos
        while [[ -n "$3" ]]; do
            shift; CUSTOM_REPOS_ARGS+=("--custom-repo=$2")
        done
    fi

    lago_cleanup

    # final lago init file
    suite_name="$SUITE_NAME" engine_image=$engine_image node_image=$node_image host_image=$host_image upgrade_image=$upgrade_image he_image=$he_image use_ost_images=1 python3 common/scripts/render_jinja_templates.py "${LAGO_INIT_FILE_IN}" > "${LAGO_INIT_FILE}"

    lago init --ssh-key ${ssh_key} --skip-bootstrap "$PREFIX" "${LAGO_INIT_FILE}"

    # start the OST VMs, run deploy scripts and generate hosts for ansible tasks
    lago start && lago ansible_hosts > $PREFIX/hosts

    # ... and that's it
}

# $@ test scenarios .py files, relative to OST_REPO_ROOT e.g. basic-suite-master/test-scenarios/test_002_bootstrap.py
# TC individual test to run
_run_tc () {
    local res=0
    local testcase=${@/#/$PWD/}
    local junitxml_file="$PREFIX/${TC:-$SUITE_NAME}.junit.xml"
    source "${OST_REPO_ROOT}/.tox/deps/bin/activate"
    PYTHONPATH="${PYTHONPATH}:${OST_REPO_ROOT}:${SUITE}" python3 -u -B -m pytest \
        -s \
        -v \
        -x \
        ${TC:+-k $TC}\
        --junit-xml="${junitxml_file}" \
        -o junit_family=xunit2 \
        --log-file="${OST_REPO_ROOT}/exported-artifacts/pytest.log" \
        ${CUSTOM_REPOS_ARGS[@]} \
        ${testcase[@]} || res=$?
    [[ "$res" -ne 0 ]] && xmllint --format ${junitxml_file}
    which deactivate &> /dev/null && deactivate
    return "$res"
}
# $1 test scenario .py file
# $2 individual test to run, e.g. test_add_direct_lun_vm0
run_tc() {
    local testcase=$(realpath $1)
    TC=$2 _run_tc "$1"
}

run_tests() {
    run_linters
    TC= _run_tc "${SUITE_NAME}/test-scenarios" || { echo "\x1b[31mERROR: Failed running $SUITE :-(\x1b[0m"; return 1; }
    echo -e "\x1b[32m $SUITE - All tests passed :-) \x1b[0m"
    return 0
}

# $1=tc file, $2=test name
run_since() {
    { PYTHONPATH="${PYTHONPATH}:${OST_REPO_ROOT}:${SUITE}" python3 << EOT
exec(open('$1').read())
since=_TEST_LIST.index('$2')
print('%s' % '\n'.join(_TEST_LIST[since:]))
EOT
    } | while IFS= read -r i; do
        TC=$i _run_tc $1
        [[ $? -ne 0 ]] && break
    done
}

run_linters() {
    echo "Running linters..."
    python3 -m tox -q -e flake8,pylint
}

lago_cleanup() {
    # cleanup lago deployment env $1 (or the default $PREFIX)
    WHAT=${1:-$PREFIX}
    [[ -d "$WHAT" ]] && { lago --workdir "$WHAT" stop || true ; rm -rf "$WHAT"; echo "Removed existing $WHAT"; }
}


export OST_REPO_ROOT=$(realpath "$PWD")
export SUITE=${OST_REPO_ROOT}/${1:-basic-suite-master}
export SUITE_NAME="${SUITE##*/}"
echo -n "Suite $SUITE_NAME - "
export LAGO_INIT_FILE="${SUITE}/LagoInitFile"
export LAGO_INIT_FILE_IN="${LAGO_INIT_FILE}.in"
export PREFIX=${OST_REPO_ROOT}/deployment-${SUITE_NAME}
export ANSIBLE_NOCOLOR="1"
export ANSIBLE_HOST_KEY_CHECKING="False"
export ANSIBLE_SSH_CONTROL_PATH_DIR="/tmp"
export CUSTOM_REPOS_ARGS=()
lago() {
    if [[ "$1" == "shell" && -n "$2" ]]; then
        local ssh=$(sed -n "/^lago/ s/ansible[a-z_]*=//g p" $PREFIX/hosts | while IFS=\  read -r host ip key; do
        [[ "$2" == "${host}" ]] && $(ping -c1 -w1 ${ip} &>/dev/null) && { echo "ssh -t -i ${key} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@${ip}"; break; }
        done)
        [ -n "${ssh}" ] || { echo "$2 not running"; return 1; }
        eval ${ssh}
    else
        /usr/bin/lago --workdir "$PREFIX" "$@"
    fi
}

check_dependencies || return $?

echo "you can run the following:

lago_init <base_qcow_file> [-n] [-s additional_repo ...]
    to initialize the workspace with qcow-host and qcow-engine preinstalled images, and launch lago VMs (with  deployment scripts from LagoInitPlain file)
    add extra repos with -s url1 url2 ..., use -n if you do not want to check whether those repos were actually used
lago status | stop | shell | console ...
    show environment status, shut down VMs, log into a running VM, etc
run_tc <full path to test case file> [test function]
    run single test case file, optionally only a single test case (e.g. \`pwd\`/basic-suite-master/test-scenarios/test_002_bootstrap.py test_add_role)
run_since <full path to test case file> <test function>
    resume running of test case file after the test function (excluded)
run_tests
    run the whole suite
run_linters
    run flake8 and pylint linters
lago_cleanup [workdir]
    stop and remove the running lago environment. [workdir] use different deployment directory than the current suite
"
