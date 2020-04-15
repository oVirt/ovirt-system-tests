#!/bin/bash

IMGDIR=${1:-`pwd`}

pushd "${IMGDIR}"

for qcow in *.qcow2; do
    backing="$(qemu-img info ${qcow} | sed -n 's/backing file: \([^[:space:]]*\).*/\1/p')"

    if [ -n "${backing}" ]; then
        backing="${IMGDIR}/$(basename ${backing})"
        echo "Rebasing ${qcow} to ${backing}"
        qemu-img rebase -u -b "${backing}" "${qcow}"
    else
        echo "${qcow} has no base image, skipping"
    fi
done

popd
