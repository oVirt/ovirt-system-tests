#!/bin/bash

source /etc/os-release
OST_OS="${ID:?}${VERSION_ID:?}"

if [[ "${OST_OS}" =~ "rhel8" ]]; then
    export OST_IMAGES_DISTRO=rhel8
fi

