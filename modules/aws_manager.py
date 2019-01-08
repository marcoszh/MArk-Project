import json
import logging
import operator
import tempfile
import time
from datetime import datetime

import boto3
import requests
from celery import Celery, task

from . import utils
from .model_source import mdl_source
from .constants import *
from .data_accessor import (aws_accessor, demand_aws_accessor,
                            instance_accessor, backup_ins_accessor, pre_aws_accessor,
                            pre_demand_aws_accessor)

app = Celery(
    'aws-manager', 
    broker='redis://localhost:6379', 
    backend='redis://')

@app.task
def check_spot_states():
    all_info = aws_accessor.get_all_cluster()
    if all_info:
        client = get_client()
        spot_list = []
        [ spot_list.append(c) for c in all_info ]

        cancel_reqs = []
        num = 0
        for info in spot_list:
            name = info['name']
            for req, i in info['info'].items():
                res = client.describe_spot_fleet_requests(SpotFleetRequestIds=[req])
                if res['SpotFleetRequestConfigs'][0]['SpotFleetRequestState'] != 'active':
                    logging.info(f'Inactive spot request detected: {req}')
                    num += len(i['instance_id_list'])
                    cancel_reqs.append(req)
                    start_on_demand_instances(name)

        time.sleep(10)
        if len(cancel_reqs) > 0:
            logging.info('Cancel inactive requests')
            cancel_spot_instances(name, cancel_reqs)

            # interrupt recovery test
            time.sleep(100)
            logging.info(f'Monitor launching {num} spot instances')
            name = 'inception'
            launch_spot_instances(name, {'imageId':AMIS[DEFAULT_REGION]['CPU'], 'instanceType':'c5.large', 'targetCapacity':num, 'key_value':[('exp_round', 0)] })
            stop_on_demand_instances(name)

@app.task
def launch_on_demand_instances(name, params):
    params['region'] = params['region'] if 'region' in params else DEFAULT_REGION
    ec2 = boto3.resource('ec2', region_name=params['region'], **CREDENTIALS)
    instances = ec2.create_instances(
        ImageId=params['imageId'],
        InstanceType=params['instanceType'],
        KeyName=KEYS[params['region']],
        MinCount=params['targetCapacity'],
        MaxCount=params['targetCapacity'], 
        SecurityGroupIds=SECURITY_GROUPS[params['region']],
        BlockDeviceMappings=[
            {
                'VirtualName': 'Root',
                'DeviceName': '/dev/sda1',
                'Ebs': {
                    'VolumeSize': 51,
                    'VolumeType': 'gp2',
                    'DeleteOnTermination': True
                }
            }
        ],
    )

    time.sleep(10)
    ids = [ i.id for i in instances]

    pre_info = {}
    single_info = {
        'region' : params['region'],
        'type' : params['instanceType'],
        'num' : 1
    }
    [ pre_info.update({id: single_info}) for id in ids ]
    pre_demand_aws_accessor.save_cluster(name, pre_info)

    if 'key_value' in params:
        _add_tags(ec2.meta.client, ids, params['key_value'])
    

    ins_list = utils.get_ins_from_ids(params['region'], ids)
    # check the state of instances by trying ssh
    while True:
        logging.info('Checking SSH connection')
        if all([_check_ssh(i.ip) for i in ins_list]):
            logging.info('Checked SSH connection')
            break
        time.sleep(10)
        ins_list = utils.get_ins_from_ids(params['region'], ids)

    mdl_source.setup_config(ins_list, params['region'], params['instanceType'])
    
    ins_dict = {}
    [ ins_dict.update( {i: utils.get_ins_from_id(ec2, params['region'], i)} ) for i in ids]

    pre_demand_aws_accessor.del_requests(name, ids)
    save_ins = {}
    for id, ins in ins_dict.items():
        save_ins[id] = ins.__dict__
    demand_aws_accessor.save_cluster(name, save_ins)

def stop_on_demand_instances(name, typ='t2.medium' , region=DEFAULT_REGION):
    client = get_client()
    info = demand_aws_accessor.get_cluster(name)['info']
    ins = []
    [ins.append(id) for id, instance in info.items() if instance['typ'] == typ and instance['region'] == region]

    if len(ins) > 0:
        logging.info(f'Stop {len(ins)} {typ} on demand backup instances')
        backup_ins_accessor.del_all_instance()
        res = client.stop_instances(InstanceIds=ins)
        while True:
            res = client.describe_instances(InstanceIds=ins)
            ins_res = res['Reservations'][0]['Instances']
            if all([ r['State']['Name'] == 'stopped' for r in ins_res ]):
                logging.info(f'Backup instances stopped')
                break
            logging.info(f'Checking backup instances state')
            time.sleep(10)


def start_on_demand_instances(name, typ='t2.medium' , region=DEFAULT_REGION):
    client = get_client()
    record = demand_aws_accessor.get_cluster(name)
    if record:
        info = record['info']
        ins = []
        [ins.append(id) for id, instance in info.items() if instance['typ'] == typ and instance['region'] == region]

        if len(ins) > 0:
            logging.info(f'Start {len(ins)} {typ} on demand instances')
            res = client.start_instances(InstanceIds=ins)
            instances = utils.get_ins_from_ids(region, ins)

            while True:
                logging.info('Checking SSH connection')
                if all([_check_ssh(i.ip) for i in instances]):
                    logging.info('Checked SSH connection')
                    break
                time.sleep(10)
                instances = utils.get_ins_from_ids(region, ins)

            mdl_source.setup_config(instances, region, typ)

            instances_json = [ i.__dict__ for i in instances ]
            backup_ins_accessor.update_instances(name, instances_json)
            logging.info('Started Backup instances')


@app.task
def kill_on_demand_instances(name, region, typ, num):
    if num <= 0:
        return
    ec2 = boto3.resource('ec2', region_name=region, **CREDENTIALS)
    info = demand_aws_accessor.get_cluster(name)['info']
    ins = []
    [ins.append(id) for id, instance in info.items() if instance['typ'] == typ and instance['region'] == region]

    if len(ins) > num:
        ins = ins[-num:]

    if len(ins) > 0:
        logging.info(f'To kill {num} {typ} instances')
        ec2.instances.filter(InstanceIds=ins).terminate()
        demand_aws_accessor.del_requests(name, ins)

def kill_all_on_demand_ins(name, region):
    ec2 = boto3.resource('ec2', region_name=region, **CREDENTIALS)
    records = demand_aws_accessor.get_cluster(name)
    pre_rec = pre_demand_aws_accessor.get_cluster(name)
    if pre_rec:
        pre_ids = pre_rec['info'].keys()
        if len(list(pre_ids)) > 0:
            ec2.instances.filter(InstanceIds=list(pre_ids)).terminate()
            pre_demand_aws_accessor.del_requests(name, pre_ids)
    if records:
        ids = records['info'].keys()
        if len(list(ids)) > 0:
            ec2.instances.filter(InstanceIds=list(ids)).terminate()
            demand_aws_accessor.del_requests(name, ids)

@app.task
def launch_spot_instances(name, params):
    """
    params :
        - 'imageId'
        - 'instanceType' 
        - 'targetCapacity'
        - 'key_value' (optional)
        - 'region' (optional)

    """
    params['region'] = params['region'] if 'region' in params else DEFAULT_REGION
    client = get_client(params['region'])

    logging.info(f'Launch {params["targetCapacity"]} {params["instanceType"]} instances')
    request_id = _send_request(client, params)
    pre_info = {
        request_id : {
            'region' : params['region'],
            'type' : params['instanceType'],
            'num' : params['targetCapacity']
        }
    }
    pre_aws_accessor.save_cluster(name, pre_info)

    instance_id_list = _wait_active(client, request_id, params['targetCapacity'])
    # _wait_initialized(client, instance_id_list)
    if 'key_value' in params:
        _add_tags(client, instance_id_list, params['key_value'])
    _set_security_group(client, instance_id_list, SECURITY_GROUPS[params['region']])

    ins = utils.get_ins_from_ids(params['region'], instance_id_list)

    # check the state of instances by trying ssh
    while True:
        logging.info('Checking SSH connection')
        if all([_check_ssh(i.ip) for i in ins]):
            logging.info('Checked SSH connection')
            break
        time.sleep(10)

    mdl_source.setup_config(ins, params['region'], params['instanceType'])

    # make the instances configured
    time.sleep(3)

    pre_aws_accessor.del_request(name, request_id)
    info = {
        request_id : {
            'region' : params['region'],
            'type' : params['instanceType'],
            'instance_id_list' : instance_id_list
        }
    }
    aws_accessor.save_cluster(name, info)
    instances_json = [ i.__dict__ for i in ins ]
    instance_accessor.update_instances(name, instances_json)

def _check_ssh(ip):
    try:
        utils.get_session(ip)
    except Exception as e:
        print(f'SSH exception for ip: {ip}')
        return False
    else:
        return True

@app.task
def kill_spot_instances_by_num(name, region, typ, num):
    info = aws_accessor.get_cluster(name)['info']

    req_ins_num = []
    [ req_ins_num.append((len(ins['instance_id_list']), r)) for r, ins in info.items() if ins['type'] == typ and ins['region'] == region ]
    
    logging.info(f'Will kill {num} {typ} instances')

    cancel_req_ids = []
    total_size = 0
    req_ins_num.sort(key=lambda e : e[0], reverse=True)
    for size, req in req_ins_num:
        if size + total_size > num:
            continue
        total_size += size
        cancel_req_ids.append(req)

    logging.info(f'Kill {total_size} {typ} instances')
            
    if len(cancel_req_ids) > 0:
        cancel_spot_instances(name, cancel_req_ids)

def cancel_spot_instances(name, request_ids):
    info = aws_accessor.get_cluster(name)['info']
    for i in request_ids:
        if i not in info:
            logging.info('Request ID : {} not found'.format(i))
            continue
        instance_id_list = info[i]['instance_id_list']
        region = info[i]['region']
        client = get_client(region)
        res = client.cancel_spot_fleet_requests(
            SpotFleetRequestIds=[i],
            TerminateInstances=True
        )
        if 'SuccessfulFleetRequests' in res:
            logging.info('Successful cancel spot fleet request {}'.format(i))
            instance_accessor.del_instance(name, [ i.__dict__ for i in utils.get_ins_from_ids(region, instance_id_list)])
            aws_accessor.del_request(name, i)

def cancel_all_instances(name):
    requests = aws_accessor.get_requests(name)
    if requests:
        cancel_spot_instances(name, requests)


def get_client(region=DEFAULT_REGION):
    return boto3.client('ec2', region_name=region, **CREDENTIALS)

def _get_request_config(params):
    base = {
        'TargetCapacity': params['targetCapacity'],
        'TerminateInstancesWithExpiration': True,
        'ValidFrom': datetime(2018, 1, 1),
        'ValidUntil': datetime(2019, 1, 1),
        'IamFleetRole': 'arn:aws:iam::906727922743:role/aws-ec2-spot-fleet-role',
        'LaunchSpecifications': [{
            'ImageId': params['imageId'],
            'KeyName': KEYS[params['region']],
            'InstanceType': params['instanceType'],
            'BlockDeviceMappings': [{
                'VirtualName': 'Root',
                'DeviceName': '/dev/sda1',
                'Ebs': {
                    'VolumeSize': 75,
                    'VolumeType': 'gp2',
                    'DeleteOnTermination': True
                }
            }],
            'Monitoring': {
                'Enabled': False
            }
        }],
        'AllocationStrategy': 'lowestPrice',
        'Type': 'maintain'
    }
    return base

def _send_request(client, params):
    """
    Create a new spot fleet request and send it.

    :return: request id
    :rtype: str
    """
    # Note: We cannot set SecurityGroup here in that it will cause an error.
    res = client.request_spot_fleet(
        SpotFleetRequestConfig=_get_request_config(params)
    )
    logging.info('Created spot fleet request {}'.format(res["SpotFleetRequestId"]))
    return res['SpotFleetRequestId']

def _wait_initialized(client, instance_id_list):
    """
    Wait for all instances specified by `instance_id_list` to be initialized.
    """
    logging.info('Waiting for instances to be initialized.')
    while True:
        res = client.describe_instance_status(InstanceIds=instance_id_list)
        if len(res['InstanceStatuses']) == 0:
            time.sleep(10)
            continue
        if all([ s['InstanceStatus']['Status'] == 'ok' for s in res['InstanceStatuses'] ]):
            logging.info('Instances are initialized now.')
            return
        time.sleep(10)

def _wait_active(client, request_id, max_num):
    """
    Wait for spot fleet request with `request_id` to be active.

    :return: id of instances
    :rtype: list
    """
    logging.info('Waiting for instances to be active')
    while True:
        res = client.describe_spot_fleet_instances(SpotFleetRequestId=request_id)
        if len(res['ActiveInstances']) == max_num:
            logging.info('Instances are active now.')
            instance_id_list = [ i['InstanceId'] for i in res['ActiveInstances'] ]
            return instance_id_list
        time.sleep(10)

def _set_security_group(client, instance_id_list, security_groups):
    """
    Set the security group for instances specified by `instance_id_list`.
    """
    logging.info('Setting the security group of instances.')
    for instance_id in instance_id_list:
        client.modify_instance_attribute(InstanceId=instance_id, Groups=security_groups)

def _add_tags(client, instance_id_list, key_value):
    tags = [ {'Key':k, 'Value':str(v)} for k, v in key_value ]
    client.create_tags(Resources=instance_id_list, Tags=tags)

    '''
    Filter based on the tag:
    
    res = client.describe_instances(
        Filters=[
            {
                'Name': 'tag:' + key,
                'Values': [value]
            }
        ]
    )
    '''
