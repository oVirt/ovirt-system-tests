#!/bin/bash -xe

# This directory has to be visible by both processes
# outside mock (libvirt) and inside mock (lago)
_OST_IMAGES_ROOT="/var/lib/lago"

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

_fix_permissions() {
    chown "$(whoami):qemu" "$1"
    chmod g+rwx "$1"
}

prepare_images_for_mock() {
    export OST_IMAGES_DIR="$(mktemp -d -p ${_OST_IMAGES_ROOT} ost-images-XXXXXX)"

    _fix_permissions "${OST_IMAGES_DIR}"
    ln -s "${OST_IMAGES_DIR}" "${PREFIX}/ost-images"

    local all_images=(
        ${OST_IMAGES_BASE} \
        ${OST_IMAGES_UPGRADE} \
        ${OST_IMAGES_ENGINE_INSTALLED} \
        ${OST_IMAGES_HOST_INSTALLED} \
        ${OST_IMAGES_HE_INSTALLED} \
        ${OST_IMAGES_NODE} \
    )

    for image in ${all_images[*]}; do
        local dest="${OST_IMAGES_DIR}/$(basename ${image})"
        cp "${image}" "${dest}"
        _fix_permissions "${dest}"
    done

    local key_dest="${OST_IMAGES_DIR}/$(basename ${OST_IMAGES_DIR})"
    cp "${OST_IMAGES_SSH_KEY}" "${key_dest}"
    cp "${OST_IMAGES_SSH_KEY}.pub" "${key_dest}.pub"
    chmod 600 "${key_dest}"
    export OST_IMAGES_SSH_KEY="${key_dest}"

    export OST_IMAGES_BASE="${OST_IMAGES_DIR}/$(basename ${OST_IMAGES_BASE})"
    export OST_IMAGES_NODE="${OST_IMAGES_DIR}/$(basename ${OST_IMAGES_NODE})"
    export OST_IMAGES_UPGRADE="${OST_IMAGES_DIR}/$(basename ${OST_IMAGES_UPGRADE})"
    export OST_IMAGES_ENGINE_INSTALLED="${OST_IMAGES_DIR}/$(basename ${OST_IMAGES_ENGINE_INSTALLED})"
    export OST_IMAGES_HOST_INSTALLED="${OST_IMAGES_DIR}/$(basename ${OST_IMAGES_HOST_INSTALLED})"
    export OST_IMAGES_HE_INSTALLED="${OST_IMAGES_DIR}/$(basename ${OST_IMAGES_HE_INSTALLED})"
}

cleanup_ost_images() {
    local ost_images_dir_link="${PREFIX}/ost-images"
    if [ -e "${ost_images_dir_link}" ]; then
        local real_ost_images_dir="$(readlink ${ost_images_dir_link})"
        rm -r "${real_ost_images_dir}"
        rm "${ost_images_dir_link}"
    fi
}
