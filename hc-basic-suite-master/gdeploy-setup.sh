#!/usr/bin/env bash

#Set up gdepl on the first node (host0), to deploy HC setup on host0, 1, 2
# The reposync is not pickingup rpm from copr repo for some reason
yum install -y gdeploy
