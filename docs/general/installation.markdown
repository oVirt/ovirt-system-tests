Getting started
===============
This document describes how to get started with running oVirt system tests.<br>


Prerequisites
=============

#### Operating System
Currently OST can run on either Fedora 23+ or Centos 6/7.<br>
(We are working on adding support for more distributions in the near future).

#### Disk Space
Most tests suites will require that you have at least 36GB of free space under the<br>
/var/lib/lago directory and an extra 200MB wherever you are running them.

If you don't have enough disk space on /var, you can change the location<br>
in lago configuration, for more info see [Lago docs][1].

#### Memory
While the memory requirements are derived from the VM specs you'll have in the test suite<br>
It is recommended that the server you're using will have at least 8GB of RAM in order to<br>
run the basic suite.

**Choose either automated or manual install to setup the environment.**
### Automated Install

Please run the following script on your testing env to install all prerequisits:

```
wget https://raw.githubusercontent.com/lago-project/lago-demo/master/install_scripts/install_lago.sh
./install_lago.sh
```

### Manual Install

Please follow the guidelines below to setup your environment:

#### Installing dependencies

Running OST requires installation of [Lago][1] & [repoman][2] projects.

**For Fedora:**
```
[lago]
baseurl=http://resources.ovirt.org/repos/lago/stable/0.0/rpm/fc$releasever
name=Lago
enabled=1
gpgcheck=0

[ovirt-ci-tools]
baseurl=http://resources.ovirt.org/repos/ci-tools/fc$releasever
name=oVirt CI Tools
enabled=1
gpgcheck=0
```

**For EL distros (such as CentOS, RHEL, etc.):**
```
[lago]
baseurl=http://resources.ovirt.org/repos/lago/stable/0.0/rpm/el$releasever
name=Lago
enabled=1
gpgcheck=0

[ovirt-ci-tools]
baseurl=http://resources.ovirt.org/repos/ci-tools/el$releasever
name=oVirt CI Tools
enabled=1
gpgcheck=0
```

**TODO**: point to the release rpm once it's implemented, and use gpgcheck=1

Once you have them, install the following packages::
```
    yum install python-lago lago python-lago-ovirt lago-ovirt
```
This will install all the needed packages.

[1]: http://lago.readthedocs.io
[2]: http://repoman.readthedocs.io

#### Machine set-up

Make sure your laptop or test server has the folllowing setup:

* *Virtualization and nested virtualization support*

    Make sure that virtualization extension is enabled on the CPU, otherwise,
    you might need to enable it in the BIOS. Generally, if virtualization extension
    is disabled, `dmesg` log would contain a line similar to:
    ```
        kvm: disabled by BIOS
    ```

    **NOTE**: you can wait until everyithing is setup to reboot and change the
    bios, to make sure that everyithing will persist after reboot

* *Verify nested virtualization is enabled*
    ```
        $ cat /sys/module/kvm_intel/parameters/nested
    ```
       This command should print `Y` if nested virtualization is enabled, otherwise,
       enable it the following way:

       Edit `/etc/modprobe.d/kvm-intel.conf` and add the following line:
    ```
        options kvm-intel nested=y
    ```
       Reboot, and make sure nested virtualization is enabled.


*  *Setting up libvirt*

    Make sure libvirt is configured to run:
    ```
        $ systemctl enable libvirtd
        $ systemctl start libvirtd
    ```

*  *Configure SELinux*

    At the moment, this framework might encounter problems running while SELinux
    policy is enforced.

    To disable SELinux on the running system, run:
    ```
        $ setenforce 0
    ```
    To disable SELinux from start-up, edit `/etc/selinux/config` and set:
    ```
        SELINUX=permissive
    ```

*  *User permissions setup*

    Running lago requires certain permissions, so the user running it should be
    part of certain groups.

    Add yourself to lago and qemu groups:
    ```
        $ usermod -a -G lago USERNAME
        $ usermod -a -G qemu USERNAME
    ```
    It is also advised to add qemu user to your group (to be able to store VM files
    in home directory):
    ```
        $ usermod -a -G USERNAME qemu
    ```
    For the group changes to take place, you'll need to re-login to the shell.
    Make sure running `id` returns all the aforementioned groups.

    Make sure that the qemu user has execution rights to the dir where you will be
    creating the prefixes, you can try it out with:
    ```
        $ sudo -u qemu ls /path/to/the/destination/dir
    ```
    If it can't access it, make sure that all the dirs in the path have your user
    or qemu groups and execution rights for the group, or execution rights for
    other (highly recommended to use the group instead, if the dir did not have
    execution rights for others already)

    It's very common for the user home directory to not have group execution
    rights, to make sure you can just run:
    ```
        $ chmod g+x $HOME
    ```
    And, just to be sure, let's refresh libvirtd service to ensure that it
    refreshes it's permissions and picks up any newly created users:
    ```
        $ sudo service libvirtd restart
    ```

#### Preparing the workspace for running the tests

Create a directory where you'll be working, *make sure qemu user can access it*.<br>
We will be using the example configurations of lago, for a custom setup you might want to create your own.

You're now ready to run the tests! checkout [Running the tests](running_tests.html) for more info.
