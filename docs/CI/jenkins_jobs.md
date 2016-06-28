oVirt CI Jobs running ovirt-system-tests
========================================
One of the main benefits of OST is using it in a CI environment, where you can catch regressions before a release<br>
is done.

Currently the oVirt [Jenkins server](http://jenkins.ovirt.org) has a few jobs which run ovirt-system-tests on various flows per version.<br>
The jobs are devided into 2 main types:

ovirt-system-tests jobs
-----------------------
**Trigger/Frequency**: Running every few hours on latest night, example for master [oVirt master nightly repos][1]<br>
**Link**: [ovirt-system-tests-jenkins-view][2]<br>

These jobs are using oVirt packages which are built per commit and published nightly via the [publishers jobs][3]<br>
They are also used in the standard CI for OST, so when you send a new patch for ovirt-system-tests, the same tests<br>
will run on your new code and fail if there is a regression.


ovirt experimental jobs
------------------------
**Link**: [ovirt experimental jobs][4]<br>
**Trigger**: Running every time a new commit is merged on ANY oVirt project. (Usually will run on a few commits due to resource limitation).<br>

These jobs are triggered by each 'build-artifacts' job in CI which created RPMs for a specific oVirt project.<br>
These rpms are being deployed to a temp repo by the 'deploy-ovirt-experimental' job and merged into latest nightly repo using repoman.<br>
Once the repo is ready with the new RPMs, the 'test experimental' job is triggered using the given repo.<br>
If the tests pass then a new repo is being publised under latest tested repo,

for e.g for oVirt master [latest master tested][5]

[1]: http://resources.ovirt.org/pub/ovirt-master-snapshot/rpm/
[2]: http://jenkins.ovirt.org/view/oVirt%20system%20tests/
[3]: http://jenkins.ovirt.org/view/Publishers/
[4]: http://jenkins.ovirt.org/view/experimental%20jobs/
[5]: http://resources.ovirt.org/repos/ovirt/experimental/master/latest.tested/
