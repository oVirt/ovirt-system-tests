#!/bin/sh

source ./func.sh

usage() {
        cat << __EOF__
Usage: $0 -a ovirt-api-url -u ovirt-user -p ovirt-password -c ovirt-cluster-id -s ovirt-storage-domain-id -w working-directory -k ssh_key_file -r prefix -n network-name -t terraform-pull-request-number -d domain

    -h                         - This help text.
    -a OVIRT_API_URL           - <fqdn>/ovirt-engine/api (def. ${OVIRT_API_URL})
    -u OVIRT_USER              - The oVirt engine user name (def. ${OVIRT_USER})
    -p OVIRT_PASSWD             - The oVirt engine user password (def. ${OVIRT_PASSWD})
    -c OVIRT_CLUSTER_ID        - The oVirt cluster id used by the installer (def. ${OVIRT_CLUSTER_ID})
    -s OVIRT_STORAGE_DOMAIN_ID - The active storage domain used by the installer (def. ${OVIRT_STORAGE_DOMAIN_ID})
    -w WORKING_DIR             - working directory for the scripts (def. ${WORKING_DIR})
    -k SSH_KEY_FILE            - The SSH key file needed by the installer config (def. ${SSH_KEY_FILE})
    -r PREFIX                  - The prefix that will be used for created master VMs (def. ${PREFIX})
    -n OVIRT_NETWORK_NAME      - The oVirt network name that should be used for the installation (def. ${OVIRT_NETWORK_NAME})
    -t TPR_OR_CH_OR_MB         - Teraform PR id or commit hash or master branch to check (def. ${TPR_OR_CH_OR_MB})
    -d OVIRT_BASE_DOMAIN       - The oVirt domain address (def. ${OVIRT_BASE_DOMAIN})
__EOF__
}

#get parameters
while getopts ha:u:p:c:s:w:k:r:n:t:d: option; do
    case $option in
            h) usage; exit 0;;
            a) OVIRT_API_URL="${OPTARG}";;
            u) OVIRT_USER="${OPTARG}";;
            p) OVIRT_PASSWD="${OPTARG}";;
            c) OVIRT_CLUSTER_ID="${OPTARG}";;
            s) OVIRT_STORAGE_DOMAIN_ID="${OPTARG}";;
            w) WORKING_DIR="${OPTARG}";;
            k) SSH_KEY_FILE="${OPTARG}";;
            r) PREFIX="${OPTARG}";;
            n) OVIRT_NETWORK_NAME="${OPTARG}";;
            t) TPR_OR_CH_OR_MB="${OPTARG}";;
            d) OVIRT_BASE_DOMAIN="${OPTARG}";;
    esac
done

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
    TF_LOG=debug OVIRT_CONFIG=${OVIRT_CONFIG} ${INSTALLER_DIR}/bin/openshift-install \
        --dir=${INSTALLER_DIR} ${op} ${obj} --log-level=debug

}

# validate arguments to the script (this counts vars and flags)
info "validating arguments to the script (this counts vars and flags..."
echo "number of args = $#"
if [[ "$#" -ne 22 ]]; then
    usage
    exit 1
fi

# setting up shared env variables
set_env

# local vars

MAX_VMS=4
SLEEP_IN_SEC=10

cd ${WORKING_DIR}

# configure go
info "configuring go"

# validate UUID format for OVIRT_CLUSTER_ID and OVIRT_STORAGE_DOMAIN_ID
info "validating UUID format for OVIRT_CLUSTER_ID and OVIRT_STORAGE_DOMAIN_ID"

if [[ ! ${OVIRT_CLUSTER_ID//-/} =~ ^[[:xdigit:]]{32}$ || ! ${OVIRT_STORAGE_DOMAIN_ID//-/} =~ ^[[:xdigit:]]{32}$ ]]; then
    error " either OVIRT_CLUSTER_ID=${OVIRT_CLUSTER_ID} or OVIRT_STORAGE_DOMAIN_ID=${OVIRT_STORAGE_DOMAIN_ID} have no valid UUID format"
fi

# compile OCP installer
cd ${INSTALLER_DIR}
info "compiling OCP installer"
./hack/build.sh

# create ovirt-config.yaml
info "creating ovirt-config.yaml"

OVIRT_CONFIG="${INSTALLER_DIR}/ovirt-config.yaml"

cp -f ${WORKING_DIR}/ovirt-config.yaml.in ${OVIRT_CONFIG}

# replace vars with real parameters value

sed -i -e 's;OVIRT_API_URL;'"$OVIRT_API_URL"';' \
       -e 's;OVIRT_USER;'"$OVIRT_USER"';' \
       -e 's;OVIRT_PASSWD;'"$OVIRT_PASSWD"';' \
       -e 's;OVIRT_CLUSTER_ID;'"$OVIRT_CLUSTER_ID"';' \
       -e 's;OVIRT_STORAGE_DOMAIN_ID;'"$OVIRT_STORAGE_DOMAIN_ID"';' \
    -e 's;OVIRT_NETWORK_NAME;'"${OVIRT_NETWORK_NAME}"';' \
       ${OVIRT_CONFIG}

# check if OVIRT_CONFIG file exists
info "checking if ${OVIRT_CONFIG}/ file exists"

if [ ! -e "${OVIRT_CONFIG}" ]; then
    git_cleanup_and_error "file ${OVIRT_CONFIG} does not exist"
fi

# create install-config.yaml
info "creating install-config.yaml"

if [ ! -e "${WORKING_DIR}/install-config.yaml.in" ]; then
    git_cleanup_and_error "can not find ${WORKING_DIR}/install-config.yaml.in file"
fi

cp -f ${WORKING_DIR}/install-config.yaml.in ${INSTALLER_DIR}/install-config.yaml

# set SSH key
info "set SSH key, prefix, oVirt cluster id, oVirt SD id , oVirt network name"

if [ ! -e ${SSH_KEY_FILE} ]; then
    git_cleanup_and_error "ssh key file ${SSH_KEY_FILE} does not esists"
fi

# generate a unique PREFIX for that run to be used in VM creation and API search

PREFIX_FOR_SEARCH="${PREFIX}$(( ( RANDOM % 1000 )  + 1 ))"
PREFIX="${PREFIX_FOR_SEARCH}-${TPR_OR_CH_OR_MB}"
#limit PREFIX to first 14 chars
PREFIX=${PREFIX:0:14}
SSH_KEY=$( cat ${SSH_KEY_FILE} | cut -f1-2 -d " " )
sed -i  -e 's;SSH_KEY;'"${SSH_KEY}"';' \
    -e 's;PREFIX;'"${PREFIX}"';' \
    -e 's;OVIRT_CLUSTER_ID;'"${OVIRT_CLUSTER_ID}"';' \
    -e 's;OVIRT_STORAGE_DOMAIN_ID;'"${OVIRT_STORAGE_DOMAIN_ID}"';' \
    -e 's;OVIRT_NETWORK_NAME;'"${OVIRT_NETWORK_NAME}"';' \
    -e 's;OVIRT_BASE_DOMAIN;'"${OVIRT_BASE_DOMAIN}"';' \
    ${INSTALLER_DIR}/install-config.yaml

cd ${INSTALLER_DIR}

# create cluster
info "creating cluster"

# run the following in background and follow VM creation in order to exit before k8s actions

os_installer create cluster &

ISNTALLER_PID=$!
info "running openshift-install in background with PID=${INSTALLER_PID}"

VMS=0

#  waiting for 1 master and 3 worker VMs to be created and up

while [[ ${VMS} -ne ${MAX_VMS} ]]; do
    info "waiting for 1 master and 3 worker VMs with prefix ${PREFIX_FOR_SEARCH} to be created and up and running [ ${VMS}/${MAX_VMS} ]"
    VMS=$(curl --insecure -s -X \
    GET -H "Accept: application/xml" \
    -u ${OVIRT_USER}:${OVIRT_PASSWD} \
    ${OVIRT_API_URL}/vms/?search=name%3D${PREFIX_FOR_SEARCH}* \
           | grep "<status>up</status>" \
    | wc -l)

    if [[ $? -ne 0 ]]; then
        error "failed to get VMs using API GET call, please check reported errors"
    fi

    sleep ${SLEEP_IN_SEC}
    # checking that background invocation of os installer is still alive
    if [ $(ps -ef | grep "openshift-install" | wc -l) -eq 1 ]; then
        git_cleanup_and_error "Openshift installer exited abnormally, please check logs"
    fi
done

info "1 master and 3 worker VMs were created successfully, [ ${VMS}/${MAX_VMS} ]"

# cleanup
info "cleaning background process, bootstrap, cluster VMs and other temp files"

info "stopping background children that run OS installer"
kill $(list_descendants $$)

#kill -9 ${ISNTALLER_PID}

if [[ $? -ne 0 ]]; then
    warn "failed to kill OS installer execution in background, please kill it manually"
fi

info "destroying bootstrap"
os_installer destroy bootstrap

if [[ $? -ne 0 ]]; then
    warn "failed to destroy bootstrap"
fi
info "destroying cluster"
os_installer destroy cluster
if [[ $? -ne 0 ]]; then
    warn "failed to destroy cluster"
fi

git_cleanup

