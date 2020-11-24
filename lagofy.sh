#!/bin/bash
[[ "${BASH_SOURCE[0]}" -ef "$0" ]] && { echo "Hey, source me instead! Use: . lagofy.sh [suite]"; exit 1; }

# check dependencies
check_dependencies() {
    [[ -d "$SUITE" ]] || { echo "$SUITE is not a suite directory"; return 2; }
    pip3 install --user -q -r ${OST_REPO_ROOT}/requirements.txt
    # update ost_utils all the time since we don't version it
    pip3 install --user -q -e ost_utils
    sysctl net.ipv6.conf.all.accept_ra | egrep -q 'accept_ra ?= ?2' || {
        echo 'Missing "sysctl -a|grep ipv6|grep accept_ra\ | sed 's/.$/2/' >> /etc/sysctl.conf", then REBOOT!'
        return 4
    }
    [[ $(cat /sys/module/kvm_*/parameters/nested) -eq 1 ]] || {
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
# lago_init [-k key] [-s repo1 repo2 ...]
lago_init() {
    # does not have to be in /var/lib/lago/store
    QCOW=$(realpath "$1")
    [ -n "$QCOW" -a -e "$QCOW" ] || { echo "Image file $1 doesn't exist"; return 1; }
    local engine_image=${QCOW/-host/-engine}
    local host_image=${QCOW/-engine/-host}
    [[ "$2" = "-k" ]] && { LAGO_INIT_SSH_KEY="--ssh-key $3 --skip-bootstrap"; shift 2; }

    # cleanup
    [[ -d "$PREFIX" ]] && { lago stop || true ; rm -rf "$PREFIX"; echo "Removed existing $PREFIX"; }

    echo "Using images $(rpm -qf $host_image 2>/dev/null || echo $host_image), $(rpm -qf $engine_image 2>/dev/null || echo $engine_image) containing "
    egrep -h '(^ovirt-engine-4|^vdsm-4).*' ${engine_image/.qcow2/-pkglist-diff.txt} ${host_image/.qcow2/-pkglist-diff.txt}

    # final lago init file
    local add_repo=0
    cat << EOT > add_plain_repos.sh
#!/bin/bash # generated file
dnf config-manager --disable \*
mkdir -p /tmp/dummy/repodata
echo '<repomd> <data type="primary"> <location href="repodata/primary.xml"/> </data> </repomd>' > /tmp/dummy/repodata/repomd.xml
echo '<metadata packages="0"/>' > /tmp/dummy/repodata/primary.xml
echo -e "[dummy]\nname=dummy\nbaseurl=/tmp/dummy" > /etc/yum.repos.d/dummy.repo
EOT
    if [[ "$2" = "-s" ]]; then # inject additional repos
        echo "touch /etc/yum.repos.d/lagofy.repo" >> add_plain_repos.sh
        while [[ -n "$3" ]]; do
            shift; let add_repo++; echo "Add repo $add_repo: $2"
            echo 'echo -e "[lagofy'${add_repo}']\nname=lagofy'${add_repo}'\nbaseurl='${2}'\ngpgcheck=0\nmodule_hotfixes=1\nsslverify=0\n" >> /etc/yum.repos.d/lagofy.repo' >> add_plain_repos.sh
        done
        echo "dnf upgrade --nogpgcheck -y" >> add_plain_repos.sh
    fi
    suite_name="$SUITE_NAME" engine_image=$engine_image host_image=$host_image use_ost_images=1 add_plain_repos=1 python3 common/scripts/render_jinja_templates.py "${SUITE}/LagoInitFile.in" > "${SUITE}/LagoInitFile"

    lago init $LAGO_INIT_SSH_KEY "$PREFIX" "$SUITE/LagoInitFile"

    # start the OST VMs, run deploy scripts and generate hosts for ansible tasks
    lago start && lago deploy && lago ansible_hosts > $PREFIX/hosts

    # ... and that's it
}

# $@ test scenarios .py files, relative to OST_REPO_ROOT e.g. basic-suite-master/test-scenarios/test_002_bootstrap.py
# TC individual test to run
_run_tc () {
    local res=0
    local testcase=${@/#/$PWD/}
    cd $PREFIX
    local junitxml_file="$PREFIX/${TC:-$SUITE_NAME}.junit.xml"
    PYTHONPATH="${PYTHONPATH}:${OST_REPO_ROOT}:${SUITE}" python3 -u -B -m pytest \
        -s \
        -v \
        -x \
        ${TC:+-k $TC}\
        --junit-xml="${junitxml_file}" \
        -o junit_family=xunit2 \
        ${testcase[@]} || res=$?
    [[ "$res" -ne 0 ]] && xmllint --format ${junitxml_file}
    cd -
    return "$res"
}
# $1 test scenario .py file
# $2 individual test to run, e.g. test_add_direct_lun_vm0
run_tc() {
    local testcase=$(realpath $1)
    TC=$2 _run_tc "$1"
}

run_tests() {
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

collect_logs() {
    logs="${OST_REPO_ROOT}/test_logs/${SUITE_NAME}/$(date +'%Y-%m-%d_%H:%M:%S')_${scenario##*/}"
    lago collect --output $logs # lago logs
    [ -n "$coverage" ] && python3 ${OST_REPO_ROOT}/common/scripts/generate_vdsm_coverage_report.py $PREFIX ${OST_REPO_ROOT}/exported-artifacts/coverage/
    [ -d "${OST_REPO_ROOT}/exported-artifacts" ] && ls "${OST_REPO_ROOT}/exported-artifacts" | xargs -IX mv "${OST_REPO_ROOT}/exported-artifacts/X" $logs/
}


export OST_REPO_ROOT=$(realpath "$PWD")
export SUITE=${OST_REPO_ROOT}/${1:-basic-suite-master}
SUITE_NAME="${SUITE##*/}"
echo -n "Suite $SUITE_NAME - "
export PREFIX=${OST_REPO_ROOT}/deployment-${SUITE_NAME}
export ANSIBLE_NOCOLOR="1"
export ANSIBLE_INVENTORY_FILE="${PREFIX}/hosts"
export ANSIBLE_HOST_KEY_CHECKING="False"
export ANSIBLE_SSH_CONTROL_PATH_DIR="/tmp"
lago() { /usr/bin/lago --lease_dir "$HOME/.lago" --workdir "$PREFIX" "$@"; }

check_dependencies || return $?

echo "you can run the following:

lago_init <base_qcow_file> [-k key_file] [-s additional_repo ...]
    to initialize the workspace with qcow-host and qcow-engine preinstalled images, and launch lago VMs (with  deployment scripts from LagoInitPlain file)
    add extra repos with -s url1 url2 ...
    use pregenerated ssh key with -k key_file without selinux relabeling
lago status | stop | shell | console ...
    show environment status, shut down VMs, log into a running VM, etc
run_tc <full path to test case file> [test function]
    run single test case file, optionally only a single test case (e.g. \`pwd\`/basic-suite-master/test-scenarios/002_bootstrap.py test_add_role)
run_since <full path to test case file> <test function>
    resume running of test case file after the test function (excluded)
run_tests
    run the whole suite
collect_logs
    grab logs from lago and exported-artifacts and add to test_logs
"
