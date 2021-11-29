#!/bin/bash -xe

OST_IMAGES_DIR=${OST_IMAGES_DIR:=/usr/share/ost-images}
OST_IMAGES_DISTRO=${OST_IMAGES_DISTRO:=el8stream}
local node=node-base.qcow2
[[ "$OST_IMAGES_DISTRO" == "rhel8" ]] && node=rhvh-base.qcow2

echo ${OST_IMAGES_BASE:=${OST_IMAGES_DIR}/${OST_IMAGES_DISTRO}-base.qcow2}
echo ${OST_IMAGES_NODE:=${OST_IMAGES_DIR}/${node}}
echo ${OST_IMAGES_ENGINE_INSTALLED:=${OST_IMAGES_DIR}/${OST_IMAGES_DISTRO}-engine-installed.qcow2}
echo ${OST_IMAGES_HOST_INSTALLED:=${OST_IMAGES_DIR}/${OST_IMAGES_DISTRO}-host-installed.qcow2}
echo ${OST_IMAGES_HE_INSTALLED:=${OST_IMAGES_DIR}/${OST_IMAGES_DISTRO}-he-installed.qcow2}
[[ -r "${OST_IMAGES_SSH_KEY:=${OST_IMAGES_DIR}/${OST_IMAGES_DISTRO}_id_rsa}" ]] || echo "ssh key file missing"

export $(set | grep ^OST_IMAGES_ | cut -d= -f1)