#!/bin/bash -e

CLI="lagocli"

if [[ ! -z "$ENGINE_BUILD_GWT" ]];
then
	ENGINE_WITH_GWT="--engine-with-gwt"
fi

usage () {
	echo "
Usage:

$0 SUITE [-o|--output path] [-e|--engine path] [-v|--vdsm path] [-i|--ioprocess path]

This script runs a single suite of tests (a directory of tests repo)

Positional arguments:
	SUITE
		Path to directory that contains the suite to be executed

Optional arguments:
	-o,--output PATH
		Path where the new environment will be deployed.

	-e,--engine PATH
		Path to ovirt-engine source that will be available in the environment

	-v,--vdsm PATH
		Path to vdsm source that will be available in the environment

	-i,--ioprocess PATH
		Path to ioprocess source that will be available in the environment
"
}

env_init () {
	$CLI init 		\
		$PREFIX			\
		$SUITE/init.json	\
		--template-repo-path $SUITE/template-repo.json
}

env_repo_setup () {
	cd $PREFIX
	$CLI ovirt reposetup 	\
		--reposync-yum-config $SUITE/reposync-config.repo \
		--engine-dir=$ENGINE_DIR \
		$ENGINE_WITH_GWT \
		--vdsm-dir=$VDSM_DIR \
		--ioprocess-dir=$IOPROCESS_DIR
}

env_start () {
	cd $PREFIX
	$CLI start
}

env_deploy () {
	cd $PREFIX
	$CLI ovirt deploy
}

env_run_test () {
	cd $PREFIX
	$CLI ovirt runtest $1
}

env_collect () {
	cd $PREFIX
	$CLI ovirt collect --output $1
}

if [ $# -lt 1 ];
then
	usage
	exit 1
fi

export SUITE=$(realpath $1);
export PREFIX=$PWD/deployment-$(basename $SUITE)
shift 1;

TEMP=$(getopt -o ho:v:e:i: --long help,output:,vdsm:,engine:,ioprocess: -n 'run_suite.sh' -- "$@")
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
		-i|--ioprocess)
			IOPROCESS_DIR=$(realpath $2)
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
