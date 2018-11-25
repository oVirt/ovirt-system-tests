#!/bin/bash -xe

# Imports
SCRIPT_PATH="${0%/*}"
source "${SCRIPT_PATH}/../../helpers/logger.sh"

usage () {
    echo "
Usage:

$0 [options] [REPOSYNC_0 [ REPOSYNC_1 ...]]

This script will create a VM with Lago, which will be used to generate
a reposync-config. The generated reposync config will match the lago-template
that was provided (which means that it can't be used with another template).

Positional arguments:
    REPOSYNC
        Path to the Yum config that should be used. If not provided the
        default Yum config that is configured on the host will be used.

Optional arguments:
    -p,--pkg PKG
        Package/s to include in the config
    -s,--suite SUITE
        Suite to create the reposync on
"
}

generate_init_file() {
    local lago_template="${1:?}"
    local vm_name="${2:?}"

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
    local lago_repo="${1:?}"

    lago init --template-repo-path "$lago_repo"
    lago start
}

run_reposync_builder() {
    local builder_path="${1:?}"
    local builder_config_path="${2:?}"
    local reposync_config="${3:?}"
    local pkgs_to_install="${4:?}"
    local vm_name="${5:?}"

    local yum_verify_cmd=("yum" "info")
    local yum_install_cmd=("yum" "install" "-y" "$pkgs_to_install")

    [[ -n "$reposync_config" ]] && {
        local remote_config_path="/tmp/${reposync_config##*/}"
        lago copy-to-vm "$vm_name" "$reposync_config" "$remote_config_path"
        yum_verify_cmd+=(-c "$remote_config_path")
        yum_install_cmd+=(-c "$remote_config_path")
    }

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
    local vm_name="${1:?}"
    local prefix="${2:?}"
    rm -f LagoInitFile
    env_cleanup "$vm_name" "$prefix"
}


env_cleanup() {
    local vm_name="${1:?}"
    local prefix="${2:?}"
    local res=0
    local uuid

    logger.info "Cleaning up"
    if [[ -e "$prefix" ]]; then
        logger.info "Cleaning with lago"
        lago --workdir "$prefix" destroy --yes --all-prefixes || res=$?
        [[ "$res" -eq 0 ]] && logger.success "Cleaning with lago done"
    elif [[ -e "$prefix/.lago/current/uuid" ]]; then
        uid="$(cat "$prefix/.lago/current/uuid")"
        uid="${uid:0:4}"
        res=1
    else
        logger.info "No uuid found, cleaning up any lago-generated vms"
        res=1
    fi
    if [[ "$res" -ne 0 ]]; then
        logger.info "Lago cleanup did not work (that is ok), forcing libvirt"
        env_libvirt_cleanup "$uid" "$vm_name"
    fi
    logger.success "Cleanup done"
}

env_libvirt_cleanup() {
    local uid="${1?}"
    local vm_name="${2:?}"
    local domain
    local net
    if [[ "$uid" != "" ]]; then
        local domains=($( \
            virsh -c qemu:///system list --all --name \
            | egrep "$uid*" \
        ))
        local nets=($( \
            virsh -c qemu:///system net-list --all \
            | egrep "$uid*" \
            | awk '{print $1;}' \
        ))
    else
        local domains=($( \
            virsh -c qemu:///system list --all --name \
            | egrep "[[:alnum:]]*-$vm_name" \
            | egrep -v "vdsm-ovirtmgmt" \
        ))
        local nets=($( \
            virsh -c qemu:///system net-list --all \
            | egrep -w "[[:alnum:]]{4}-.*" \
            | egrep -v "vdsm-ovirtmgmt" \
            | awk '{print $1;}' \
        ))
    fi
    logger.info "Cleaning with libvirt"
    for domain in "${domains[@]}"; do
        virsh -c qemu:///system destroy "$domain"
    done
    for net in "${nets[@]}"; do
        virsh -c qemu:///system net-destroy "$net"
    done
    logger.success "Cleaning with libvirt Done"
}

uniq_array() {
    local tmp_array=("$@")
    local array_unique=($(echo "${tmp_array[@]}" | tr ' ' '\n' | sort -u ))
    echo "${array_unique[@]}"
}

verify_array_size_is_one() {
    local type_to_check="${1:?}" && shift
    [[ "${#@}" -ne 1 ]] && {
        logger.error "More than one value for ${type_to_check}: ${*}"
        return 1
    }
    return 0
}
collect_pkgs_from_suite() {
    local suite="${1:?}"
    declare -a pkgs_array

    local pkg_suite_file="${suite}/pkgs.txt"
    [[ -e "$pkg_suite_file" ]] && {
        readarray -t pkgs_array < "$pkg_suite_file"
    }
    echo "${pkgs_array[*]}"
}

collect_template_name_from_suite() {
    local suite="${1:?}"
    local script_path="${2:?}"
    local main_yaml="${suite}/vars/main.yml"
    declare -a template_name
    [[ -e "$main_yaml" ]] && {
        template_name=($("${script_path}/parse_yaml.py" "$main_yaml"))
        echo "${template_name[*]}"
    }
}

collect_template_repo_json_from_suite() {
    local suite="${1:?}"
    local lago_repo_file="${suite}/template-repo.json"
    [[ -e "$lago_repo_file" ]] \
    && realpath "$lago_repo_file"
}

create_updated_reposync_file() {
    local reposync_config="${1:?}"
    local script_path="${2:?}"
    declare -a pkgs=($3)
    declare -a suites=($4)
    declare -a lago_repo_file_array \
        template_array
    local res=0
    # remove ".in" from the template name to get all suites using this template
    local reposync_config_base="${reposync_config%.in}"

    logger.info "Creating updated reposync file for: $reposync_config_base"

    [[ "${#suites[@]}" -eq 0 ]] && {
        local suite_list
        suite_list=$("${script_path}"/change_resolver.py "$reposync_config_base")
        suites=(${suite_list/ /\n/ })
    }

    rm -f "${reposync_config##*/}".modified
    for suite in "${suites[@]}"; do
        [[ -d "$suite" ]] && {
            pkgs+=($(collect_pkgs_from_suite "$suite"))
            template_array+=($(collect_template_name_from_suite "$suite" "$script_path"))
            lago_repo_file_array+=($(collect_template_repo_json_from_suite "$suite"))
        }
    done
    template_array=($(uniq_array "${template_array[@]}"))
    verify_array_size_is_one tempates "${template_array[@]}" || return 1
    lago_repo_file_array=($(uniq_array "${lago_repo_file_array[@]}"))
    verify_array_size_is_one repos "${lago_repo_file_array[@]}" || return 1

    logger.info "Building config for the following packges:\n${pkgs[*]}"
    logger.info "Creating lago env"

    generate_init_file "${template_array[0]}" "$vm_name"
    run_lago_env "${lago_repo_file_array[0]}"
    run_reposync_builder \
        "$project_dir/reposync_config_builder.py" \
        "$project_dir/reposync_config_builder.conf" \
        "$reposync_config" \
        "${pkgs[*]}" \
        "$vm_name" || res=$?
    return "$res"
}

exist_in_array() {
    local my_item="${1:?}"
    local array=("$2")
    for  item in "${array[@]}"; do
       [[ "$my_item" == "$item" ]] && return 0
    done
    return 1
}

main() {
    local project_dir="${0%/*}"
    local lago_repo="http://templates.ovirt.org/repo/repo.metadata"
    local vm_name="vm-01"
    local prefix="$(pwd)"
    local script=$(readlink -f "$0")
    local script_path=$(dirname "$script")
    declare -a pkgs \
        suites \
        reposync_config_base_files array_repo_files \

    local options=$( \
        getopt \
            -o hp:s: \
            --long help,pkg:suite: \
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
            -p|--pkg)
                pkgs+=("$2")
                shift 2
                ;;
            -s|--suite)
                suites+=("$2")
                shift 2
                ;;
            --)
                shift
                break
                ;;
        esac
    done

    trap "cleanup $vm_name $prefix" EXIT
    reposync_config_base_files+=("$@")
    reposync_config_base_files=($(uniq_array "${reposync_config_base_files[@]}"))
    logger.info "Collect information to build updated reposync file: ${reposync_config_base_files[*]}"

    for reposync in "${reposync_config_base_files[@]}"; do
        reposync=$(realpath "$reposync")
        [[ ! -f "$reposync" ]] && {
            logger.error "$reposync is not a file"
            continue
        }

        exist_in_array "$reposync" "${array_repo_files[*]}" && continue
        array_repo_files+=("$reposync")
        create_updated_reposync_file "$reposync" "$script_path" "${pkgs[*]}" "${suites[*]}"
        cleanup "$vm_name" "$prefix"
        continue
    done
    echo "Success !"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    main "$@"
fi
