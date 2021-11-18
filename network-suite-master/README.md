# oVirt System Tests - network suite

## Running the suite against an independent deployment

Developers of both engine\vdsm and OST need the following capabilities:

* test their code changes on engine\vdsm against the network suite during
  development with zero setup time and zero wait-for-results time.
* debug the suite code in a visual debugger and use break points to stop
  the execution at any desired point.

To accomplish these goals it is required to run the network-suite against an
environment independent of the deployment that is executed using LagoInitFile
and the suite's scripts. For example, a pre-existing ovirt-engine development
environment.

The prerequisites for running the suite against an independent deployment are
a running ovirt-engine with two hosts added to it, all accessible via ipv4.
If you have a such a pre-existing deployment you will need to manually supply
some details about it to the suite to make your deployment reachable and usable
by the suite.
At the time of writing of this README the following are required:

#### A. Supply connectivity facts for your machines
`network-suite-master/fixtures/ansible.py`

For example:
```
def engine_facts():
    return MachineFacts('127.0.0.1', 'localhost', 'my_ssh_pass')

@pytest.fixture(scope="session")
def host0_facts():
    return MachineFacts('192.168.122.10', 'my_hostname', 'my_ssh_pass')

@pytest.fixture(scope="session")
def host1_facts():
    return MachineFacts('192.168.122.11', 'my_hostname', 'my_ssh_pass')
```
where `my_hostname` is what the host was named in ovirt-engine when it was
added to ovirt-engine.

#### B. Supply ovirt-engine access password
`network-suite-master/fixtures/engine.py`
```
@pytest.fixture(scope="session")
def engine_password():
    return "my_ovirt_engine_password"
```

#### C. Bypass `ovirt_engine_setup` fixture
`network-suite-master/fixtures/engine.py`

The setup is not needed when machine containing a running ovirt-engine exists.
* Remove the `autouse=True` notation from the fixture.
* Remove the fixture from:
  * parameter list of the fixture `ovirt_engine_service_up`
  * import list in `network-suite-master/test-scenarios/conftest.py`

#### D. Modify ovirt-engine API url
`network-suite-master/fixtures/engine.py`

The default url in `_create_engine_connection` assumes https with its default
port. This might need to be modified to http and the configured port.

#### E. Comment out most `ost_utils` fixtures
`ost_utils` fixtures assume the existence of the standard LagoInitFile
deployment. Therefore they fail when run against an independent deployment.
They can be bypassed by commenting out their imports in the file
`network-suite-master/test-scenarios/conftest.py`

Only below imports should remain uncommented:
```
from ost_utils.pytest.fixtures.virt import artifacts_dir
from ost_utils.pytest.fixtures.virt import cirros_image_template_name
```

#### F. Supply suite name environment variable
`network-suite-master/testlib/suite.py`

For example, to run the 'master' suite:
```
os.environ['SUITE'] = 'network-suite-master'
```

#### G. Create an exported-artifacts folder for pytest.log
`ovirt-system-tests/pytest.ini`

Create a folder named `exported-artifacts` and modify the path in `pytest.ini`
to point at it. For example:
```
log_file = /tmp/exported-artifacts/pytest.log
```