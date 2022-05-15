#!/bin/bash

usage() {
    echo "Usage: $0 [-h|--help] [-y|--assume-yes] [ANSIBLE_EXTRA_VARS_FILE]"
    echo
	echo "For automated scenarios there's --assume-yes option (please note that it"
	echo "will work only if you have passwordless sudo - otherwise you'll still need"
    echo "to provide the sudo password interactively):"
	echo
	echo " ./setup_for_ost.sh -y"
	echo
	echo "some variables from the playbook can be overriden with a YAML/JSON"
	echo "file (see the playbook and ansible for details):"
	echo
	echo " ./setup_for_ost.sh myvars.json"
	echo
	echo "where:"
	echo
	echo " $ cat myvars.json"
	echo
	echo " {"
	echo '     "ost_images_repo_url": "http://other.repo.org/",'
	echo '     "ost_images_rpms": ['
	echo '         "ost-images-rhel8-engine-installed",'
	echo '         "ost-images-rhel8-host-installed"'
	echo "     ]"
	echo " }"
}

while [[ "${#}" -gt 0 ]]; do
    case ${1} in
        -y|--assume-yes)
            ASSUME_YES=1
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            ANSIBLE_EXTRA_VARS_FILE="${1}"
            ;;
    esac
    shift
done

if [[ ${EUID} -eq 0 ]]; then
    echo "This script should be run as a non-root user with sudo access."
    exit 1
fi

source /etc/os-release

ANSIBLE_INSTALLED=$(which ansible-playbook &> /dev/null && echo 1 || echo 0)

if [[ ${ASSUME_YES} -ne 1 ]]; then
    echo "You're running this setup as \"$(whoami)\" user"
    echo "That means you will have to run OST (or use lago in general) as the same user."
    echo "You will still be asked for sudo password during setup to run some commands as root."
    echo
    echo "Please note, that running OST requires ~6.5GBs of space on the root partition constantly"
    echo "and around twice as much during 'dnf update'. If that's a problem, one way to work around"
    echo "is to mount/symlink '/usr/share/ost-images' directory to something more capacious."
    echo
    read -p "Type 'y' if you want to continue " -n 1 -r
    echo
    if [[ ! ${REPLY} =~ ^[Yy]$ ]]; then
        exit 0
    fi
fi

if [[ ${ANSIBLE_INSTALLED} -eq 0 ]]; then
    echo "This script needs ansible to work properly, will install it now..."
    sudo dnf install -y "ansible-core"
    if [[ ${?} -ne 0 ]]; then
        echo "Ansible-core installation failed";
        exit 1;
    fi
fi

echo "This script needs some ansible collections to work properly, will install them now..."
ansible-galaxy collection install ansible.posix community.general
if [[ ${?} -ne 0 ]]; then
    echo "Ansible collection installation failed"
    exit 1
fi

echo "Running the setup playbook..."

if [[ ${ASSUME_YES} -eq 1 ]]; then
    ANSIBLE_ASK_SUDO_PASS_FLAG=""
else
    ANSIBLE_ASK_SUDO_PASS_FLAG="-K"
fi

if [[ -n ${ANSIBLE_EXTRA_VARS_FILE} ]]; then
    ANSIBLE_EXTRA_VARS_FLAG="-e"
    ANSIBLE_EXTRA_VARS_FILE="@${ANSIBLE_EXTRA_VARS_FILE}"
else
    ANSIBLE_EXTRA_VARS_FLAG=""
fi

ansible-playbook \
    --connection=local \
    -i 127.0.0.1, \
    ${ANSIBLE_ASK_SUDO_PASS_FLAG} \
    ${ANSIBLE_EXTRA_VARS_FLAG} ${ANSIBLE_EXTRA_VARS_FILE} \
    common/setup/setup_playbook.yml
