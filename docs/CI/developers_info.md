Verifying an oVirt patch with ovirt-system-tests
================================================

On your laptop
--------------
Please follow the guidelines to run & install Lago & OST before trying this step.<br>

Once you have everything set and you managed to run locally a basic ost suite without issues, <br>
The only change you need to do is add '-s' to your command line, and provide a URL with the custom <br>
RPMs you built for your patches ( see [build-on-demand][1] on how to build RPMs from an open patch. ) <br>

Example of running a suite locally with a custom repo: (from the OST root dir)
```
./run_suite.sh -s http://jenkins.ovirt.org/job/vdsm_master_build-artifacts-on-demand-el7-x86_64/1/ basic_suite_master
```

On Jenkins
----------
On some occassions running OST on your laptop might not be possible due to various reasons (time/resources/etc..)<br>
So another easy option is to run a manual OST job on CI on your desired open patch(es).

To run an OST job on any open oVirt patch follow the following guidelines:

* *Build RPMs from your open patch(es)*

    Building RPMs today from any open oVirt patch is simple as just
    asking for it.. :)<br>
    The new 'build-on-demand' option from oVirt [Standard CI][1] allows
    you to just type **ci please build** in a comment on your patch
    and a new build will be triggered on the project 'build-on-demand' jobs.<br>
    Once the 'build-on-demand' job finished building, write down the job URL,
    for e.g: [vdsm-master-build-on-demand][2].
    (btw, you can do this for as many oVirt projects you want and have a list of URLs).


* *Run the manual OST job with your custom RPMs*

    Now that you have your custom RPMs ready, you're a click away from running OST
    on them.<br>
    * Login to [Jenkins][3] (make sure you have 'dev role' permissions, if not open a ticket to infra)<br>
    * Go to the [OST Manual job][4] for your relevant version ( usually master ).<br>
    * Click on 'build with parameters' menu ( on the left side )
    * Now add all the URLs you have with the custom RPMs ( one per line ),for e.g [vdsm-build][2]
    * Choose a fallback_repo:<br>
        A base repo that will be used 'under' your tested patch.<br>
        <u>latest:</u> includes all the rpm's that passed CI.<br>
        <u>latest_release:</u> includes all the rpm's in the latest release.<br>
    * Choose the suite type you want:<br>
        <u>basic:</u> Run engine-setup, and basic tests (bootstrap, sanity and etc)<br>
        <u>upgrade:</u> Initialize the engine with a base version, test if an upgrade to the target<br>
        version is possible.<br>
        Here we have 3 options:<br>
        upgrade-from-rc: The base version installed (before the upgrade) is the current release candidate<br>
        upgrade-from-release: Depends on the target version, the current official release will be set as the<br>
        base installed version from which we will upgrade.<br>
        e.g, if you choose upgrade from release for oVirt-4.1, the suite will install the official release of <b>4.1</b><br>
        and upgrade to the latest repo with your patch on top of it.<br>
        upgrade-from-prevrelease: Depends on the target version, the previous official release will be set as the<br>
        base installed version from which we will upgrade.<br>
        e.g, if you choose upgrade from release for oVirt-4.1, the suite will install the official release of <b>4.0</b><br>
        and upgrade to the latest repo with your patch on top of it.<br>
    * Choose the engine_version: This is the version that we actually test.<br>
      (in the upgrade suites, this is the version that we will be upgrading to)<br>
    * Choose the lago_version (unless you are testing lago, you'll probably want the stalbe release)<br>
    * Click 'Build'<br>
    * Go have coffee, don't worry the job will send you an email once its done ( on any status )<br>


If you're having issues or have any questions, please contact the infra team at infra@ovirt.org.

[1]: http://infra-docs.readthedocs.io/en/latest/CI/Build_and_test_standards.html#standard-ci-stages
[2]: http://jenkins.ovirt.org/job/vdsm_master_build-artifacts-on-demand-el7-x86_64/lastSuccessfulBuild/
[3]: http://jenkins.ovirt.org
[4]: http://jenkins.ovirt.org/job/ovirt-system-tests_manual/