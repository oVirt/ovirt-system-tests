#!/usr/bin/env bash

#Set up gdepl on the first node (host0), to deploy HC setup on host0, 1, 2
# The reposync is not pickingup rpm from copr repo for some reason
#yum install -y gdeploy
yum install -y https://copr-be.cloud.fedoraproject.org/results/rnachimu/gdeploy/epel-7-x86_64/00521219-gdeploy/gdeploy-2.0.1-13.noarch.rpm
