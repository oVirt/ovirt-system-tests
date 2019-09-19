set -xe

create_env_variable_from_yaml() {
    export host_type=$1
    python="$(command -v python)" || res=$?
    [[ "$res" -ne 0 ]] && {
        python="/usr/libexec/platform-python"
        INSTALL_PY3=true
    }

eval "$($python <<END
import os
import yaml

vars_dict = yaml.load(open('/tmp/vars_main.yml'));
rhv_ver = str(vars_dict['ovirt_version'][os.environ.get('host_type')])
print('RHV_VER={0}'.format(rhv_ver))
os_ver = str(vars_dict['os_version'][os.environ.get('host_type')])
print('OS_VER={0}'.format(os_ver))

END
)"

}

DIST=$(uname -r | sed -r  's/^.*\.([^\.]+)\.[^\.]+$/\1/')
ADDR=$(ip -4 addr show scope global up |grep -m1 inet | awk '{split($4,a,"."); print a[1] "." a[2] "." a[3] ".1"}')


cat > /etc/yum.repos.d/local-ovirt.repo <<EOF
[alocalsync]
name=Reposync & Extra Sources Content
baseurl=http://$ADDR:8585/default/$DIST/
enabled=1
gpgcheck=0
repo_gpgcheck=0
cost=1
keepcache=1
ip_resolve=4
max_connections=10
deltarpm=0
EOF

sed -i "s/var\/cache/dev\/shm/g" /etc/yum.conf
echo "persistdir=/dev/shm" >> /etc/yum.conf

# disable any other repos to avoid downloading metadata
cd  /etc/yum.repos.d/
yum install --disablerepo=\* --enablerepo="$(cat local-ovirt.repo reposync-config*.repo | grep '\['| tr -d '[]'| grep -v main| xargs | tr ' ' ',')" -y yum-utils
yum-config-manager --disable \*
yum-config-manager --enable "$(cat local-ovirt.repo reposync-config*.repo | grep '\['| tr -d '[]'| grep -v main| xargs | tr ' ' ',')"

yum repolist -v > /var/log/rst_yum_repos.log
