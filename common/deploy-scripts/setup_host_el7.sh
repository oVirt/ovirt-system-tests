#!/bin/bash -xe

systemctl disable --now postfix
yum update -y iptables
