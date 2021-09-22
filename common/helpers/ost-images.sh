#!/bin/bash -xe

_find_qcow() {
    rpm -q ost-images-${OST_IMAGES_DISTRO}-${1} 1>&2
    rpm -ql ost-images-${OST_IMAGES_DISTRO}-${1} | grep qcow2
}

_find_ssh_key() {
    rpm -ql ost-images-${OST_IMAGES_DISTRO}-base | grep 'id_rsa$'
}

export OST_IMAGES_DISTRO=${OST_IMAGES_DISTRO:-el8stream}

export OST_IMAGES_BASE=${OST_IMAGES_BASE:-$(_find_qcow "base")}
export OST_IMAGES_NODE=${OST_IMAGES_NODE:-$(OST_IMAGES_DISTRO=node _find_qcow "base")}
export OST_IMAGES_UPGRADE=${OST_IMAGES_UPGRADE:-$(_find_qcow "upgrade")}
export OST_IMAGES_ENGINE_INSTALLED=${OST_IMAGES_ENGINE_INSTALLED:-$(_find_qcow "engine-installed")}
export OST_IMAGES_HOST_INSTALLED=${OST_IMAGES_HOST_INSTALLED:-$(_find_qcow "host-installed")}
export OST_IMAGES_HE_INSTALLED=${OST_IMAGES_HE_INSTALLED:-$(_find_qcow "he-installed")}

export OST_IMAGES_SSH_KEY=${OST_IMAGES_SSH_KEY:-$(_find_ssh_key)}
