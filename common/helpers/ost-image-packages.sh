#!/bin/bash

suite=$1
OST_IMAGES_DISTRO=$2

source common/helpers/ost-images.sh

if [[ -f "$suite/ost.json" ]]; then
    ost_json_file="$suite/ost.json"
    root_disk_vars=$(jq '.vms[] | .root_disk_var' $ost_json_file)

    packages=()
    for var in $root_disk_vars; do
        package_name=$(echo $var | tr -d '"' )_PACKAGE
        package_value=${!package_name}
        packages+=("$package_value")
    done

    {
        printf '{"ost_images_rpms":['
        for e in "${packages[@]}"; do
            printf '"%s",' "$e"
        done | sed 's/,$//'
        printf ']}\n'
    } > ost_image_vars.json
fi
