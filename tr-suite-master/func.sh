#!/bin/sh

# define colors for info/warn/error messages (green/yellow/red) , we must reset to nocolor each time

red='\033[0;31m'
green='\033[0;32m'
yellow='\033[0;33m'
nocolor='\033[0m'

info() {
    printf  "${green} [INFO] ===> ${nocolor} ${1}...\n" >> "${LOGFILE}"
}

warn() {
    printf  "${yellow} [WARN] ===> ${nocolor} ${1}...\n" >> "${LOGFILE}"
}

error() {
    printf "${red} [ERROR] ===> ${nocolor} ${1}...\n" >> "${LOGFILE}"
    exit 1
}

git_fetch_rebase() {
	git fetch
	git rebase origin/master
}

git_cleanup () {

    if [ -e ${INSTALLER_DIR}/terraform.tfstate ]; then
        rm -f ${INSTALLER_DIR}/terraform.tfstate
    fi

    if [ -e ${TERRAFORM_DIR} ]; then

        cd ${TERRAFORM_DIR}

        # cleanup git patches and temp branch
        info "cleanup git patches and temp branch"

        rm -f ./*.patch
        git stash
        git stash clear
        git checkout master
        branch_exists=$(git branch |grep ${TPR_OR_CH_OR_MB} | wc -l)
        if [ "${TPR_OR_CH_OR_MB}" != "master" -a  ${branch_exists} -eq 1 ]; then
            info "removing branch ${TPR_OR_CH_OR_MB}"
            git branch -D ${TPR_OR_CH_OR_MB}
        fi

        # clean any new files/directories created by the patch
        rm -rf $(git status --short |cut -f2 -d " ")
    fi
    cd ${WORKING_DIR}
}

git_cleanup_and_error() {
    git_cleanup
    error "${1}"
}

set_env() {

    if [ ! -e "${WORKING_DIR}"/go ]; then
        mkdir "${WORKING_DIR}"/go
    fi
    GOPATH="${WORKING_DIR}/go"
    if [ ! -d ${GOPATH}/src ]; then
        mkdir ${GOPATH}/bin ${GOPATH}/src ${GOPATH}/pkg > /dev/null  2>&1
    fi
    GOBIN="${GOPATH}/bin"
    GOSRC="${GOPATH}/src"
    GOPKG="${GOPATH}/pkg"

    INSTALLER_DIR="${GOSRC}/installer"
    ARTIFACTS_DIR="${INSTALLER_DIR}"/artifacts
    OVIRT_DIR="${INSTALLER_DIR}/vendor/github.com/ovirt"
    TERRAFORM_DIR=${OVIRT_DIR}/terraform-provider-ovirt
    if [[ $(ls -1 ${WORKING_DIR}/tr_master_suite_*.log | wc -l) -gt 0 ]]; then
        LOGFILE=$(ls -1 ${WORKING_DIR}/tr_master_suite_*.log | head -1)
    else
        LOGFILE="${WORKING_DIR}/tr_master_suite_$(date +'%Y_%m_%d_%I_%M_%p').log"
    fi

}

validate_uuid() {

    name="${1}"
    id="${2}"

    d8="[[:xdigit:]]{8}"
    d4="[[:xdigit:]]{4}"
    d12="[[:xdigit:]]{12}"

    if [[ ! ${id} =~ ^${d8}-${d4}-${d4}-${d4}-${d12}$ ]]; then
        error "Value of parameter ${name} - ${id} has no valid UUID format"
    fi
}
