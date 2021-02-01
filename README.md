Overview of ovirt-system-tests
------------------------------
Checkout the [oVirt Sytem Tests Introduction page][1] for more info.


Running tox tests
---------------------
For developers of OST, a quick flake8 and pylint runs are available to identify any
syntax errors, typos, unused import etc.

To run the flake8/pylint, you'll need to have tox installed. To run pylint
without import errors you should also have ovirtdsk4, netaddr, lago and
ansible-runner installed.

Running flake8 and pylint tests:
```
tox -e flake8,pylint
```

[1]: http://ovirt-system-tests.readthedocs.io/en/latest/
