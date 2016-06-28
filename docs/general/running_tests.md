Run oVirt system tests
======================
oVirt system tests has multiple 'testing suites', each targeted at a different version<br>
of oVirt or a different product, for e.g, the 'basic_suite_4.0' will run basic sanity<br>
tests for the 4.0 version, which includes: installing engine, adding hosts, adding storage, installing VMs, etc..

For simplicity we chose the 'basic suite 4.0' in this example, but you can choose any other suite<br>
and it should work just the same.

Start by cloning the git repo:
```
    $ git clone git://gerrit.ovirt.org/ovirt-system-tests
```

As the tests that we are going to run are for ovirt-engine 4.0, we have to add<br>
the oVirt 4.0 release repository to our system so it will pull in the sdk<br>
package, the following works for any centos/fedora distro:

```
    # yum install -y http://resources.ovirt.org/pub/yum-repo/ovirt-release40.rpm
```

Once you have the code and the repo, you can run the run_suite.sh script to<br>
run any of the suites available:

```
    $ cd ovirt-system-tests
    $ ./run_suite.sh basic_suite_4.0
```

**NOTE**: this will download a lot of vm images the first time it runs, check<br>
the section "`template-repo.json: Sources for templates`_" on how to use local<br>
mirrors if available.

Remember that you don't need root access to run it, if you have permission<br>
issues, make sure you followed the guidelines in the user permissions section before.<br>

This will take a while, as first time execution downloads a lot of stuff,<br>
like downloading OS templates, where each one takes at least 1G of data.<br>
If you are still worried that its stuck, please refer to the [FAQ](docs/general/faq.html)
to see if the issue you're seeing is documented.

Once it is done, you will get the results in the directory<br>
`deployment-basic_suite_4.0`, that will include an initialized prefix with a<br>
4.0 engine vm with all the hosts and storages added.

To access it, log in to the web-ui at:

* URL: `https://192.168.200.2/`
* Username: `admin@internal`
* Password: `123`

If you're running the framework on a remote machine, you can tunnel a local<br>
port directly to the destination machine::
```
    $ ssh -L 8443:192.168.200.2:443 remote-user@remote-ip
            ---- =================             ~~~~~~~~~
            (*)   (**)                         (***)

    (*)   - The port on localhost that the tunnel will be available at.
    (**)  - The destination where the remote machine will connect when local machine
            connects to the local end of the tunnel.
    (***) - Remote machine through which we'll connect to the remote end of the
            tunnel.
```
After creating the tunnel, web-ui will be available at `https://localhost:8443/`


Poke around in the env
------------------------

You can now open a shell to any of the vms, start/stop them all, etc.:
```
    $ cd deployment-basic_suite_4.0
    $ lagocli shell engine
    [root@engine ~]# exit

    $ lagocli stop
    2015-11-03 12:11:52,746 - root - INFO - Destroying VM engine
    2015-11-03 12:11:52,957 - root - INFO - Destroying VM storage-iscsi
    2015-11-03 12:11:53,167 - root - INFO - Destroying VM storage-nfs
    2015-11-03 12:11:53,376 - root - INFO - Destroying VM host3
    2015-11-03 12:11:53,585 - root - INFO - Destroying VM host2
    2015-11-03 12:11:53,793 - root - INFO - Destroying VM host1
    2015-11-03 12:11:54,002 - root - INFO - Destroying VM host0
    2015-11-03 12:11:54,210 - root - INFO - Destroying network lago

    $ lagocli start
    2015-11-03 12:11:46,377 - root - INFO - Creating network lago
    2015-11-03 12:11:46,712 - root - INFO - Starting VM engine
    2015-11-03 12:11:47,261 - root - INFO - Starting VM storage-iscsi
    2015-11-03 12:11:47,726 - root - INFO - Starting VM storage-nfs
    2015-11-03 12:11:48,115 - root - INFO - Starting VM host3
    2015-11-03 12:11:48,573 - root - INFO - Starting VM host2
    2015-11-03 12:11:48,937 - root - INFO - Starting VM host1
    2015-11-03 12:11:49,296 - root - INFO - Starting VM host0
```

Cleanup
---------

Once you're done with the environment, run:
```
    $ cd deployment-basic_suite_4.0
    $ lagocli cleanup
```
That will stop any running vms and remove the lago metadata in the prefix, it<br>
will not remove any other files (like disk images) or anything though, so you<br>
can play with them for further investigation if needed, but once executed, it's<br>
safe to fully remove the prefix dir if you want to.

Where to find more info
=======================

If you're interested in how things works internally and how you can use Lago cli to do more cool stuff,<br>
checkout the full [Lago documentation][1] and read about Lago 'verbs' and other goodies.

If you're have more questions about ovirt-system-tests, try checking out the faq[2] page<br>.
If you still can't find what you're looking for try the mailing list of ovirt (devel@ovirt.org) or lago (lago-devel@ovirt.org).

Enjoy!


[1]: http://lago.readthedocs.io/en/stable/
[2]: docs/general/faq.html
