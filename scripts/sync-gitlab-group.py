#! env python
import argparse
import ConfigParser
import os
import urllib
import subprocess
import requests

GITLAB_INI_FILE = '~/.gitlab.ini'
DEFAULT_CLONE_ROOT_DIR = '~/projects'

def subprocess_cmd(command):
    out = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
    if out.strip():
        print out.strip()

def get_group(args):
    url = '%s/api/v4/groups/%s' % (args['url'], urllib.quote_plus(args['group']))
    ret = requests.get(
        url=url,
        headers={
            'PRIVATE-TOKEN': args['api_token'],
            'Content-Type': 'application/json'
        }
    )
    ret.raise_for_status()
    return ret.json()

def process_arg(profile, config_parser, cli_args, argname):
    arg = getattr(cli_args, argname)
    if not arg:
        envvar = 'GITLAB_%s' % argname.upper()
        arg = os.environ.get(envvar)
    if not arg:
        arg = config_parser.get(profile, argname)
    return arg


def process_args(profile, config_parser, cli_args):
    """ Returns all relevant params as dict
    """
    ret = dict(
        api_token=process_arg(profile, config_parser, cli_args, 'api_token'),
        url=process_arg(profile, config_parser, cli_args, 'url'),
        root_dir=process_arg(profile, config_parser, cli_args, 'root_dir'),
        root_group=process_arg(profile, config_parser, cli_args, 'root_group'),
    )
    if not ret.get('api_token'):
        raise ValueError('api_token is required')
    if not ret.get('url'):
        raise ValueError('url is required')
    if not ret.get('root_dir'):
        raise ValueError('root_dir is required')

    group = cli_args.group[0]
    if '/' not in group and ret['root_group']:
        group = '%s/%s' % (ret['root_group'], group)
    ret['group'] = group
    return ret


def main():
    parser = argparse.ArgumentParser(description='Clones gitlab subgroup repos')
    parser.add_argument(
        '--profile',
        help='The gitlab profile to use within ~/.gitlab.ini',
        type=str,
        default='default',
    )
    parser.add_argument(
        '--url',
        help='The gitlab url',
        type=str,
    )
    parser.add_argument(
        '--root-group',
        help='The gitlab root group path',
        type=str,
    )
    parser.add_argument(
        '--api-token',
        help='The gitlab api token to be used',
        type=str,
    )
    parser.add_argument(
        '--root-dir',
        help='The local directory to be used when cloning. Default: ~/projects/',
        type=str,
        default=DEFAULT_CLONE_ROOT_DIR,
    )
    parser.add_argument(
        'group',
        nargs=1,
        help='The group that owns the repositories',
        type=str,
    )
    cli_args = parser.parse_args()
    config_parser = ConfigParser.SafeConfigParser()
    config_parser.read(os.path.expanduser(GITLAB_INI_FILE))

    args = process_args(cli_args.profile, config_parser, cli_args)
    ret_group = get_group(args)
    for p in ret_group['projects']:
        default_branch = p['default_branch']
        project_path = p['path']
        ssh_url = p['ssh_url_to_repo']
        if default_branch:
            clone_dir = '%s/%s/%s' % (args['root_dir'], args['group'], project_path)
            subprocess_cmd('''\
set -e
mkdir -p {clone_dir}
STATUS_RES=0
git --work-tree {clone_dir} --git-dir {clone_dir}/.git status >> /dev/null 2>&1 || STATUS_RES=$?
if [ $STATUS_RES != 0 ]; then
    echo "Cloning {ssh_url} to {clone_dir}"
    git clone {ssh_url} {clone_dir} >> /dev/null 2>&1
else
    echo "Synching {ssh_url} to {clone_dir}"
    git --work-tree {clone_dir} --git-dir {clone_dir}/.git fetch --all --prune >> /dev/null 2>&1
    git --work-tree {clone_dir} --git-dir {clone_dir}/.git pull >> /dev/null 2>&1
fi

'''.format(
        clone_dir=os.path.expanduser(clone_dir),
        ssh_url=ssh_url,
    ))


if __name__ == '__main__':
    main()
