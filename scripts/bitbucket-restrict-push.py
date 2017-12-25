#! env python
import argparse
import base64
import ConfigParser
import os
import urllib
import subprocess
import requests

BITBUCKET_INI_FILE = '~/.bitbucket.ini'

'https://stash.borderf.net/rest/branch-permissions/latest/projects/CICD/repos/stash-scanner-seed-job/restrictions'
'https://stash.borderf.net/rest/branch-permissions/latest/projects/CICD/repos/stash-scanner-seed-job/restrictions'
'{matcher: {id: "*", displayId: "*", type: {id: "PATTERN"}}, type: "read-only", users: [], groups: []}'
'https://stash.borderf.net/rest/api/1.0/projects/DCKR/repos/'

def subprocess_cmd(command):
    out = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
    if out.strip():
        print out.strip()

def get_project(args):
    url = '%s/rest/api/1.0/projects/%s/repos' % (args['url'], urllib.quote_plus(args['project']))
    ret = requests.get(
        url=url,
        headers={
            'Authorization': 'Basic %s' % base64.b64encode("%s:%s" % (args['username'], args['password'])),
        }
    )
    ret.raise_for_status()
    return ret.json()['values']

def get_restrictions(args, slug):
    url = '%s/rest/branch-permissions/latest/projects/%s/repos/%s/restrictions' % (args['url'], urllib.quote_plus(args['project']), slug)
    ret = requests.get(
        url=url,
        headers={
            'Authorization': 'Basic %s' % base64.b64encode("%s:%s" % (args['username'], args['password'])),
        }
    )
    ret.raise_for_status()
    return ret.json()['values']

def delete_restrictions(args, slug, r):
    url = '%s/rest/branch-permissions/latest/projects/%s/repos/%s/restrictions/%s' % (args['url'], urllib.quote_plus(args['project']), slug, r['id'])
    ret = requests.delete(
        url=url,
        headers={
            'Authorization': 'Basic %s' % base64.b64encode("%s:%s" % (args['username'], args['password'])),
        }
    )
    ret.raise_for_status()
    # return ret.json()['values']

def create_restrictions(args, slug):
    url = '%s/rest/branch-permissions/latest/projects/%s/repos/%s/restrictions' % (args['url'], urllib.quote_plus(args['project']), slug)
    payload = {'matcher': {'id': "*", 'displayId': "*", 'type': {'id': "PATTERN"}}, 'type': "read-only", 'users': [], 'groups': []}
    ret = requests.post(
        url=url,
        json=payload,
        headers={
            'Content-Type': 'application/json',
            'Authorization': 'Basic %s' % base64.b64encode("%s:%s" % (args['username'], args['password'])),
        }
    )
    ret.raise_for_status()
    # return ret.json()

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
        username=process_arg(profile, config_parser, cli_args, 'username'),
        password=process_arg(profile, config_parser, cli_args, 'password'),
        url=process_arg(profile, config_parser, cli_args, 'url'),
    )
    if not ret.get('username'):
        raise ValueError('username is required')
    if not ret.get('password'):
        raise ValueError('password is required')
    if not ret.get('url'):
        raise ValueError('url is required')

    project = cli_args.project[0]
    ret['project'] = project
    return ret


def main():
    parser = argparse.ArgumentParser(description='Restrict push for all repositories in project')
    parser.add_argument(
        '--profile',
        help='The gitlab profile to use within ~/.bitbucket.ini',
        type=str,
        default='default',
    )
    parser.add_argument(
        '--url',
        help='The bitbucket url',
        type=str,
    )
    parser.add_argument(
        '--username',
        help='The bitbucket username',
        type=str,
    )
    parser.add_argument(
        '--password',
        help='The bitbucket password',
        type=str,
    )
    parser.add_argument(
        'project',
        nargs=1,
        help='The project that owns the repositories',
        type=str,
    )
    cli_args = parser.parse_args()
    config_parser = ConfigParser.SafeConfigParser()
    config_parser.read(os.path.expanduser(BITBUCKET_INI_FILE))

    args = process_args(cli_args.profile, config_parser, cli_args)
    ret_repos = get_project(args)
    for repo in ret_repos:
        slug = repo['slug']
        restrictions = get_restrictions(args, slug)
        if restrictions:
            print "Deleting current restrictions for %s/%s" %(args['project'], slug)
        for r in restrictions:
            delete_restrictions(args, slug, r)
        print "Creating restrictions for %s/%s" %(args['project'], slug)
        create_restrictions(args, slug)



if __name__ == '__main__':
    main()
