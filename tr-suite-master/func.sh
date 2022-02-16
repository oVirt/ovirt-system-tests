#!/bin/sh

export TMPDIR="${WORKING_DIR}"
export HOME="${WORKING_DIR}"

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

set_env() {

    CONFIG_DIR="${WORKING_DIR}"/config
    if [[ $(ls -1 ${WORKING_DIR} | grep tr_master_suite_ | grep log | wc -l) -gt 0 ]]; then
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
