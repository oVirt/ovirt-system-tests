fstrim -va
yum install -y ovirt-hosted-engine-setup ovirt-engine-appliance
rm -rf /dev/shm/*.rpm
fstrim -va

echo -e "\nDefaults:root !requiretty\n" >> /etc/sudoers
echo -e "\nDefaults:%root !requiretty\n" >> /etc/sudoers
