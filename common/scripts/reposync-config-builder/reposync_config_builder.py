"""
"reposync_config_builder" is a Yum plugin which generates Yum config for
 reposync. If package X is going to be installed from repo Y,
 the plugin will add "includepkgs=X" in the section of repo Y/
 This operation is recursive (deps of package X will be also included).

 If no package is going to be installed from repo Y, the plugin will add
 "exclude=*" in the config of repo Y.

Setup:

1. Copy this file to to Yum's plugin folder
    (the default is /usr/share/yum-plugins).

2. Create a file named "reposync_config_builder.conf", and place it
   in the Yum plugin's conf directory (the default is /etc/yum/pluginconf.d)

3. Add the following lines to "reposync_config_builder.conf":

[main]
enabled=1
# If skip install is True, don't install any package, just generate the config.
skip_install=True

Usage:

Run yum install with the list of packages you wish to include in the config.
The plugin will generate a new config named "YOUR_CONF_NAME.modified".
The modified conf will be created in the directory of your original conf,
and will include the packages you tried to install and their deps.



"""

from yum.plugins import PluginYumExit, TYPE_INTERACTIVE
import ConfigParser
from collections import defaultdict
import re

requires_api_version = '2.7'
plugin_type = (TYPE_INTERACTIVE,)
cache = {}


def postconfig_hook(conduit):
    """
    Add the config's path to the cache

    :param conduit: :class:`yum.plugins.PostConfigPluginConduit`
    """
    conf = conduit.getConf()
    cache['config_file_path'] = getattr(conf, 'config_file_path')


def predownload_hook(conduit):
    """
    Get a list of pkgs that should be downloaded by yum,
    and update the includepkgs / exclude field in the config.

    :param conduit: :class:`yum.plugins.DownloadPluginConduit`
    :raises: :class:`yum.plugins.PluginYumExit
        if an error occurred when trying to build the pkgs list,
        or if "skip_install" config option == True
    """
    repoid_to_pkgs = defaultdict(set)
    pkgs_to_dl = conduit.getDownloadPackages()

    errors = conduit.getErrors()
    if errors:
        conduit.info(2, errors)
        raise PluginYumExit(
            'Error were detected in predownload_hook, aborting'
        )

    for pkg in pkgs_to_dl:
        repoid_to_pkgs[pkg.repoid].add(pkg.name)

    set_include(cache['config_file_path'], repoid_to_pkgs)

    if conduit.confBool('main', 'skip_install', default=False):
        raise PluginYumExit('reposync_config_builder: Skipping install')


def set_include(conf_path, repoid_to_pkgs):
    """
    Update the includepkgs / exclude fields of the yum
    conf located at "conf_path"

    An "exclude=*" field will be added to repos that doesn't contain
    any required pkg.

    :param conf_path: Path to yum's conf
    :param repoid_to_pkgs: dict of str -> set. A mapping of pkgs
        to download from each repo
    """
    cp = ConfigParser.SafeConfigParser()
    with open(conf_path, mode='rt') as f:
        cp.readfp(f)

    # repos that doesn't have pkgs that we need
    repos_to_exclude = (
        repo
        for repo in cp.sections()
        if repo not in repoid_to_pkgs.keys() and
        repo != 'main'
    )

    # add include
    for repoid, pkgs in repoid_to_pkgs.iteritems():
        if cp.has_option(repoid, 'includepkgs'):
            predefined_includes = set(
                re.split(r'\s+', cp.get(repoid, 'includepkgs'))
            )
        else:
            predefined_includes = set()

        cp.set(
            repoid,
            'includepkgs',
            '\n'.join(sorted(predefined_includes | set(pkgs)))
        )

    # add exclude
    for repoid in repos_to_exclude:
        cp.set(repoid, 'exclude', '*')

    with open(conf_path + '.modified', mode='wt') as f:
        cp.write(f)




