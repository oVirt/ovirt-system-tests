#!/bin/bash -xe
set -ex

yum -y install ovirt-host
rm -rf /dev/shm/*.rpm /dev/shm/yum
