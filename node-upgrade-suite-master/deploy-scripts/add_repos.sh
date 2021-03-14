cat >/etc/yum.repos.d/latest-node.repo <<EOL
[Latest-Ovirt-Node]
name=Latest ovirt node
baseurl=https://jenkins.ovirt.org/job/ovirt-node-ng-image_master_build-artifacts-el8-x86_64/lastSuccessfulBuild/artifact/exported-artifacts
gpgcheck=0
enabled=1
EOL
