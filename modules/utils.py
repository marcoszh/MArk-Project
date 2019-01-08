import logging
import argparse
import pathlib
import os
from base64 import b64decode
from os.path import abspath, dirname, join

import time
import boto3
import paramiko
from functools import reduce
from .constants import * 
from .data_accessor import aws_accessor, instance_accessor

KEY_FILE = '~/.ssh/id_rsa.pub'

upper_folder = dirname(dirname(abspath(__file__)))

now = lambda: time.time()
gap_time = lambda past_time : int((now() - past_time) * 1000)

gcd = lambda array : reduce( _gcd_in_two, array)
def _gcd_in_two(x, y):
    """
    Requirement : !(x==0 && y==0)
    """
    max_val = max(x, y)
    min_val = min(x, y)

    if min_val == 0:
        return max_val
    else:
        return _gcd_in_two(min_val, max_val % min_val)

decode_image = lambda raw_data: b64decode(raw_data)
    
def load_cluster_instances(name):
    info = aws_accessor.get_cluster(name)
    instances = []
    for _, id in info['info'].items():
        ec2 = boto3.resource('ec2', region_name=id['region'], **CREDENTIALS)
        [ instances.append(ec2.Instance(i)) for i in id['instance_id_list'] ]
    return instances

get_ins = lambda instance, region: Instance(instance.public_ip_address, instance.instance_type, region)
get_ins_from_id = lambda ec2, region, id: get_ins(ec2.Instance(id), region)

def get_ins_from_ids(region, instance_id_list):
    ins = []
    ec2 = boto3.resource('ec2', region_name=region, **CREDENTIALS)
    [ ins.append(get_ins(ec2.Instance(i), region)) for i in instance_id_list ]
    return ins

class Instance:
    def __init__(self, ip, typ, region):
        self.ip = ip
        self.typ = typ
        self.region = region

    def __repr__(self):
        return f'Instance({self.ip}, {self.typ}, {self.region})'

    def __str__(self):
        self.__repr__

def dict2Instance(dct):
    if 'ip' in dct and 'typ' in dct and 'region' in dct:
        return Instance(dct['ip'], dct['typ'], dct['region'])
        
def parse_instances(cursor):
    lst = []
    [ lst.append(c) for c in cursor ]
    res = {}
    for dct in lst:
        res[dct['name']] = [ dict2Instance(i) for i in dct['instances'] ]
    return res

def get_session(ip):
    ssh = paramiko.client.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())
    key_name = get_key_path()
    ssh.connect(ip, username='ubuntu', key_filename=key_name)
    # sftp = ssh.open_sftp()
    return ssh

def check_command(ssh_client, command, debug=False):
    _, stdout, stderr = ssh_client.exec_command(command)
    stdout.channel.set_combine_stderr(True)
    is_success = stdout.channel.recv_exit_status() == 0
    if debug or (not is_success):
        for line in stdout.xreadlines():
            print(line)
    return is_success

def get_key_path():
    return os.path.expanduser(KEY_FILE)

def get_project_root():
    return pathlib.Path(__file__).parent.parent

def _mkdir(newdir):
    """
    works the way a good mkdir should :)
        - already exists, silently complete
        - regular file in the way, raise an exception
        - parent directory(ies) does not exist, make them as well
    """
    if type(newdir) is not str:
        newdir = str(newdir)
    if os.path.isdir(newdir):
        pass
    elif os.path.isfile(newdir):
        raise OSError("a file with the same name as the desired " \
                      "dir, '%s', already exists." % newdir)
    else:
        head, tail = os.path.split(newdir)
        if head and not os.path.isdir(head):
            _mkdir(head)
        if tail:
            os.mkdir(newdir)

def get_public_keys():
    return [
        'ssh-rsa xx',
        'ssh-rsa xxx'
    ]