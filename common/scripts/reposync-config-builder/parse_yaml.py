#!/bin/env python

# -*- coding: utf-8 -*-

from __future__ import print_function
import sys
import yaml


def main():
    yaml_file = sys.argv[1]
    template_name = get_templates(yaml_file)
    print(" ".join(str(x) for x in template_name))

def get_templates(yaml_file):
    with open(yaml_file, 'r') as stream:
        data_loaded = yaml.load(stream)
    template = data_loaded.get('templates',{})
    return template.values()

if __name__ == '__main__':
    main()
