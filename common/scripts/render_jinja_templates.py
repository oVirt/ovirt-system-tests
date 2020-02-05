from __future__ import print_function

import os
import sys
import yaml
from jinja2 import Environment, FileSystemLoader


def render(template):
    """

    :param template: Path to jinja2 template, yaml format
    :return: string representation of the rendered jinja template
    """

    envDir = os.path.dirname(template)
    envDir = os.getcwd() if envDir == '' else envDir
    env = Environment(loader=FileSystemLoader(envDir))
    template = env.get_template(os.path.basename(template))

    # Load vars
    with open(os.path.join(envDir, 'vars', 'main.yml')) as _:
        context = yaml.load(_)

    # Make the shell environment accessible as variable 'env'
    context['env'] = os.environ
    return template.render(**context)


if __name__ == '__main__':
    if len(sys.argv) < 2:

        print("Usage: %s [path to jinja2 template]" % sys.argv[0])
        sys.exit(1)
    print(render(sys.argv[1]))
