# oVirt System Tests

[![Read the Docs]( https://readthedocs.org/projects/ovirt-system-tests/badge/?version=latest)](https://ovirt-system-tests.readthedocs.io/en/latest/)

Welcome to the oVirt System Tests source repository.

This repository is hosted on [GitHub:ovirt-system-tests](https://github.com/oVirt/ovirt-system-tests)

## System requirements

### Operating System

Currently OST can run on RHEL or CentOS Stream at least roughly matching the version used by oVirt or RHV.
Latest CentOS Stream or RHEL 8 or 9 should work.

### Disk Space

ost-images packages that contain the preinstalled images are fairly large, make sure you have enough disk space,
15 GB per each distro variant in /usr/share. Additional space is needed for actual suite run,
another 5GB at least in the directory where you run tests from.

### Memory

The memory requirements are derived from the VM specs you'll have in the test suite, it is recommended that the host you're using will have at
least 16GB of RAM, though basic suite still runs with 8GB.

### Permissions

The user account used to run OST should belong to the groups qemu and libvirt. setup_for_ost.sh does that for you.

## How to contribute

### Submitting patches

Patches are welcome!

Please submit patches to [GitHub:ovirt-system-tests](https://github.com/oVirt/ovirt-system-tests).
If you are not familiar with the review process for GitHub patches you can read about [Working with oVirt GitHub](https://ovirt.org/develop/dev-process/working-with-github.html)
on the [oVirt](https://ovirt.org/) website.

### Found a bug or documentation issue?

To submit a bug, suggest an enhancement or report a documentation issue for oVirt System Tests please
join [oVirt Development forum / mailing list](https://lists.ovirt.org/admin/lists/devel.ovirt.org/) and discuss there.

## Still need help?

If you have any other questions, please join [oVirt Development forum / mailing list](https://lists.ovirt.org/admin/lists/devel.ovirt.org/) and ask there.

## Running the tests

Make sure your machine is set up with `setup_for_ost.sh`
You can use `ost.sh` for running the complete suite on a concrete ost-images distro
E.g. `./ost.sh run basic-suite-master el8stream`

You can use `--custom-repo` for verifying an oVirt patch:

* On your GitHub account go to Settings/Developer settings/Personal access tokens/Generate new token, and give it the **repo** scopes.
* On your ost machine run `export GITHUB_TOKEN=personal_access_token`
* Run the tests, e.g `./ost.sh run basic-suite-master el8stream --custom-repo=https://github.com/oVirt/ovirt-engine/pull/pr_number`
You can pass this option multiple times to test more than 1 build at once.

The environment is left running after it finishes so that you can examine or further use the created environment.
It is necessary to clean the environment up aftery every run with `./ost.sh destroy`.
It is possible to prevent accidental destroying with `./ost.sh lock Some reason`. If done, `destroy` fails with a message.
The environment contains inventory, VMs, live VM logs and is normally stored
in `deployment` subdirectory of the repository. The location can be changed
through `OST_DEPLOYMENT` environment variable.

When the environment is up you can use `./ost.sh shell` to connect to the VMs.
`./ost.sh status` shows a little overview of how the OST environment is laid out on the host system.

## Advanced use

`ost.sh` internally uses bash functions from `lagofy.sh` that you can source into your (bash only, other shells are not supported) environment
and use for more granular control.
Functions starting with `ost_` and `OST_` variables can be used to bring up the VMs with custom images, boot OST environment without running tests,
or to run individual test cases.

You can also access the web ui easily, locate the engine's IP address in `./ost.sh status`. In case of Hosted Engine-based suites where
the engine VM is not declared in OST you can inspect the DNS entries of management network by `virsh net-dumpxml`.
Once you've located the engine VM's IP, add it to `/etc/hosts`. You have to use **the exact FQDN** (for basic suite you can also use just `engine`)
Now, log in to the web-UI at:

* URL: `https://engine/ovirt-engine/webadmin/`
* Username: `admin` or `admin@ovirt` if keycloak is enabled
* Password: `123456`
* Profile: `internal`

If you're running OST on a remote machine, you can tunnel a local
port directly to the destination machine - from your local machine:

```console
    $ sudo ssh -L 443:192.168.200.2:443 USER@HOST_RUNNING_OST
            ----  =================      ~~~~~~~~~~~~~~~~
            (*)   (**)                       (***)

    (*)   - The port on the local machine that the tunnel will be available at.
    (**)  - The machine IP, visible from the *host running OST* . This is were the traffic is tunneled to.
            Usually 192.168.200.2 is the address of ovirt-engine, but you can check that with ./ost.sh status
    (***) - The host running OST which can reach the VMs network and will tunnel the connection.
```

### Running specific tests

It's often useful to run just a single test, usually after running a suite, to test something using the existing machines.
Following is an example showing how to run the he-basic-suite, and after it's finished, run again one of the tests.

First, run the suite:

```console
./ost.sh run he-basic-suite-master el8stream
```

Now, you might change the code, e.g. to run a test with some change in it, or a new test you are developing. Then, run it:

```console
. lagofy.sh
ost_init he-basic-suite-master
ost_run_tc he-basic-suite-master/test-scenarios/test_030_ovirt_auth.py
```

The first argument to `ost_run_tc` is the test to run - a module, or a method/class inside one, e.g.:

```console
ost_run_tc basic-suite-master/test-scenarios/test_004_basic_sanity.py::test_vdsm_recovery
```

An optional second argument is passed as `-k` to pytest, for selecting tests based on pattern,
e.g. this will run `test_010_local_maintenance_cli.py` and `test_012_local_maintenance_sdk.py`:

```console
ost_run_tc he-basic-suite-master/test-scenarios local_maintenance
```

and this will run `test_add_hosts` and `test_verify_add_hosts`:

```console
ost_run_tc basic-suite-master/test-scenarios/test_002_bootstrap.py add_hosts
```

See the [pytest documentation](https://docs.pytest.org/en/stable/usage.html#specifying-tests-selecting-tests) for details.

Please note, that these are ran in a separate pytest session, and that several of our tests depend on previous ones to pass,
and/or on a specific state of the test VMs.

## Development

Make sure your machine is set up with `setup_for_ost.sh`
OST is designed to run concurrently under single non-root user, but in separate checkouts.
At runtime it creates "deployment" and "exported-artifacts" directories in the workspace.

Make sure that your new code doesn't depend on anything on the OST host,
whenever you need something it's usually a better idea to run that inside one of the VMs.

## Running tox tests

For developers of OST, a quick flake8 and pylint runs are available to identify any
syntax errors, typos, unused import etc.

To run the flake8/pylint, you'll need to have tox installed. To run pylint
without import errors you should also have ovirtdsk4 and ansible-runner installed.

Running linting tests:

```console
tox -e flake8,pylint,black,broken-symlinks
```

or `ost_linters` lagofy function.
