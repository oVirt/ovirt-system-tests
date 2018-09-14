# Openshift on oVirt

This suite's goal is to perform a deployment of openshift on
oVirt 4.2 plus the extras provided by [ovirt-openshift-extensions project][1]

## Steps

1. Start ovirt 4.2 from images using [ovirt orb][ovirt orb]
2. Install openshift 3.10 using openshift ansible (all-in-one)
3. Install ovirt flexvolume driver and volume provisioner
4. Test that openshift can use a data domain from ovirt
5. Test spinning a container with flexvolume from above succeeded
   and the container see the volume
6. Test tearing down the container
7. Test tearing down the storage claim

## Tools used

- ovirt orb to spin ovirt from vms
- [ovirt-openshift-extensions-ci container][ci container] , [code is here][ci code], to install openshift + extensions
- ansible to automate the installation and executes the test stages


[1]: https://github.com/ovirt/ovirt-openshift-extensions
[ovirt orb]: https://ovirt.org/documentation/ovirt-orb/
[ci container]: https://quay.io/repository/rgolangh/ovirt-openshift-extensions-ci
[ci-code]: https://github.com/ovirt/ovirt-openshift-extensions/tree/master/automation/ci
