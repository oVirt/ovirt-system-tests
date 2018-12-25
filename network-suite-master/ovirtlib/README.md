ovirt-sdk wrapper ovirtlib
=====================

This package is a general-purpose library wrapping the ovirt sdk. It is
intentded to provide an easier interface for test developers. We hope that in
the future it becomes useful for anybody that wants to write a script or an
application on top of ovirt sdk.

Below is a simple example reporting the status of the Default data
center.

    >>> URL = 'https://engine/ovirt-engine/api'
    >>> PASSWORD = '123'
    >>> USERNAME = 'admin@internal'
    >>>
    >>> from ovirtlib.system import SDKSystemRoot
    >>> from ovirtlib.datacenterlib import DataCenter
    >>>
    >>> system = SDKSystemRoot()
    >>> system.connect(
    ...     url=URL, insecure=True, password=PASSWORD, username=USERNAME)
    >>>
    >>> default_dc = DataCenter(system)
    >>> default_dc.import_by_name('Default')
    >>> print(default_dc.status)
    <DataCenterStatus.UP: 'up'>

Further examples can be found under `fixtures` and `tests` directories.
