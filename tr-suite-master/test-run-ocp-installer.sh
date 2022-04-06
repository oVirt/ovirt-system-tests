#!/bin/sh

usage() {
        cat << __EOF__
Usage: $0 -a ovirt-api-url -u ovirt-user -p ovirt-password -c ovirt-cluster-id -s ovirt-storage-domain-id -w working-directory -o openshift-dir -k ssh_key_file -r prefix -n network-name -v vnic-profile-id -d domain

    -h                         - This help text.
    -a OVIRT_API_URL           - <fqdn>/ovirt-engine/api (def. ${OVIRT_API_URL})
    -u OVIRT_USER              - The oVirt engine user name (def. ${OVIRT_USER})
    -p OVIRT_PASSWD             - The oVirt engine user password (def. ${OVIRT_PASSWD})
    -c OVIRT_CLUSTER_ID        - The oVirt cluster id used by the installer (def. ${OVIRT_CLUSTER_ID})
    -s OVIRT_STORAGE_DOMAIN_ID - The active storage domain used by the installer (def. ${OVIRT_STORAGE_DOMAIN_ID})
    -w WORKING_DIR             - working directory for the scripts (def. ${WORKING_DIR})
    -o OPENSHIFT_DIR           - Openshift-install binary directory (def. ${OPENSHIFT_DIR})
    -k SSH_KEY_FILE            - The SSH key file needed by the installer config (def. ${SSH_KEY_FILE})
    -r PREFIX                  - The prefix that will be used for created master VMs (def. ${PREFIX})
    -n OVIRT_NETWORK_NAME      - The oVirt network name that should be used for the installation (def. ${OVIRT_NETWORK_NAME})
    -v OVIRT_VNIC_PROFILE_ID   - The vNic profile id of OVIRT_NETWORK_NAME (def. ${OVIRT_VNIC_PROFILE_ID})
    -d OVIRT_BASE_DOMAIN       - The oVirt domain address (def. ${OVIRT_BASE_DOMAIN})
__EOF__
}

list_descendants () {

  local children=$(ps -o pid= --ppid "$1")

  for pid in ${children}
  do
    list_descendants "${pid}"
  done
  echo "${children}"

}

os_installer() {

    local op=${1}
    local obj=${2}
    local run_in_background=${3}
    if [[ $run_in_background -eq 0 ]]; then
        TF_LOG=debug OVIRT_CONFIG=${OVIRT_CONFIG} ${OPENSHIFT_DIR}/openshift-install \
            --dir=${CONFIG_DIR} --log-level=debug ${op} ${obj}
    else
        TF_LOG=debug OVIRT_CONFIG=${OVIRT_CONFIG} ${OPENSHIFT_DIR}/openshift-install \
            --dir=${CONFIG_DIR} --log-level=debug ${op} ${obj} &
    fi
}

# Default to OST deployment path
PREFIX=${OST_DEPLOYMENT}

#get parameters
while getopts ha:u:p:c:s:w:o:k:r:n:v:d: option; do
    case $option in
            h) usage; exit 0;;
            a) OVIRT_API_URL="${OPTARG}";;
            u) OVIRT_USER="${OPTARG}";;
            p) OVIRT_PASSWD="${OPTARG}";;
            c) OVIRT_CLUSTER_ID="${OPTARG}";;
            s) OVIRT_STORAGE_DOMAIN_ID="${OPTARG}";;
            w) WORKING_DIR="${OPTARG}";;
            o) OPENSHIFT_DIR="${OPTARG}";;
            k) SSH_KEY_FILE="${OPTARG}";;
            r) PREFIX="${OPTARG}";;
            n) OVIRT_NETWORK_NAME="${OPTARG}";;
            v) OVIRT_VNIC_PROFILE_ID="${OPTARG}";;
            d) OVIRT_BASE_DOMAIN="${OPTARG}";;
    esac
done

source ${WORKING_DIR}/func.sh

# setting up shared env variables
set_env

# validate arguments to the script (this counts vars and flags)
info "validating arguments to the script (this counts vars and flags..."
if [[ "$#" -ne 24 ]]; then
    usage
    exit 1
fi

# local vars

max_vms=4
sleep_in_sec=10

cd ${WORKING_DIR}

# configure go
info "configuring go"

# validate UUID format for OVIRT_CLUSTER_ID and OVIRT_STORAGE_DOMAIN_ID
info "validating UUID format for OVIRT_CLUSTER_ID and OVIRT_STORAGE_DOMAIN_ID"

validate_uuid "OVIRT_CLUSTER_ID" "${OVIRT_CLUSTER_ID}"
validate_uuid "OVIRT_STORAGE_DOMAIN_ID" "${OVIRT_STORAGE_DOMAIN_ID}"
validate_uuid "OVIRT_VNIC_PROFILE_ID" "${OVIRT_VNIC_PROFILE_ID}"

# create ovirt-config.yaml
info "creating ovirt-config.yaml"

mkdir -p ${CONFIG_DIR}

OVIRT_CONFIG="${CONFIG_DIR}/ovirt-config.yaml"

cp -f ${WORKING_DIR}/ovirt-config.yaml.in ${OVIRT_CONFIG}
export OVIRT_CONFIG

# replace vars with real parameters value

sed -i -e 's;OVIRT_API_URL;'"$OVIRT_API_URL"';' \
       -e 's;OVIRT_USER;'"$OVIRT_USER"';' \
       -e 's;OVIRT_PASSWD;'"$OVIRT_PASSWD"';' \
       -e 's;OVIRT_CLUSTER_ID;'"$OVIRT_CLUSTER_ID"';' \
       -e 's;OVIRT_STORAGE_DOMAIN_ID;'"$OVIRT_STORAGE_DOMAIN_ID"';' \
    -e 's;OVIRT_NETWORK_NAME;'"${OVIRT_NETWORK_NAME}"';' \
       ${OVIRT_CONFIG}

if [[ $? -ne 0 ]]; then
    error "Failed to set values on ${OVIRT_CONFIG} file"
fi

# check if OVIRT_CONFIG file exists
info "checking if ${OVIRT_CONFIG}/ file exists"

if [ ! -e "${OVIRT_CONFIG}" ]; then
    error "file ${OVIRT_CONFIG} does not exist"
fi

# create install-config.yaml
info "creating install-config.yaml"

if [ ! -e "${WORKING_DIR}/install-config.yaml.in" ]; then
    error "can not find ${WORKING_DIR}/install-config.yaml.in file"
fi

cp -f ${WORKING_DIR}/install-config.yaml.in ${CONFIG_DIR}/install-config.yaml

# set SSH key
info "set SSH key, prefix, oVirt cluster id, oVirt SD id , oVirt network name"

if [ ! -e ${SSH_KEY_FILE} ]; then
    error "ssh key file ${SSH_KEY_FILE} does not exists"
fi

# generate a unique PREFIX for that run to be used in VM creation and API search

prefix_for_search="${PREFIX}$(( ( RANDOM % 1000 )  + 1 ))"
#limit PREFIX to first 14 chars
PREFIX=${prefix_for_search:0:14}
ssh_key=$( cat ${SSH_KEY_FILE} | cut -f1-2 -d " " )
sed -i  -e 's;SSH_KEY;'"${ssh_key}"';' \
    -e 's;PREFIX;'"${PREFIX}"';' \
    -e 's;OVIRT_CLUSTER_ID;'"${OVIRT_CLUSTER_ID}"';' \
    -e 's;OVIRT_STORAGE_DOMAIN_ID;'"${OVIRT_STORAGE_DOMAIN_ID}"';' \
    -e 's;OVIRT_NETWORK_NAME;'"${OVIRT_NETWORK_NAME}"';' \
    -e 's;OVIRT_VNIC_PROFILE_ID;'"${OVIRT_VNIC_PROFILE_ID}"';' \
    -e 's;OVIRT_BASE_DOMAIN;'"${OVIRT_BASE_DOMAIN}"';' \
    ${CONFIG_DIR}/install-config.yaml

if [[ $? -ne 0 ]]; then
    error "Failed to set values on ${CONFIG_DIR}/install-config.yaml file"
fi

# create cluster
info "creating cluster"

# run the following in background and follow VM creation in order to exit before k8s actions

export OPENSHIFT_INSTALL_OS_IMAGE_OVERRIDE="https://github.com/oVirt/512-byte-vm/releases/download/1.1.0/512-byte-vm.qcow2"
os_installer create cluster 1

installer_pid=$!
info "running openshift-install in background with PID=${installer_pid}"

vms=0

#  waiting for 1 master and 3 worker VMs to be created and up

while [[ ${vms} -ne ${max_vms} ]]; do
    info "waiting for ${max_vms} VMs with prefix ${prefix_for_search} to be created and up and running [ ${vms}/${max_vms} ]"
    vms=$(curl --insecure -s -X \
    GET -H "Accept: application/xml" \
    -u ${OVIRT_USER}:${OVIRT_PASSWD} \
    ${OVIRT_API_URL}/vms/?search=name%3D${prefix_for_search}* \
           | grep "<status>up</status>" \
    | wc -l)

    if [[ $? -ne 0 ]]; then
        error "failed to get VMs using API GET call, please check reported errors"
    fi

    sleep ${sleep_in_sec}
    # checking that background invocation of os installer is still alive
    if [ $(ps -ef | grep "openshift-install" | wc -l) -eq 1 ]; then
        error "Openshift installer exited abnormally, please check logs"
    fi
done

info "1 master and 3 worker VMs were created successfully, [ ${vms}/${max_vms} ]"

# cleanup
info "cleaning background process, bootstrap, cluster VMs and other temp files"

info "stopping background children that run OS installer"
kill $(list_descendants $$)

kill -9 ${installer_pid}

if [[ $? -ne 0 ]]; then
    warn "failed to kill OS installer execution in background, please kill it manually"
fi

info "destroying bootstrap"
os_installer destroy bootstrap 0

if [[ $? -ne 0 ]]; then
    warn "failed to destroy bootstrap"
fi
info "destroying cluster"
os_installer destroy cluster 0
if [[ $? -ne 0 ]]; then
    warn "failed to destroy cluster"
fi

