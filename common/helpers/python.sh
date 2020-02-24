#!/bin/bash

if grep -qe '\(Red Hat\|CentOS\).*release 7' /etc/redhat-release; then
    PYTHON="python2"
else
    PYTHON="python3"
fi
