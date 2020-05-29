#!/bin/bash

source /etc/os-release
os="${ID:?}${VERSION_ID:?}"

if [[ "$os" =~ "centos8" ]] || [[ "$os" =~ "rhel8" ]]; then
    PYTHON="python3"
    OVIRT_ENGINE_SDK_PKG="python3-ovirt-engine-sdk4"
else
    PYTHON="python2"
    OVIRT_ENGINE_SDK_PKG="python-ovirt-engine-sdk4"
fi
