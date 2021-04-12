# oVirt System Tests

Welcome to the oVirt System Tests source repository.

This repository is hosted on [gerrit.ovirt.org:ovirt-system-tests](https://gerrit.ovirt.org/#/admin/projects/ovirt-system-tests)
and a **backup** of it is hosted on [GitHub:ovirt-system-tests](https://github.com/oVirt/ovirt-system-tests)

Checkout the [oVirt Sytem Tests Introduction page](http://ovirt-system-tests.readthedocs.io/en/latest/) for more info about this project.


## How to contribute

### Submitting patches

Patches are welcome!

Please submit patches to [gerrit.ovirt.org:ovirt-system-tests](https://gerrit.ovirt.org/#/admin/projects/ovirt-system-tests).
If you are not familiar with the review process for Gerrit patches you can read about [Working with oVirt Gerrit](https://ovirt.org/develop/dev-process/working-with-gerrit.html)
on the [oVirt](https://ovirt.org/) website.

**NOTE**: We might not notice pull requests that you create on Github, because we only use Github for backups.


### Found a bug or documentation issue?
To submit a bug, suggest an enhancement or report a documentation issue for oVirt System Tests please
join [oVirt Development forum / mailing list](https://lists.ovirt.org/admin/lists/devel.ovirt.org/) and discuss there.


## Still need help?
If you have any other questions, please join [oVirt Development forum / mailing list](https://lists.ovirt.org/admin/lists/devel.ovirt.org/) and ask there.


# Development

## Running tox tests

For developers of OST, a quick flake8 and pylint runs are available to identify any
syntax errors, typos, unused import etc.

To run the flake8/pylint, you'll need to have tox installed. To run pylint
without import errors you should also have ovirtdsk4, lago and
ansible-runner installed.

Running flake8 and pylint tests:
```
tox -e flake8,pylint
```
