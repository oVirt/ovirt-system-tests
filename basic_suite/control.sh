prep_suite () {
	sed -e "s,@SUITE@,${SUITE},g" < ${SUITE}/init.json.in > ${SUITE}/init.json
}

run_suite () {
	testenv_init
	testenv_repo_setup
	testenv_start
	testenv_deploy

	for script in $(find $SUITE/test-scenarios -type f -name '*.py' | sort); do
		echo "Running script " $(basename $script)
		testenv_run_test $script
		testenv_collect $PREFIX/test_logs/post-$(basename $script)
	done
}
