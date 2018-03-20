oVirt CI Jobs running ovirt-system-tests
========================================
One of the main benefits of OST is using it in a CI environment, where you can catch regressions before a release<br>
is done.

Currently the oVirt [Jenkins server](http://jenkins.ovirt.org) has a few jobs which run ovirt-system-tests on various flows per version.<br>

ovirt-system-tests jobs
-----------------------
**Trigger/Frequency**: Running nightly on latest oVirt snapshot RPMs, example for master [oVirt master nightly repos][1]<br>
**Link**: [ovirt-system-tests-jenkins-view][2]<br>

These jobs are using oVirt packages which are built per commit and published nightly via the [publishers jobs][3]<br>
Note: since the experimental jobs are running on newer packages, these jobs might be obsolete soon since they
are running on non-verified published RPMs.

ovirt-system-tests check-patch
-------------------------------
**Trigger/Frequency**: Running on each OST patch, using latest.tested oVirt experimental RPMs(see next section for info)<br>
**Link**: [ovirt-system-tests-check-patch][4]<br>

The 'check-patch' OST job is using the 'standard CI' to run the OST suites on each new OST patch.<br>
Usually the job will run on the updated suite which is modified in the patch itself, but if any of the 'common' files<br>
will be changed, all 'basic' suites will run as well to make sure a regression wasn't added to a common file.

[1]: http://resources.ovirt.org/pub/ovirt-master-snapshot/rpm/
[2]: http://jenkins.ovirt.org/view/oVirt%20system%20tests/
[3]: http://jenkins.ovirt.org/view/Publishers/
[4]: http://jenkins.ovirt.org/view/oVirt%20system%20tests/job/ovirt-system-tests_master_check-patch-el7-x86_64/
