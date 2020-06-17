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

## update /etc/dnf/dnf.conf for centos8
dnf_conf_file="/etc/dnf/dnf.conf"
dnf_yum_bck_file="/tmp/dnf_yum.conf"
if [[ -e  "$dnf_conf_file" ]]; then
    sed -i -e 's/gpgcheck=1/gpgcheck=0/g' "$dnf_conf_file"
    sed -i -e '/^gpgcheck=.*/a enabled=1' "$dnf_conf_file"
    cp "$dnf_conf_file" "$dnf_yum_bck_file"
else
    cp "/etc/yum.conf" "$dnf_yum_bck_file"
fi

DIST=$(uname -r | sed -r  's/^.*\.([^\.]+)\.[^\.]+$/\1/')
ADDR=$(ip -4 addr show scope global up |grep -m1 inet | awk '{split($4,a,"."); print a[1] "." a[2] "." a[3] ".1"}')
curl_res=0
curl -f http://$ADDR:8585/default/${DIST%_*}/repodata/repomd.xml  || curl_res=$?

if [[ "$curl_res" -eq 0 ]]; then
    cat > /etc/yum.repos.d/local-ovirt.repo <<EOF
[alocalsync]
name=Reposync & Extra Sources Content
baseurl=http://$ADDR:8585/default/${DIST%_*}/
enabled=1
gpgcheck=0
repo_gpgcheck=0
cost=1
keepcache=1
ip_resolve=4
max_connections=10
deltarpm=0
priority=1
EOF

fi


# disable any other repos to avoid downloading metadata
cd  /etc/yum.repos.d/
yum install --disablerepo=\* --enablerepo="$(cat reposync-config*.repo | grep '\['| tr -d '[]'| grep -v main | xargs | tr ' ' ',')" -y yum-utils
yum-config-manager --disable \*

for i in $(cat reposync-config*.repo | grep '\['| tr -d '[]'| grep -v main); do
    yum-config-manager --enable "$i"
done

INSTALL_PKG=("tar")

python="$(command -v python)" || res=$?
[[ "$res" -ne 0 ]] && {
    INSTALL_PKG+=("python3")
    INSTALL_PKG+=("wget")
}
yum install --nogpgcheck -y "${INSTALL_PKG[@]}"

[[ "$curl_res" -eq 0 ]] && {
    yum-config-manager --enable alocalsync
}

yum repolist -v > /var/log/rst_yum_repos.log

## collect general info on the lago vm
yum install --nogpgcheck -y libvirt sos
systemctl start libvirtd
lscpu >  /var/log/lscpu.log || res=$?
cat /proc/cpuinfo > /var/log/cpuinfo.log || res=$?
sosreport --batch --tmp-dir=/tmp --name=sosreport_for_vm.log || res=$?
reqsubstr="host"
if [[ -z "${hostname##*$reqsubstr*}" ]] ;then
    virsh capabilities > /var/log/virsh_capabilities.log || res=$?
fi

yum upgrade --nogpgcheck -y
