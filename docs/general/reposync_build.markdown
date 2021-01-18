Reposync File Build Process
=============================
This document describes:
- How to create an updated reposync file
- How the automated process is running through Jenkins

Reposync Template Files
=========================

**FIXME: This section si OBSOLETE: ovirt-4.2.repo is no longer used**

In order to create new updated reposync files we are using reposync template files.

These files are located in ovirt-system-tests/common/yum-repos

The structure of the template name is:
<REPOSYNC_FILE>.repo.in e.g: "ovirt-4.2.repo.in"

How to create a new reposync file?
=============================================
```
Command Usage:

build_reposync_config.sh [options] [REPOSYNC_0 [ REPOSYNC_1 ...]]

This script creates a VM with Lago, which will be used to generate a reposync-config. The generated reposync config will match the lago-template.

Positional arguments:
    REPOSYNC
        Path to the reposync config file that should be used.

Optional arguments:
    -p,--pkg PKG
        Package/s to include in the config
```

This command creates an updated reposync file, by using the template file: template.in
It searches for all the suites that are using the the same reposync file that was created from specific template file.
It collects information from all the suites in order to be able to create the new modified reposync file.
The new reposync file would be created by collecting the below information from all the suites:
- pkgs.txt - list of base, high level packages needed (not dependencies)
- the image template name located in <suite>vars/main.yml



#### How to run the command?
```
    $ cd ovirt-system-tests
    $ ./common/scripts/reposync-config-builder/build_reposync_config.sh <REPOSYNC_FILE_TEMPLATE>
```
The new updated/mofidied reposync-config file is created with a suffix 'modified'

#### Example, updating ovirt-master.repo:

We want to update ovirt-master.repo file

The steps for updating the ovirt-master.repo file:

- Update the template file: ovirt-master.repo.in
- Update the pkgs.txt file of the suite basic-suite-master - list of base, high level packages needed (not dependencies)

    Note: pkgs who are not listed in the pkgs.txt file and don't have dependencies won't be listed in the modified repo file, unless they were requested by the optional argument --pkg.

- Run the command:
```
    $ cd ovirt-system-tests
    $ ./common/scripts/reposync-config-builder/build_reposync_config.sh common/yum-repos/ovirt-master.repo.in
```

- The created file is ovirt-master.repo.in.modified, located on the root directory of ovirt-system-tests.
- copy the file:
```
    $ cp ovirt-master.repo.in.modified common/yum-repos/ovirt-master.repo
```

Poll upstream sources
========================
This process runs automatically every night through Jenkins and creates the updated reposync-config file.

The file is copied to the correct location.

The updated file sent as patch to gerrit only if there is a change in the new modified reposync-config file.

All the scripts for the automatic process are located in OST under automation directory:

 ```
 poll-upstream-sources.<REPOSYNC_FILENAME_WITHOUT_SUFFIX>.*
```
