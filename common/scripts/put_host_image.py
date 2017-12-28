import sys
from os import path, symlink, environ
from textwrap import dedent

from lago import sdk
from lago.utils import get_qemu_info

def usage():
    print(
        dedent(
            """
            Usage: put_host_image PREFIX_PATH DEST

            Create a symlink to the host's base image in DEST.

            PREFIX_PATH is a path to a lago prefix.
            """
        )
    )

def _itr_hosts(prefix):
    return (
        h for h in prefix.get_vms().itervalues()
        if h.vm_type == 'ovirt-host'
    )

def _get_host(prefix):
    try:
        return next(_itr_hosts(prefix))
    except StopIteration:
        raise RuntimeError('No hosts found')

def add_host_image_to_dest(prefix_path, dest):
    '''
    Creates a symlink to the host's base image in dest.

    Args:
        prefix_path (str): Path to the prefix
        dest (str): Where to create the symlink
    '''
    prefix = sdk.load_env(prefix_path)
    environ['LAGO_PREFIX_PATH'] = path.join(prefix_path, 'current')

    disk_path = _get_host(prefix).disks[0]['path']
    backing_file_path = get_qemu_info(disk_path).get('backing-filename')

    if not backing_file_path:
        raise RuntimeError(
            'Failed to add image {} to {}'.format(disk_path, dest)
        )

    if path.isdir(dest):
        dest = path.join(dest, path.basename(backing_file_path))

    symlink(backing_file_path, dest)


def main():
    if len(sys.argv) != 3:
        usage()
        sys.exit(1)

    add_host_image_to_dest(prefix_path=sys.argv[1], dest=sys.argv[2])

if __name__ == '__main__':
    main()
