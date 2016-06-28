oVirt System Tests Framework Introduction
=========================================

oVirt system tests is a testing framework written in python and uses<br>
the python SDK oVirt has in order to run end-to-end system tests on any bare metal server with the minimum requirements<br>

The framework includes various 'test suites' while each one is targeted on different packages of oVirt.<br>
Currently available suites includes:<br>
* Basic sanity (install engine, add hosts, install VM, storage, migration,etc...)
* Hosted Engine (install hosted engine and performs various actions on it)
* Next Generation Node (install engine on NGN as hypervisor and run similar tests to basic suite)

The framework runs on a single bare metal host, running virtual<br>
machines created by a project called [Lago][1].

The framework serves various purposes and scenarios, to name a few: <br>
* Allows any developer or even a user to run system-level test on his laptop, w/o<br>
  needing a complex CI system.
* Allows running system (end-to-end) tests in CI in order to catch regressions before oVirt is released.<br>
* Allows easy POC or demos for customers or users to try out oVirt or any other product.<br>

[1]: http://lago.readthedocs.io/en/stable/
