#!/bin/bash -xe

# install common deps

# Which tests suites to run

#TODO: update commons with valid paths that are relevant
#to ALL tests, right now its hard to understand exactly
#which suite is using what

# Project's root
PROJECT="$PWD"
COMMONS=
TESTS_36_PATH="basic-suite-3.6"
TESTS_40_PATH="basic-suite-4.0"
TESTS_MASTER_PATH="basic-suite-master"

# This function will collect the logs
# of each suite to a different directory
collect_suite_logs() {
  local test_logs="$PROJECT"/exported-artifacts
  if [[ -d "$test_logs" ]]; then
      suite_logs="$PROJECT"/"$TEST_SUITE_PREFIX$VER"__logs
      # Rename the logs
      mv "$test_logs" "$suite_logs"
  fi
}

# This function will collect the logs from
# all the suites and store them in exported-artifacts,
# which later will be collected by jenkins
collect_all_logs() {
  if ! [[ -d logs ]]; then
    mkdir logs
  fi
  # mock_cleanup.sh collects the logs from ./logs, ./*/logs
  # The root directory is jenkins' workspace
  mv *__logs logs
}

# collect the logs  on failure
on_error() {
  collect_suite_logs
  collect_all_logs
}

trap on_error SIGTERM ERR

# for now all tests are on master branch
# so we have to check which tests were changed
# notice that multiple versions can be updated
# on the same patch
VERSIONS_TO_RUN=()
if git show --pretty='format:' --name-only | grep -E \
    "$COMMONS"; then
    VERSIONS_TO_RUN+=('master' '4.0' '3.6')

else
  if git show --pretty='format:' --name-only | grep -E \
      "$TESTS_MASTER_PATH" ; then
      VERSIONS_TO_RUN+=('master')
  fi

  if git show --pretty='format:' --name-only | grep -E \
      "$TESTS_40_PATH"; then
      VERSIONS_TO_RUN+=('4.0')
  fi

  if git show --pretty='format:' --name-only | grep -E \
      "$TESTS_36_PATH"; then
      VERSIONS_TO_RUN+=('3.6')
  fi
fi

pwd

# clean old logs
rm -rf "$PROJECT/exported-artifacts"

# run on each version + collect its logs
for VER in "${VERSIONS_TO_RUN[@]}"
do
	# we need a specific SDK for each oVirt version
	/usr/bin/dnf install -y lago-ovirt ovirt-engine-sdk-python --disablerepo=ovirt* --enablerepo=ovirt-$VER*
	TEST_SUITE_PREFIX="basic_suite_"
	echo "running tests for version $VER"
	RUN_SCRIPT=$TEST_SUITE_PREFIX$VER".sh"
	echo "running $RUN_SCRIPT"
	automation/${RUN_SCRIPT}

	# cleanup: we need to remove the sdk in case another test will run and need a different version
	/usr/bin/dnf remove -y ovirt-engine-sdk-python

  # collect the logs for the current suite
  collect_suite_logs
done

# collect all the suit's logs to exported-artifacts
collect_all_logs
