Performance Suite
===

Purpose
===
This suite makes it possible to configure the setup size. It lets you set the number
 of host (2 by default for almost all suites) and/or VMs, using environment variable or vars/main.yml
The outcome is the ability to run system tests on large setup i.e 100/5000 hosts/vms or 300/300 all depending
on the setup type.
If you are short on resources you can make the hosts and VMs run on ovirt-vdsmfake, again using environment variable (see Usage)

It makes very much sense to port those dynamic features to the basic suite, but this first this suite needs to
fully prove it self useful

Usage
===
The suite is soft-linking almost all of the basic-suite files and just adds
a test scenario which does:
- deploy collectd + fluentd, forwarding to the `engine` machine
- create a working setup with configurable num of hosts/vms
- Save the fluentd outfile with all the events - that can be uploaded to
 ElasticSearch for analysis(basic-suite-master already has that)

- Configure the number of hosts to deploy using vars/main.yml
```bash
# cat performance-suite-master/vars/main.yml
...
hostCount: 2
```

- Configure the number of Hosts using environment variable
```bash
# OST_HOST_COUNT=100 ./run_suite.sh performance-suite-master
```

- Configure the number of VMs using environment variable
```bash
# OST_VM_COUNT=1000 ./run_suite.sh performance-suite-master
```

- Run with ovirt-vdsmfake (no need to create a VM per deployed hosts, i.e 1 VM is needed for the execution)
```bash
# OST_USE_VDSMFAKE=1 ./run_suite.sh performance-suite-master
```
