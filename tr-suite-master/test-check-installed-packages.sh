#!/bin/sh

enable_repo() {

    local repo_name="${1}"
    if  [[ ${DNF_INSTALLED} -gt 0 ]];then
    dnf config-manager --enable "${repo_name}"
    else
    yum-config-manager --enable "${repo_name}"
    fi
}

disable_repo() {

    local repo_name="${1}"
    if  [[ ${DNF_INSTALLED} -gt 0 ]];then
    dnf config-manager --disable "${repo_name}"
    else
    yum-config-manager --disable "${repo_name}"
    fi
}

is_package_installed() {
    exists=$(rpm -qa |grep -E "^$1[-][0-9]+[0-9a-z\-\.]+" |wc -l)
    return $exists

}

install_package() {

    local package_name="${1}"

    if  [[ ${DNF_INSTALLED} -gt 0 ]];then
        dnf install -y ${package_name}
    else
        yum install -y ${package_name}
    fi
}

# enable relevant repos in order to install missing packages
enable_repo "baseos"
enable_repo "appstream"
enable_repo "hashicorp"


is_package_installed "dnf"
DNF_INSTALLED=$?
is_package_installed "make"
MAKE_INSTALLED=$?
is_package_installed "git"
GIT_INSTALLED=$?
is_package_installed "golang"
GOLANG_INSTALLED=$?
is_package_installed "terraform"
TERRAFORM_INSTALLED=$?

TERRAFORM_REPO="https://rpm.releases.hashicorp.com/RHEL/hashicorp.repo"


# install git

if [[ ${GIT_INSTALLED} -eq 0 ]]; then

    install_package "git"
    install_package "git-core"
fi

# install make

if [[ ${MAKE_INSTALLED} -eq 0 ]]; then

    install_package "make"
fi

# install golang

if [[ ${GOLANG_INSTALLED} -eq 0 ]]; then

    install_package "golang"

fi

#install terraform

if [[ ${DNF_INSTALLED} -gt 0 ]]; then
    if [[ ${TERRAFORM_INSTALLED} -eq 0 ]]; then
        dnf install -y dnf-plugins-core
        dnf config-manager --add-repo ${TERRAFORM_REPO}
        dnf install -y terraform
    fi
else
    if [[ ${TERRAFORM_INSTALLED} -eq 0 ]]; then
        yum install -y yum-utils
        yum-config-manager --add-repo ${TERRAFORM_REPO}
        yum install -y terraform
    fi
fi

# disable relevant repos

disable_repo "baseos"
disable_repo "appstream"
disable_repo "hashicorp"
