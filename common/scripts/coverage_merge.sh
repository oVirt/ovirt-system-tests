#!/bin/bash

PYTHON=python3.9

get_run_url() {
    fragment=$(wget -q -O - $1/console | grep -oP "<a href='\K[^']+(?='>ds-ost-baremetal_manual #\d+</a> started)")
    base="${1%"${1#*//*/}"}"
    echo $base/$fragment
}

get_coverage_file() {
    echo $(wget -q -O - "$1" | jq -r '[.artifacts[] | {name: .fileName, path: .relativePath}] | map(if ( .name|test("[a-z-]*\\.[0-9a-f]*\\.coverage$")) then ( .path ) else ( empty ) end)[0]')
}

get_git_sha() {
    IFS='.' read -r -a split_coverage <<< "${1##*/}"
    echo "${split_coverage[1]}"
}

get_dist() {
    echo $(echo $1 | grep -oP "OST_IMAGE=\K\w+(?=\+)")
}

get_coverage_name() {
    IFS='/' read -r -a split_coverage <<< "$1"
    echo "${split_coverage[2]}"
}

[[ $# -eq 0 ]] && { echo "URL to 'ds-ost-baremetal-ost' job expected"; exit 1; }

source lagofy.sh
merge_dir="${OST_REPO_ROOT}/exported-artifacts/coverage-merge"

mkdir -p "$merge_dir"

echo "Getting the build URLs..."
build_urls=($(wget -q -O - "$1/lastSuccessfulBuild/api/json" | jq -r '.number as $build_id | .runs[] | if (.number == $build_id) then ( .url ) else ( empty ) end'))
echo "---"

for build_url in ${build_urls[@]}; do

    echo "Checking $build_url:"

    run_url=$(get_run_url $build_url)
    echo "URL of the run: $run_url"
    
    run_api="${run_url}/api/json"

    run_coverage=$(get_coverage_file $run_api)
    echo "Coverage file path: $run_coverage"

    run_git=$(get_git_sha $run_coverage)
    echo "GIT SHA of the commit used in the run: $run_git"

    [[ -z "$merged_git" ]] && merged_git="${run_git}"

    [[ $merged_git != $run_git ]] && { echo "Git hashes not matching between the runs"; exit 1; }

    run_distro=$(get_dist $build_url)
    echo "Distribution used in the run: $run_distro"

    coverage_name=$(get_coverage_name $run_coverage)
    
    echo "Downloading the coverage file $coverage_name..."
    wget -q -nc -O "$merge_dir/$run_distro.$coverage_name" "${run_url}/artifact/${run_coverage}"

    echo "---"

done

echo "Preparing for the coverage merge..."
ost_check_dependencies
source "${OST_REPO_ROOT}/.tox/deps/bin/activate"

git checkout "$merged_git"
python -m coverage combine --keep --data-file="${merge_dir}/.coverage" ${merge_dir}/*.${merged_git}.coverage

python -m coverage html -d "${merge_dir}/html" --data-file="${merge_dir}/.coverage"
