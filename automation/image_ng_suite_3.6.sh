#!/bin/bash -xe

# This script is meant to be run within a mock environment, using
# mock_runner.sh or chrooter, from the root of the repository:
#
# $ cd repository/root
# $ mock_runner.sh -e automation/basic_suite_3.5.sh
# or
# $ chrooter -s automation/basic_suite_3.5.sh
#

cleanup() {
	rm -rf exported-artifacts
    mkdir -p exported-artifacts
    [[ -d deployment-image_ng_suite_3.6/current/logs ]] \
    && mv deployment-image_ng_suite_3.6/current/logs exported-artifacts/lago_logs
    find deployment-image_ng_suite_3.6 \
        -iname nose\*.xml \
        -exec mv {} exported-artifacts/ \;
    [[ -d test_logs ]] && mv test_logs exported-artifacts/
    ./run_suite.sh --cleanup image_ng_suite_3.6
    exit
}

# needed to run lago inside chroot
export LIBGUESTFS_BACKEND=direct

#Turn on the next 3 lines for virt debug
#export LIBGUESTFS_DEBUG=1
#export LIBGUESTFS_TRACE=1
#libguestfs-test-tool

# Hack sudo to ignore tty
sed -i -e 's/Defaults    requiretty.*/ #Defaults    requiretty/g' /etc/sudoers

trap cleanup SIGTERM EXIT
res=0

engine="$(find "images/exported-artifacts" -mindepth 1 -maxdepth 3 -type f -name '*.ova' -print -quit)"
node="$(find "images/exported-artifacts" -mindepth 1 -maxdepth 3 -type f -name '*.squashfs.img' -print -quit)"

rm -rf ovirt-node-ng || true
git clone https://gerrit.ovirt.org/ovirt-node-ng
pushd ovirt-node-ng
git checkout ovirt-3.6
#remove this line when node_ng get patched
sed -i 's/--extra-args "/--wait=-1 --graphics none --extra-args "console=ttyS0 /' Makefile.am
#build installed qcow
./autogen.sh
make boot.iso
mv ../$node ./ovirt-node-ng-image.squashfs.img
touch ovirt-node-ng-image.squashfs.img
#use script to cheat the TTY
script -e -c "sudo 	make installed-squashfs"

#give it a chance to finish installing
sleep 10
while [ "$(virsh list | grep node | wc -l)" -ne "0" ]; do sleep 1 ; echo "waiting" ; done
popd

./run_image_suite.sh image_ng_suite_3.6 -n ovirt-node-ng/ovirt-node-ng-image.installed.qcow2 -e $engine \
|| res=$?
exit $res
