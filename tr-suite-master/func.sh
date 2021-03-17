#!/bin/sh

# define colors for info/warn/error messages (GREEN/YELLOW/RED) , we must reset to NOCOLOR each time

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NOCOLOR='\033[0m'

info() {
    printf  "${GREEN} [INFO] ===> ${NOCOLOR} ${1}...\n"
}

warn() {
    printf  "${YELLOW} [WARN] ===> ${NOCOLOR} ${1}...\n"
}

error() {
    printf "${RED} [ERROR] ===> ${NOCOLOR} ${1}...\n"
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
        BRANCH_EXISTS=$(git branch |grep ${TPR_OR_CH_OR_MB} | wc -l)
        if [ "${TPR_OR_CH_OR_MB}" != "master" -a  ${BRANCH_EXISTS} -eq 1 ]; then
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
    OVIRT_DIR="${INSTALLER_DIR}/vendor/github.com/ovirt"
    TERRAFORM_DIR=${OVIRT_DIR}/terraform-provider-ovirt

}
