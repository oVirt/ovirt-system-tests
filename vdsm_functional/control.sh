prep_suite () {
	sed -e "s,@SUITE@,${SUITE},g" < ${SUITE}/init.json.in > ${SUITE}/init.json
}

run_suite () {
	testenv_init
	testenv_repo_setup
	testenv_start
	testenv_deploy

        for HOST in host-el7 host-fc21 host-fc22
        do
           testenvcli shell $HOST -c "pushd /usr/share/vdsm/tests && \
           ./run_tests.sh --with-xunit --xunit-file=/tmp/nosetests-${HOST}.xml -s functional/*Tests.py && \
           popd" > ../$HOST
        done
}
