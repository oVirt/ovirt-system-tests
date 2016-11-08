fstrim -va
yum install -y ovirt-hosted-engine-setup sshpass
rm -rf /dev/shm/*.rpm
fstrim -va
echo -e "\nDefaults:root !requiretty\n" >> /etc/sudoers
echo -e "\nDefaults:%root !requiretty\n" >> /etc/sudoers
