#!/bin/bash -xe

EXPORT_DIR="$PWD/exported-artifacts"
mkdir -p "$EXPORT_DIR"

builddep() {
    if [[ -f /etc/fedora-release ]]; then
        dnf builddep "$1"
    else
        yum-builddep "$1"
    fi
}

ovirtlib_rpm() {
    pushd network-suite-master
    make all
    builddep ovirtlib.spec
    make rpm
    find `rpm --eval %_topdir` \
        -iname \?\*.rpm \
        -exec mv {} "$EXPORT_DIR/" \;
    popd
}

ovirtlib_rpm
