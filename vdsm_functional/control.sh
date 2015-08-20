prep_suite () {
	sed -e "s,@SUITE@,${SUITE},g" < ${SUITE}/init.json.in > ${SUITE}/init.json
}

run_suite () {
	env_init
	env_repo_setup
	env_start
	env_deploy

    for HOST in host-el7 host-fc21 host-fc22
    do
       lagocli shell $HOST -c "pushd /usr/share/vdsm/tests && \
       ./run_tests.sh --with-xunit --xunit-file=/tmp/nosetests-${HOST}.xml -s functional/*Tests.py && \
       popd" > ../$HOST
    done
}
