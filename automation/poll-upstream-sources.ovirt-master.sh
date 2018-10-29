#!/bin/bash -ex

commit_changes_to_git() {
    local repofile_real_path="${1:?}"
    local my_repofile="${2:?}"
    local modified_date=$(stat -c %Y "$repofile_real_path")
    local md5=$(echo "$modified_date" | md5sum | cut -d ' ' -f1)
    # To revert after fixing mock_runner
    curl -Lo .git/hooks/commit-msg https://gerrit.ovirt.org/tools/hooks/commit-msg
    chmod +x .git/hooks/commit-msg

    git config user.name "jenkins CI"
    git config user.email "jenkins@ovirt.org"
    # end revert
    git add "$repofile_real_path"
    git commit -s -m "Auto create $my_repofile" -m "x-md5: $md5"
}

main() {
    local my_repofile="$0"
    my_repofile=${my_repofile/poll-upstream-sources\.//}
    # Leaving just the base dir
    my_repofile=${my_repofile##*/}
    # Remove file extension
    my_repofile=${my_repofile%.*}
    local repofile_real_path=$(realpath "common/yum-repos/${my_repofile}.repo")
    local repofile_template="${repofile_real_path}.in"
    local modified_repofile=$(realpath "${my_repofile}.repo.in.modified")
    local branch_name="${my_repofile}_autobuild"

    local application_path=$(pwd)

    git branch | grep -w "$branch_name" && {
        echo "$branch_name branch exists,remove"
        git branch -D "$branch_name"
    }

    git checkout -b "$branch_name"
    rm -f "$modified_repofile"
    rm -rf "${application_path}/exported-artifacts"

    local real_path_builder_script=$(realpath \
        "common/scripts/reposync-config-builder/build_reposync_config.sh")
    "$real_path_builder_script" "$repofile_template"

    [[ -f "$modified_repofile" ]] || {
        echo Failed to generate "$repofile_template"
        exit 1
    }
    cp "$modified_repofile" "$repofile_real_path"
    mkdir "${application_path}/exported-artifacts"
    cp "$repofile_real_path" "${application_path}/exported-artifacts/${my_repofile}.repo"
    commit_changes_to_git "$repofile_real_path" "$my_repofile"

}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    main "$@"
fi
