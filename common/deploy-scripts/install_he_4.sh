yum install -y haveged ovirt-hosted-engine-setup ovirt-engine-appliance sshpass
systemctl enable haveged
systemctl start haveged
echo -e "\nDefaults:root !requiretty\n" >> /etc/sudoers
echo -e "\nDefaults:%root !requiretty\n" >> /etc/sudoers
