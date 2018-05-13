#!/bin/bash -xe

usage () {
    echo "
Usage:

$0 [options] [PKG_0 [ PKG_1 ...]]

This script will create a VM with Lago, which will be used to generate
a reposync-config. The generated reposync config will match the lago-template
that was provided (which means that it can't be used with another template).

Positional arguments:
    PKG
        Packages to include in the config

Optional arguments:
    -c,--reposync-config PATH
        Path to the Yum config that should be used. If not provided the
        default Yum config that is configured on the host will be used.
        Make sure that in the main section of the config the following
        option exists: 'plugins=1'

    -p,--pkg-file PATH
        Path to a text file which contains a list of packages that should
        be installed. Each package should be in a new line.
        This list of packages will be appended to the list of packges that
        was given as positional arguments.

    -t,--lago-template
        The template that will be used for creating the VM.
        The generated reposync-config will be usable only with this template.

    -r,--lago-repo
        Lago image repo that the template belongs to.
"
}

generate_init_file() {
    local lago_template="$1"
    local vm_name="$2"

    sed  \
        -e "s/{{ lago_template }}/$lago_template/g" \
        -e "s/{{ vm_name }}/$vm_name/g" \
        > LagoInitFile <<EOF
domains:
  {{ vm_name }}:
    memory: 2048
    service_provider: systemd
    nics:
      - net: lago
    disks:
      - template_name: {{ lago_template }}
        type: template
        name: root
        dev: sda
        format: qcow2
    artifacts:
      - /var/log
nets:
  lago:
    type: nat
    dhcp:
      start: 100
      end: 254
    management: true
    dns_domain_name: lago.local
EOF
}

run_lago_env() {
    local lago_repo="$1"

    lago init --template-repo-path "$lago_repo"
    lago start
}

run_reposync_builder() {
    local builder_path="$1"
    local builder_config_path="$2"
    local reposync_config="$3"
    local pkgs_to_install="$4"
    local vm_name="$5"

    local yum_verify_cmd=("yum" "info")
    local yum_install_cmd=("yum" "install" "-y" "$pkgs_to_install")

    if [[ -n "$reposync_config" ]]; then
        local remote_config_path="/tmp/${reposync_config##*/}"
        lago copy-to-vm "$vm_name" "$reposync_config" "$remote_config_path"
        yum_verify_cmd+=(-c "$remote_config_path")
        yum_install_cmd+=(-c "$remote_config_path")
    fi

    # This is needed in order to overcome a bug in Yum
    # when running "yum install a b", where "a" exists and "b" isn't,
    # Yum will return status code 0
    lago shell "$vm_name" -c bash -ex <<EOF
    for pkg in $pkgs_to_install; do
        ${yum_verify_cmd[*]} \$pkg
    done
EOF

    lago copy-to-vm "$vm_name" "$builder_path" /usr/share/yum-plugins
    lago copy-to-vm "$vm_name" "$builder_config_path" /etc/yum/pluginconf.d

    lago shell "$vm_name" -c "${yum_install_cmd[*]}" || :

    lago copy-from-vm \
    	"$vm_name" \
    	"${remote_config_path}.modified" \
    	. \
        || (echo "Failed to build reposync-config" && exit 1)
}

cleanup() {
    rm LagoInitFile || :
    lago destroy -y
}

main() {
    local project_dir="${0%/*}"
    local lago_repo="http://templates.ovirt.org/repo/repo.metadata"
    local lago_template="el7.5-base"
    local vm_name=vm-01
    local pkgs=()
    local options=$( \
        getopt \
            -o hc:p:t:r: \
            --long help,reposync-config:,pkg-file:,lago-template:,lago-repo: \
            -n 'build_reposync_config.sh' \
            -- "$@" \
    )

    if [[ "$?" != "0" ]]; then
        exit 1
    fi
    eval set -- "$options"
    while true; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            -c|--reposync-config)
                local reposync_config=$(realpath $2)
                shift 2
                ;;
            -p|--pkg-file)
                local pkg_file=$(realpath $2)
                shift 2
                ;;
            -t|--lago-template)
                lago_template="$2"
                shift 2
                ;;
            -r|--lago-repo)
                lago_repo="$2"
                shift 2
                ;;
            --)
                shift
                break
                ;;
        esac
    done

    trap cleanup EXIT

    if [[ -f "$pkg_file" ]]; then
        readarray -t pkgs < "$pkg_file"
    fi

    pkgs+=("$@")
    if [[ ${#pkgs[@]} -eq 0 ]]; then
        echo "Packages list is empty"
        exit 0
    fi
    echo "Building config for the following packges:\n${pkgs[*]}"
    echo "Creating lago env"
    generate_init_file "$lago_template" "$vm_name"
    run_lago_env "$lago_repo"
    run_reposync_builder \
        "$project_dir/reposync_config_builder.py" \
        "$project_dir/reposync_config_builder.conf" \
        "$reposync_config" \
        "${pkgs[*]}" \
        "$vm_name"
    echo "Success !"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    main "$@"
fi
