#!/bin/sh

usage() {
cat << __EOF__
    Usage: $0 -w plugin-directory

    -h                         - This help text.
    -l PLUGIN_DIR             - Terraform binary plugin dir (def. ${PLUGIN_DIR})
__EOF__
}

#get parameters
while getopts hl: option; do
    case $option in
            h) usage; exit 0;;
            l) PLUGIN_DIR="${OPTARG}";;
    esac
done

if [[ ! -n $1 ]]; then
    usage
    exit 1
fi

# initialize terraform with provider plugin

info "initializing terraform..."
terraform init \
    -force-copy \
    -get=true \
    -reconfigure \
    -upgrade=false \
    -plugin-dir="${PLUGIN_DIR}"

