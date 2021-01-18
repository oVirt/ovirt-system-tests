Providing Packages For The Test Suite
=======================================

OST has a flexible mechanism for collecting packages that will be used in the
tests, those are the packages that will be used to install oVirt and its
dependencies.

The Flow
==========


**FIXME: This section si OBSOLETE: ovirt-4.2 is no longer used**

$SUITE is the path to the test suite.

1. packages that were specified in `$SUITE/reposync-config.repo` file are being
synced to the local cache located in `/var/lib/lago/reposync` using reposync.
This cache is shared between consecutive runs of the tests suites.
An example of a reposync directory:

    ```
    /var/lib/lago$tree -d -L 1 reposync
    reposync
    ├── cache
    ├── centos-base-el7
    ├── centos-extras-el7
    ├── centos-opstools-testing-el7
    ├── centos-ovirt-4.2-el7
    ├── centos-ovirt-common-el7
    ├── centos-qemu-ev-release-el7
    ├── centos-updates-el7
    ├── copr-sac-gdeploy-el7
    ├── epel-el7
    ├── glusterfs-3.10-el7
    ├── ovirt-master-snapshot-static-el7
    └── ovirt-master-tested-el7
    ```

2. Inside Lago's prefix, repoman creates a directory named `internal_repo` and
adds to it the RPMs found in the sources that were specified using
`-s,--extra-rpm-source` option to `run_suite.sh`. An example of an
`internal_repo`:

    ```
    ~/gerrit.ovirt.org/ovirt-system-tests (adding_reposync_repoman_docs)$tree \
    -d -L 2 deployment-basic-suite-master/default/internal_repo/

    deployment-basic-suite-master/default/internal_repo/
    └── el7
        ├── noarch
        ├── repodata
        └── x86_64

    ```

    *Note*: This step is executed by `lago ovirt reposetup` command, and should
    be called only after the Lago environment was created.

3. By the order of the repos in `$SUITE/reposync-config.repo`, for each repo,
repoman takes the packages that reposync synced, and add them to the
`internal_repo`. A few notes about this step:

    * repoman works in a 'greedy' manner that is, it will take the first
    package it sees and only it (even if later it will find the same package
    with a newer version), in particular:

        * Packages from the sources specified with `-s,--extra-rpm-source` has
          precedence over the packages synced with reposync.

        * For two repos 'a' and 'b', if 'a' comes before 'b' in
          `$SUITE/reposync-config.repo`, packages from repo 'a' will have
          precedence over packages from repo 'b'.

    * Depends on the distros of Lago's VMs, <b>only
      packages from repos that match to those distros will be taken from</b>
      `$SUITE/reposync-config.repo`. The distro of the VMs is taken from
      `$SUITE/LagoInitFile` or from the metadata of the Lago image. The distro
      of the repo is taken from the suffix of its name (the one in brackets),
      as it appears in `$SUITE/reposync-config.repo`.

        <b><u>For example:</u>
        if the repo's name is `epel-el7`, Lago will consider the string after
        the last `-` as the distro, in the example it will be `el7`.
        If the distro suffix is missing from the repo's name, <u>repoman will
        not take packages from that repo.</u>
        </b>

    * The internal repo is used only for the current test suite and it will be
      removed after the test suite finishes.

4. During deploy stage, the VMs are configured to use the internal repo. The
configuration is done by `common/deploy-scripts/add_local_repo.sh`, which is
part of the deploy scripts list in `$SUITE/LagoInitFile`. An example of repo
configuration taken from Lago's host:

    ```
    [root@lago-basic-suite-master-engine ~]# cat \
    /etc/yum.repos.d/local-ovirt.repo

    [alocalsync]
    name=Latest oVirt nightly
    baseurl=http://192.168.201.1:8585/el7/
    enabled=1
    skip_if_unavailable=1
    gpgcheck=0
    repo_gpgcheck=0
    cost=1
    keepcache=1
    ip_resolve=4
    ```

      *Note*: The ip specified in 'baseurl' is Lago's management network ip.

5. During `lago ovirt deploy`, Lago opens an http server that serves the
internal_repo. The server listens to port `8585` on the management network's
bridge. The http server can be also created with `lago ovirt serve`.

The Tools
==========

reposync
---------
<i>reposync is used to synchronize a remote yum repository to a local
directory, using yum to retrieve the packages</i>. (Taken from reposync's man
page).

reposync is part of `yum-utils`.

For more info see `man reposync`.

snippet of a reposync config file:

```
[main]
reposdir=/etc/reposync.repos.d
max_connections=50
ip_resolve=4
gpgcheck=0

[ovirt-master-tested-el7]
name=oVirt Master Latest Tested
baseurl=http://resources.ovirt.org/repos/ovirt/tested/master/rpm/el7/
enabled=1
max_connections=10
exclude =  ioprocess-debuginfo *-devel
 java-ovirt-engine-sdk4
 otopi-devtools
 ovirt-engine-nodejs-*
proxy=_none_
```

The following options can be added to each section:
"ost_skip_injection"
If set to True, the repo will not be modified by the plugin.
The packages won't be listed in the reposync-config file.
(i.e ost_skip_injection = True)

repoman
--------
repoman is a tool for building custom yum repos from different kinds of
sources.
For more info see  http://repoman.readthedocs.io/en/latest/


Troubleshooting
=================

1. Info about the actions of reposync and repoman (including the list of
packages that were inserted to the `internal_repo`) can be found in Lago's log
located at:
`deployment-$SUITE/default/logs/lago.log`.

2. A package that the test needs is missing from the `internal_repo`:
    * In `$SUITE/reposync-config.repo`, check that the package is not excluded.
    * In `$SUITE/reposync-config.repo`, If the package's repo has the
      `includepkgs` filter, check that the packages is on the list.
    * In `$SUITE/reposync-config.repo`, verify that all the repo's names has a
      `-DISTRO` suffix (for example `*-el7`).
    * Verify that the package exist in one of the repos that were specified in
      `$SUITE/reposync-config.repo`, or in one of the sources that were passed
      to `-s,--extra-rpm-source`.

3. A package that the test needs is in the `internal_repo` but it has the wrong
   version.
    * Most of the times this issue is caused by "precedence rules" as explained
      above.
    * The needed version of the packages is not in one of the sources passed to
      `-s,--extra-rpm-source`, nor in one of the repos in `reposync config`.
