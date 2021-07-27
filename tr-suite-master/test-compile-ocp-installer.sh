#!/bin/sh

usage() {
cat << __EOF__
    Usage: $0 -w working-directory

    -h                         - This help text.
    -w WORKING_DIR             - working directory for the scripts (def. ${WORKING_DIR})
__EOF__
}

#get parameters
while getopts hw: option; do
    case $option in
            h) usage; exit 0;;
            w) WORKING_DIR="${OPTARG}";;
    esac
done

source ${WORKING_DIR}/func.sh

# setting up shared env variables
set_env

# compile OCP installer
cd ${INSTALLER_DIR}
info "compiling OCP installer"
./hack/build.sh

if [[ $? -ne 0 ]]; then
    git_cleanup_and_error "failed to compile OCP installer"
fi
