#!/bin/bash -e

TESTENVCLI="testenvcli"

if [[ ! -z "$ENGINE_BUILD_GWT" ]];
then
	ENGINE_WITH_GWT="--engine-with-gwt"
fi

usage () {
	echo "Usage:"
	echo "$0 SUITE [-o|--output path] [-e|--engine path] [-v|--vdsm path] [-i|--ioprocess path]"
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
		$ENGINE_WITH_GWT \
		--vdsm-dir=$VDSM_DIR \
		--ioprocess-dir=$IOPROCESS_DIR
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
