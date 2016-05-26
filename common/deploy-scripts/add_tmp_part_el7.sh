#!/bin/bash

mkfs.xfs -K -r extsize=1m /dev/vdb
mount /dev/vdb /var/tmp
echo -e '/dev/vdb\t/var/tmp\t\t\txfs\tdefaults\t0 0' >> /etc/fstab
