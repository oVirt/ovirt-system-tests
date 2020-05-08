%{!?distro: %global distro el8}

# TODO: Can be overriden from cmdline
%{!?version: %global version 1}
%{!?release: %global release %(date -u +%%+4Y.%%m.%%d.%%H.%%M.%%S)}

# Whether base image is built or not
%{!?with_base: %global with_base 0}

# Disable debuginfo package, since this is a meta-package
%global debug_package %{nil}

Name: ost-images
Version: %{version}
Release: 0
Summary: VM images needed to run OST
License: GPLv2+
Source0: %{name}-%{version}.tar.gz
Prefix: %{_datarootdir}

BuildRequires: autoconf
BuildRequires: automake
BuildRequires: libguestfs-tools-c
BuildRequires: libvirt-client
BuildRequires: libvirt-daemon-config-network
BuildRequires: make
BuildRequires: qemu-img
BuildRequires: virt-install

%description
VM images needed to run OST

%prep
%setup

%build
%configure

%install
%make_install


%if %{with_base}

%package %{distro}-base
Summary: Bare distro installation image

%description %{distro}-base
Bare distro installation image

%files %{distro}-base
%{_datarootdir}/%{name}/*.ks
%attr(444, -, -) %{_datarootdir}/%{name}/*-base.qcow2
%attr(755, -, -) %{_datarootdir}/%{name}/rebase_images.sh
%exclude %{_datarootdir}/%{name}/*.ks.in

%endif # %{with_base}


%package %{distro}-upgrade
Summary: Bare distro with packages up to date
Requires: %{name}-%{distro}-base = %{version}

%description %{distro}-upgrade
Bare distro with packages up to date

%files %{distro}-upgrade
%attr(444, -, -) %{_datarootdir}/%{name}/*-upgrade.qcow2


%package %{distro}-engine-installed
Summary: Distro with ovirt-engine installed
Requires: %{name}-%{distro}-upgrade = %{version}-%{release}

%description %{distro}-engine-installed
Distro with ovirt-engine installed

%files %{distro}-engine-installed
%attr(444, -, -) %{_datarootdir}/%{name}/*-engine-installed.qcow2
%{_datarootdir}/%{name}/*-provision-engine.sh


%package %{distro}-host-installed
Summary: Distro with ovirt-host installed
Requires: %{name}-%{distro}-upgrade = %{version}-%{release}

%description %{distro}-host-installed
Distro with ovirt-host installed

%files %{distro}-host-installed
%attr(444, -, -) %{_datarootdir}/%{name}/*-host-installed.qcow2
%{_datarootdir}/%{name}/*-provision-host.sh
