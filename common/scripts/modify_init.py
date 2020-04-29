from __future__ import print_function
import yaml
import os
import sys


def main():
    if len(sys.argv) < 2:
        print('Missing init file path')
        sys.exit(1)

    init_file_path = sys.argv[1]

    if not os.path.exists(init_file_path):
        print('{} does not exist'.format(init_file_path))
        sys.exit(1)

    with open(init_file_path, 'rt') as fd:
        init_file = yaml.safe_load(fd)

    build_list = [
        {
            'virt-customize': {
                'ssh-inject': '',
                'no-network': None
            }
        }
    ]

    domains = init_file['domains']
    for _, domain in domains.viewitems():
        for disk in domain['disks']:
            if disk['type'] == 'template':
                disk['build'] = build_list
            domain['bootstrap'] = False

    with open(init_file_path, 'wt') as fd:
        fd.write(yaml.safe_dump(init_file))

if __name__ == '__main__':
    main()
