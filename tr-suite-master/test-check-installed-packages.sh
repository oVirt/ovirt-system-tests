#!/bin/sh

enable_repo() {

    local repo_name="${1}"
    dnf config-manager --enable "${repo_name}"
}

disable_repo() {

    local repo_name="${1}"
    dnf config-manager --disable "${repo_name}"
}

is_package_installed() {

    exists=$(rpm -qa |grep -E "^$1[-][0-9]+[0-9a-z\-\.]+" |wc -l)
    return $exists

}

install_package() {

    local package_name="${1}"
    dnf install -y ${package_name}
}

# enable relevant repos in order to install missing packages
enable_repo "baseos"
enable_repo "appstream"


is_package_installed "make"
make_installed=$?
is_package_installed "git"
git_installed=$?
is_package_installed "golang"
golang_installed=$?
is_package_installed "terraform"
terraform_installed=$?

terraform_repo="https://rpm.releases.hashicorp.com/RHEL/hashicorp.repo"


# install git

if [[ ${git_installed} -eq 0 ]]; then

    install_package "git"
    install_package "git-core"
fi

# install make

if [[ ${make_installed} -eq 0 ]]; then

    install_package "make"
fi

# install golang

if [[ ${golang_installed} -eq 0 ]]; then

    install_package "golang"

fi

#install terraform

if [[ ${terraform_installed} -eq 0 ]]; then
    dnf install -y dnf-plugins-core
    dnf config-manager --add-repo ${terraform_repo}
    dnf install -y terraform
    # currently there is a problem in terraform rpm that makes it fail
    # the following ia a workaround that installs terraform RPM ignoring
    # errors
    if [[ $? -ne 0 ]]; then
        dnf download terraform
        rpm=$(find . -name "*terraform*.rpm" -print)
        rpm --nodigest --nofiledigest -iv ${rpm}
    fi
fi

# disable relevant repos

disable_repo "baseos"
disable_repo "appstream"
disable_repo "hashicorp"
