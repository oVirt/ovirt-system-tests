Getting started
===============
This document describes how to get started with running oVirt system tests

System requirements
====================

#### Operating System
Currently OST can run on either supported Fedora versions or Centos 7.

#### Disk Space
Most tests suites will require that you have at least 15GB of free space under
the /var/lib/lago directory and an extra 200MB wherever you are running them.

If you don't have enough disk space on /var, you can change the location
in lago configuration, for more info see [Lago config].

#### Memory
While the memory requirements are derived from the VM specs you'll have in
the test suite, it is recommended that the host you're using will have at
least 8GB of RAM in order to run the basic suite.

Installing dependencies
======================

**NOTE**: The prefered way to run OST is inside a mock environment, created by
[mock_runner.sh] This method will ensure that the appropriate oVirt engine SDK
is being installed. Each suite should use the latest oVirt engine SDK that is
available for its version (for example, basic-suite-master should use the sdk
from [ovirt-master latest tested repo]).

### When Running OST with/without mock

#### Install Lago

[Lago installation manual]

#### Configure Firewall

During the run of OST, Lago creates an HTTP server that serves RPMs to
th VMs. This action requires that port 8585 on the localhost will be accessible
from the subnets used by Lago.

**NOTE:** This step is not needed if you run firewalld, because it will
be configured automatically when installing `lago-ovirt`.

Add the following iptables rule (in /etc/sysconfig/iptables):

```
#OST
-A INPUT -p tcp --dport 8585 -s 192.168.0.0/16 -j ACCEPT
#END OST
```

### When running OST with mock

#### Install mock

Follow the instructions in "Setting up mock_runner" section at [mock_runner.sh]

### When Running OST without mock

#### Install Lago oVirt

**NOTE:** This step is not needed if you installed lago with the install
script.

Configure the following repo:

**For EL distros (such as CentOS, RHEL, etc.):**
```
[ovirt-ci-tools]
baseurl=http://resources.ovirt.org/repos/ci-tools/el$releasever
name=oVirt CI Tools
enabled=1
gpgcheck=0
```
**For Fedora:**
```
[ovirt-ci-tools]
baseurl=http://resources.ovirt.org/repos/ci-tools/fc$releasever
name=oVirt CI Tools
enabled=1
gpgcheck=0
```
Install lago-ovirt

```
yum install lago-ovirt
```

#### Install oVirt-engine python sdk

**NOTE:** This step is not needed if you run OST in a mock environment.

Configure the following repo (replace $VERSION with the version of the
suite that you are running, for example: master or 4.1):

**For EL distros (such as CentOS, RHEL, etc.):**

```
[ovirt-tested-$VERSION]
baseurl=http://resources.ovirt.org/repos/ovirt/tested/$VERSION/rpm/el$releasever
name=oVirt-$VERSION
enabled=1
gpgcheck=0
```

**For Fedora:**

```
[ovirt-tested-$VERSION]
baseurl=http://resources.ovirt.org/repos/ovirt/tested/$VERSION/rpm/fc$releasever
name=oVirt-$VERSION
enabled=1
gpgcheck=0
```

Install oVirt engine SDK v3 and v4:

```
yum install python-ovirt-engine-sdk4 ovirt-engine-sdk-python
```

**NOTE:** Before each run of OST make sure that you have the latest SDK installed.

### Next steps

You're now ready to run the tests! checkout [Running the tests](running_tests.html) for more info.

[Lago config]: http://lago.readthedocs.io/en/latest/Configuration.html

[Lago installation manual]: http://lago.readthedocs.io/en/latest/Installation.html#rpm-based-fedora-24-centos-7-3

[mock_runner.sh]: http://ovirt-infra-docs.readthedocs.io/en/latest/CI/Using_mock_runner/index.html

[ovirt-master latest tested repo]: http://resources.ovirt.org/repos/ovirt/tested/master/rpm/
