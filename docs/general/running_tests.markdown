Run oVirt system tests
======================
oVirt system tests has multiple 'testing suites', each targeted at a different version<br>
of oVirt or a different product, for e.g, the 'basic-suite-4.0' will run basic sanity<br>
tests for the 4.0 version, which includes: installing engine, adding hosts, adding storage, installing VMs, etc..

For simplicity we chose the 'basic suite 4.0' in this example, but you can choose any other suite<br>
and it should work just the same.

Start by cloning the git repo:
```
    $ git clone git://gerrit.ovirt.org/ovirt-system-tests
```

Once you have the code and the repo, go to the project:

```
    $ cd ovirt-system-tests
```

For the first time, need to run setup_for_ost.sh in order for properly setting up a bare system to run OST:

```
    $ ./setup_for_ost.sh
```

Then you can run the run_suite.sh script to run any of the suites available:

```
    $ ./run_suite.sh basic-suite-4.0
```

Remember that you don't need root access to run it, if you have permission<br>
issues, make sure you followed the guidelines in the user permissions section before.<br>

This will take a while, as first time execution downloads a lot of stuff,<br>
like downloading OS templates, where each one takes at least 1G of data.<br>
If you are still worried that its stuck, please refer to the [FAQ]
to see if the issue you're seeing is documented.

Once it is done, you will get an initialized prefix with a 4.0 engine VM,<br>
with added hosts and storages.<br>
You can find the results in `deployment-basic-suite-4.0` directory.<br>

In order to log in the web-UI, first you should find the engine VM's IP address:<br>
* From the `deployment-basic-suite-4.0` directory, run `lago status`.<br>
* Under `[VMs]` find `[lago-basic-suite-4-0-engine]`. The IP address of <br>
`network: lago-basic-suite-4-0-net-management` is the relevant one.<br>

Once you've located the engine VM's IP, add it to `/etc/hosts` followed by the name `engine`.<br>
**NOTE**: any other name than `engine` will **not** work.

Now, log in to the web-UI at:

* URL: `https://engine/ovirt-engine/webadmin/`
* Username: `admin`
* Password: `123`
* Profile: `internal`

If you're running the framework on a remote machine, you can tunnel a local<br>
port directly to the destination machine - from your local machine:
```
    $ ssh -L 8443:192.168.200.2:443 USER@HOST_RUNNING_OST
            ----  =================      ~~~~~~~~~~~~~~~~
            (*)   (**)                       (***)

    (*)   - The port on the local machine that the tunnel will be available at.
    (**)  - The machine IP, visible from the HOST_RUNNING_OST. This is were the traffic is tunneled to.
            Usually 192.168.200.2 is the address of ovirt-engine
    (***) - The host running OST which can reach the VMs network and will tunnel the connection.
```
After creating the tunnel, web-UI will be available at `https://localhost:8443/`

**NOTE**: In some cases, like performance-suite, the engine machine will have a different IP. To find it run:
```
    # from the deployment folder, say basic-suite-master
    $ lago --out-format flat status | grep VMs/.*engine.*/NICs/eth0/ip

```

Poke around in the env
------------------------

You can now open a shell to any of the VMs, start/stop them all, etc.:
```
    $ cd deployment-basic-suite-4.0
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
    $ cd deployment-basic-suite-4.0
    $ lagocli cleanup
```
That will stop any running VMs and remove the lago metadata in the prefix, it<br>
will not remove any other files (like disk images) or anything though, so you<br>
can play with them for further investigation if needed, but once executed, it's<br>
safe to fully remove the prefix dir if you want to.

Where to find more info
=======================

If you're interested in how things works internally and how you can use Lago cli to do more cool stuff,<br>
checkout the full [Lago documentation][1] and read about Lago 'verbs' and other goodies.

If you're have more questions about ovirt-system-tests, try checking out the [FAQ] page<br>.
If you still can't find what you're looking for, try the mailing list of oVirt (devel@ovirt.org) or lago (lago-devel@ovirt.org).

Enjoy!


[1]: http://lago.readthedocs.io/en/stable/
[FAQ]: faq.markdown
