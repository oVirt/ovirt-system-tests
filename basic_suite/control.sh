prep_suite () {
	sed -e "s,@SUITE@,${SUITE},g" < ${SUITE}/init.json.in > ${SUITE}/init.json
}

run_suite () {
	testenv_init
	testenv_repo_setup
	testenv_start
	testenv_deploy

	for script in $(ls -1 $SUITE/test_scenarios); do
		echo "Running script " $script
		testenv_run_test $script
		testenv_collect $PREFIX/test_logs/post-$(basename $script)
	done
}
