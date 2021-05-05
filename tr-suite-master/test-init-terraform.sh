#!/bin/sh

usage() {
cat << __EOF__
    Usage: $0 -w working-directory -t terraform-pull-request-number

    -h                         - This help text.
    -w WORKING_DIR             - working directory for the scripts (def. ${WORKING_DIR})
    -t TPR_OR_CH_OR_MB         - Teraform PR id or commit hash or master branch to check (def. ${TPR_OR_CH_OR_MB})
__EOF__
}

#get parameters
while getopts hw:t: option; do
    case $option in
            h) usage; exit 0;;
            w) WORKING_DIR="${OPTARG}";;
            t) TPR_OR_CH_OR_MB="${OPTARG}";;
    esac
done

if [[ ! -n $2 ]]; then
    usage
    exit 1
fi

source ${WORKING_DIR}/func.sh

# setting up shared env variables
set_env

# local vars
is_commit=0

# check for OCP installer sources repo , if not found then create it
info "checking for OCP installer sources repo , if not found then create it"

cd ${GOSRC}

if [ -e ${INSTALLER_DIR} ]; then
    rm -rf ${INSTALLER_DIR}
fi

# TODO : The following line hangs the testing foreever, git is installed in stage 003
git clone https://github.com/openshift/installer
mkdir -p "${ARTIFACTS_DIR}"

# now the repo should be here, if not exit
if [ ! -e ${INSTALLER_DIR} ]; then
     git_cleanup_and_error "failed to create OCP installer repo, please check and retry after solving the problem"
fi

# fetch and rebase the OCP installer sources repo
info "fetching and rebasing the OCP installer sources repo"
cd ${INSTALLER_DIR}
git_fetch_rebase


# check for terraform provider sources repo , if not found then create it
info "checking for terraform provider sources repo , if not found then create it"

if [ ! -e ${OVIRT_DIR} ]; then
    mkdir ${OVIRT_DIR}
fi

cd ${OVIRT_DIR}

if [ -e  terraform-provider-ovirt ]; then
    rm -rf ${OVIRT_DIR}/terraform-provider-ovirt
fi

git clone https://github.com/oVirt/terraform-provider-ovirt

# now the repo should be here, if not exit
if [ ! -e terraform-provider-ovirt ]; then
    error "failed to create terraform-provider repo, please check and retry after solving the problem"
fi

# fetch and rebase the  terraform provider sources repo
info "fetching and rebasing the terraform provider sources repo"
cd  ${TERRAFORM_DIR}
git_fetch_rebase
# check if given PR is a former merged commit hash to make easy tracking any errors after PR is merged
TPR_OR_CH_OR_MB_LENGTH=$(echo -n "${TPR_OR_CH_OR_MB}" | wc -m)
if [ ${TPR_OR_CH_OR_MB_LENGTH} -lt 7 -o ${TPR_OR_CH_OR_MB} = "master" ]; then
    is_commit=0
else
    is_commit=$(git log | grep "${TPR_OR_CH_OR_MB}" |wc -l)
fi

cd  ${TERRAFORM_DIR}
# create git PR branch
if [ "${TPR_OR_CH_OR_MB}" != "master" ]; then
    if [ ${is_commit} -gt 0 -a ${TPR_OR_CH_OR_MB_LENGTH} -gt 7 ]; then
        info "checking out merged commit with hash  ${TPR_OR_CH_OR_MB}"
        git checkout ${TPR_OR_CH_OR_MB}
    fi
else
    info "checking against master branch"
fi

#format patch file from PR
if [ -e ${TPR_OR_CH_OR_MB}.patch ]; then
    rm -f ${TPR_OR_CH_OR_MB}.patch
fi

if [ "${TPR_OR_CH_OR_MB}" != "master" -a ${is_commit} -lt 1 ]; then
        git fetch origin pull/${TPR_OR_CH_OR_MB}/head:${TPR_OR_CH_OR_MB}
    if [[ $? -ne 0 ]]; then
        cmd="git fetch origin pull/${TPR_OR_CH_OR_MB}/head:${TPR_OR_CH_OR_MB}"
        git_cleanup_and_error "failed to find PR ${TPR_OR_CH_OR_MB}, cmd=${cmd}"
    fi
    git checkout ${TPR_OR_CH_OR_MB}
    info "Trying to rabase PR ${TPR_OR_CH_OR_MB} on master branch"
    git rebase origin/master
    if [[ $? -ne 0 ]]; then
        git rebase --abort
        git_cleanup_and_error "failed to apply automatically PR ${TPR_OR_CH_OR_MB}, please rebase your patch on latest master and try again"
    fi
fi

# compile terraform plugin
info "compiling terraform plugin"

make build

if [[ $? -ne 0 ]]; then
    git_cleanup_and_error "failed to build terraform provider on top of PR ${TPR_OR_CH_OR_MB}, please check your code"
fi

#install terraform provider plugin

info "installing terraform provider"
terraform init \
    -force-copy \
    -get=true \
    -reconfigure \
    -upgrade=false \
    -plugin-dir="${GOPKG}"

if [[ $? -ne 0 ]]; then
    git_cleanup_and_error "failed to init terraform provider on top of  PR ${TPR_OR_CH_OR_MB}, please check log file/s"
fi

info "committing terraform changes on installer repo"
cd  ${INSTALLER_DIR}
git add vendor/*
git commit -a -m "testing ${TPR_OR_CH_OR_MB}"
