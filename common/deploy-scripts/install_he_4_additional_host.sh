fstrim -va
yum install -y ovirt-hosted-engine-setup sshpass
fstrim -va
echo -e "\nDefaults:root !requiretty\n" >> /etc/sudoers
echo -e "\nDefaults:%root !requiretty\n" >> /etc/sudoers
