#!/bin/bash -xe

systemctl disable --now postfix
# for bz 1416386
systemctl stop lvm2-lvmetad
# prevent lvm2-lvmetad.socket to run this service
systemctl mask lvm2-lvmetad
