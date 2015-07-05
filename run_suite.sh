#!/bin/bash -e

TESTENVCLI="testenvcli"

usage () {
	echo "Usage:"
	echo "$0 SUITE [-o|--output path] [-e|--engine path] [-v|--vdsm path]"
}

testenv_init () {
	$TESTENVCLI init 		\
		$PREFIX			\
		$SUITE/init.json	\
		--template-repo-path $SUITE/template-repo.json
}

testenv_repo_setup () {
	cd $PREFIX
	$TESTENVCLI ovirt reposetup 	\
		--reposync-yum-config $SUITE/reposync-config.repo \
		--engine-dir=$ENGINE_DIR \
		--engine-with-gwt 	\
		--vdsm-dir=$VDSM_DIR
}

testenv_start () {
	cd $PREFIX
	$TESTENVCLI start
}

testenv_deploy () {
	cd $PREFIX
	$TESTENVCLI ovirt deploy
}

testenv_run_test () {
	cd $PREFIX
	$TESTENVCLI ovirt runtest $1
}

testenv_collect () {
	cd $PREFIX
	$TESTENVCLI ovirt collect --output $1
}

export SUITE=$(realpath $1);
export PREFIX=$PWD/deployment-$(basename $SUITE)
shift 1;

TEMP=$(getopt -o ho:v:e: --long help,output:,vdsm:,engine: -n 'run_suite.sh' -- "$@")
eval set -- "$TEMP"

while true ; do
	case $1 in
		-o|--output)
			PREFIX=$(realpath $2)
			shift 2
			;;
		-v|--vdsm)
			VDSM_DIR=$(realpath $2)
			shift 2
			;;
		-e|--engine)
			ENGINE_DIR=$(realpath $2)
			shift 2
			;;
		-h|--help)
			usage
			exit 0
			;;
		--)
			shift
			break
			;;
		*)
			echo "Invalid argument $1"
			usage
			exit 1
			;;
	esac
done

echo "Running suite found in ${SUITE}"
echo "Environment will be deployed at ${PREFIX}"

. ${SUITE}/control.sh

prep_suite
run_suite
