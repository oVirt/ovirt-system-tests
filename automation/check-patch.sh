#!/bin/bash -xe

# install common deps

# Which tests suites to run

#TODO: update commons with valid paths that are relevant
#to ALL tests, right now its hard to understand exactly
#which suite is using what
WORKSPACE="$PWD"
COMMONS=
TESTS_36_PATH="basic_suite_3.6"
TESTS_40_PATH="basic_suite_4.0"
TESTS_MASTER_PATH="basic_suite_master"

# for now all tests are on master branch
# so we have to check which tests were changed
# notice that multiple versions can be updated
# on the same patch
VERSIONS_TO_RUN=()
if git show --pretty='format:' --name-only | grep -E \
    "$COMMONS"; then
    VERSIONS_TO_RUN+=('3.6' '4.0' 'master')

else
  if git show --pretty='format:' --name-only | grep -E \
      "$TESTS_36_PATH" ; then
      VERSIONS_TO_RUN+=('3.6')
  fi

  if git show --pretty='format:' --name-only | grep -E \
      "$TESTS_40_PATH"; then
      VERSIONS_TO_RUN+=('4.0')
  fi

  if git show --pretty='format:' --name-only | grep -E \
      "$TESTS_MASTER_PATH"; then
      VERSIONS_TO_RUN+=('master')
  fi
fi

pwd

# clean old logs
rm -rf "$WORKSPACE/exported-artifacts"
mkdir -p "$WORKSPACE/exported-artifacts"

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

    # collecting logs
    TESTS_LOGS="$WORKSPACE/ovirt-system-tests/exported-artifacts"
    if [[ -d "$TESTS_LOGS" ]]; then
        mv "$TESTS_LOGS/"* "$WORKSPACE/exported-artifacts/"
    fi
done
