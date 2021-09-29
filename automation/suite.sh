#!/bin/bash -e

# This script needs to run on a bare metal host that has been set up
# with setup_for_ost.sh

if [[ "${RUNNING_IN_PSI}" != "true" ]]; then
    echo "automation runs only on PSI/baremetal servers"
    exit 1
fi

SUITE="$BASH_SOURCE"
SUITE=$(echo "$SUITE" | tr '_' '-')
# Leaving just the base dir
SUITE=${SUITE##*/}
# Remove file extension
SUITE=${SUITE%.*}

echo "Running suite: $SUITE"

# TODO because the hosts are not set up with setup_for_ost.sh, and it only works because stdci runs this as root
semanage permissive -a virtlogd_t
# $distro is passed from stdci, not a good idea to depend on it, but there's currently no other way how to choose which ost-image to use
if [[ "$distro" == "el8" ]]; then
    distro="el8stream"
fi
echo "Distro: ${distro:=el8stream}"
mkdir -p exported-artifacts
{
  source lagofy.sh "$PWD" &&
    export OST_IMAGES_DISTRO=$distro &&
    source "$OST_REPO_ROOT/common/helpers/ost-images.sh" &&
    cp ${OST_IMAGES_SSH_KEY}* /tmp &&
    OST_IMAGES_SSH_KEY=/tmp/$(basename $OST_IMAGES_SSH_KEY) &&
    chmod 600 ${OST_IMAGES_SSH_KEY}* &&
    ost_init $SUITE $OST_IMAGES_DISTRO &&
    ost_run_tests;
} 2>&1 | tee exported-artifacts/ost_run_tests.log
exit ${PIPESTATUS[0]}
