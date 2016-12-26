#!/bin/bash -xe
#trap read debug
# install common deps

# Project's root
PROJECT="$PWD"

#Constant regex
COMMONS_REGEX=(common automation run\_suite\.sh)
BASIC_SUITES_REGEX=($(find . -maxdepth 1 -name "basic-suite*" -exec basename \{} \;))
ALL_SUITES_REGEX=(*-suite-*)

#Array to hold all the suites
#which will be executed
SUITES_ARR=()

NEW_CHANGES=$(
    git show --pretty='format:' --name-only \
    | sed '/^\s*$/d' \
    | cut -d'/' -f1 \
    | sort \
    | uniq
)

#Check if any common file was changed
#and run all basic suites
for change in "${COMMONS_REGEX[@]}"
do
  if grep -E "$change" <<< "${NEW_CHANGES[@]}"; then
    SUITES_ARR=(${BASIC_SUITES_REGEX[@]})
    break
  fi
done

#Check if any suite was changed
for suite in "${ALL_SUITES_REGEX[@]}"
do
  if grep -E "$suite" <<< "${NEW_CHANGES[@]}"; then
    SUITES_ARR+=($suite)
  fi
done

#Remove duplicates and sort the suites
SUITES_TO_RUN=($(
  printf '%s\n' "${SUITES_ARR[@]}" \
  | awk -F- '{print $NF","$0}' \
  | sort -t"," -k1 -r -u \
  | cut -d"," -f2
))

# This function will collect the logs
# of each suite to a different directory
collect_suite_logs() {
  local test_logs="$PROJECT"/exported-artifacts
  if [[ -d "$test_logs" ]]; then
    suite_logs="$PROJECT/$suite""__logs"
    # Rename the logs
    mv "$test_logs" "$suite_logs"
  fi
}

# This function will collect the logs from
# all the suites and store them in exported-artifacts,
# which later will be collected by jenkins
collect_all_logs() {
    local logs=logs
    [[ -d "$logs" ]] || mkdir $logs
    # mock_cleanup.sh collects the logs from ./logs, ./*/logs
    # The root directory is jenkins' workspace
    mv *__logs logs
}

# collect the logs  on failure
on_error() {
  echo "Error on line: $1"
  collect_suite_logs
  collect_all_logs
}


pwd

# clean old logs
if [[ -d "$PROJECT/exported-artifacts" ]]; then
    rm -rf "$PROJECT/exported-artifacts"
fi

#Trap any errors and print the line number
trap 'on_error $LINENO' SIGTERM ERR

echo "Suites to run:"
echo "${SUITES_TO_RUN[@]}"

# run on each version + collect its logs
for suite in "${SUITES_TO_RUN[@]}"
do
    #Extract version:
    ver=$(echo "$suite" | rev | cut -d"-" -f1 | rev)

    #Copy the exta_sources file to suite's dir
    cp "$PROJECT""/common/latest-tested-src/$ver-latest-tested" "$PROJECT/$suite/""extra_sources"
    #Match the suite's name to the execution script's name
    exec_suite=$(sed 's/-/_/g' <<< "$suite")
    echo "running $exec_suite.sh"
    automation/"${exec_suite}.sh"

    # collect the logs for the current suite
    collect_suite_logs
done

# collect all the suit's logs to exported-artifacts
collect_all_logs
