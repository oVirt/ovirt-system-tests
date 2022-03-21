#!/bin/bash -xe

if [[ -n "$CUSTOM_OST_IMAGES_REPO" ]]; then
  echo "Installing custom ost-images from $CUSTOM_OST_IMAGES_REPO"
  sudo dnf -y --installroot="$OST_REPO_ROOT/custom-ost-images" --releasever=/  install bash
  sudo dnf -y --installroot="$OST_REPO_ROOT/custom-ost-images" --releasever=/ --repo=custom-ost-images --repofrompath custom-ost-images,${CUSTOM_OST_IMAGES_REPO} --setopt=custom-ost-images.gpgcheck=0 --setopt=custom-ost-images.metadata_expire=60 --setopt=sslverify=0 install ost-images-\* || exit 1
  sudo chown `id -u`:`id -g` -R custom-ost-images
  chmod ug+rwX -R "$OST_REPO_ROOT/custom-ost-images"
  find "$OST_REPO_ROOT/custom-ost-images" -name \*id_rsa | xargs chmod 600
  OST_IMAGES_DIR="$OST_REPO_ROOT/custom-ost-images/usr/share/ost-images"
else
  OST_IMAGES_DIR=${OST_IMAGES_DIR:=/usr/share/ost-images}
fi

OST_IMAGES_DISTRO=${OST_IMAGES_DISTRO:=el8stream}
local node=node-base.qcow2
[[ "$OST_IMAGES_DISTRO" == "rhel8" ]] && node=rhvh-base.qcow2

OST_IMAGES_BASE=${OST_IMAGES_BASE:-${OST_IMAGES_DIR}/${OST_IMAGES_DISTRO}-base.qcow2}
OST_IMAGES_NODE=${OST_IMAGES_NODE:-${OST_IMAGES_DIR}/${node}}
OST_IMAGES_ENGINE_INSTALLED=${OST_IMAGES_ENGINE_INSTALLED:-${OST_IMAGES_DIR}/${OST_IMAGES_DISTRO}-engine-installed.qcow2}
OST_IMAGES_HOST_INSTALLED=${OST_IMAGES_HOST_INSTALLED:-${OST_IMAGES_DIR}/${OST_IMAGES_DISTRO}-host-installed.qcow2}
OST_IMAGES_HE_INSTALLED=${OST_IMAGES_HE_INSTALLED:-${OST_IMAGES_DIR}/${OST_IMAGES_DISTRO}-he-installed.qcow2}
OST_IMAGES_STORAGE_BASE=${OST_IMAGES_STORAGE_BASE:=${OST_IMAGES_DIR}/storage-base.qcow2}
OST_IMAGES_SSH_KEY=${OST_IMAGES_SSH_KEY:-${OST_IMAGES_DIR}/${OST_IMAGES_DISTRO}_id_rsa}
for i in OST_IMAGES_BASE OST_IMAGES_NODE OST_IMAGES_ENGINE_INSTALLED OST_IMAGES_HOST_INSTALLED OST_IMAGES_HE_INSTALLED OST_IMAGES_SSH_KEY; do
  [[ -r "${!i}" ]] || declare $i=/usr/share/ost-images/$(basename ${!i})
  echo "${i} ${!i} $(rpm -qf ${!i} 2>/dev/null)"
done

export $(set | grep ^OST_IMAGES_ | cut -d= -f1)
