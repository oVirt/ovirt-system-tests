#!/usr/bin/env bash

prep_suite () {
	sed -e "s,@SUITE@,${SUITE},g" < ${SUITE}/init.json.in > ${SUITE}/init.json
}

run_suite () {
	env_init
	env_repo_setup
	env_start
	env_deploy

	for script in $(find $SUITE/test-scenarios -type f -name '*.py' | sort); do
		echo "Running script " $(basename $script)
		env_run_test $script
		env_collect $PREFIX/test_logs/post-$(basename $script)
	done
}
