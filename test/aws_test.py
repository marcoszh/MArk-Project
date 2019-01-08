import boto3
import time
from functools import reduce
import operator
from datetime import datetime

from os.path import abspath, dirname, join
import sys
sys.path.insert(0, join(dirname(dirname(abspath(__file__))), 'modules'))
from constants import *
sys.path.pop(0)

now = lambda: time.time()
gap_time = lambda past_time : int((now() - past_time) * 1000)

NUM = 4
# TYPES = ['t2.micro', 't2.medium', 't2.large', \
#         'c5.large', 'c5.xlarge', 'c5.2xlarge', 'c5.4xlarge', \
#         'm5.large', 'm5.xlarge', 'm5.2xlarge', 'm5.4xlarge', 'p2.xlarge']

TYPES = ['t2.large']

input_info = {
    'us-west-1': ('ami-xxx', 'sg-xxx', 'xxx'),
    'us-east-1': ('ami-xxx', 'sg-xxx', 'east-xxx')  
}

def on_demand_test(region):
    type_latencies = {}
    for typ in TYPES:
        start = now()
        latencies = []
        ec2 = boto3.resource('ec2', region_name=region, **CREDENTIALS)
        info = input_info[region]
        instances = ec2.create_instances(ImageId=info[0],InstanceType=typ,MinCount=NUM,MaxCount=NUM, SecurityGroupIds=[info[1]])
        ids = [ i.id for i in instances]
        
        active_ins = 0
        while True:
            res = ec2.meta.client.describe_instance_status()['InstanceStatuses']
            
            count = len([ s for s in res if s['InstanceStatus']['Status'] == 'ok' ])
            if count > active_ins:
                latency = gap_time(start)
                for _ in range(count - active_ins):
                    latencies.append(latency)
                active_ins = count
                
            if active_ins == NUM:
                break
            time.sleep(1)
        sum = reduce(operator.add, latencies)
        type_latencies[typ] = (sum + 0.0) / NUM
        print(typ, ' : ', type_latencies[typ], 'details : ', latencies)
        ec2.instances.filter(InstanceIds=ids).terminate()
        time.sleep(5)
    return type_latencies

def spot_test(region):
    type_latencies = {}
    for typ in TYPES:
        start = now()
        latencies = []
        client = boto3.client('ec2', region_name=region, **CREDENTIALS)
        info = input_info[region]
        res = client.request_spot_fleet(
            SpotFleetRequestConfig={
                'TargetCapacity': NUM,
                'TerminateInstancesWithExpiration': True,
                'ValidFrom': datetime(2018, 1, 1),
                'ValidUntil': datetime(2019, 1, 1),
                'IamFleetRole': 'arn:aws:iam::906727922743:role/aws-ec2-spot-fleet-role',
                'LaunchSpecifications': [{
                    'ImageId': info[0],
                    'KeyName': info[2],
                    'InstanceType': typ,
                    'BlockDeviceMappings': [{
                        'VirtualName': 'Root',
                        'DeviceName': '/dev/sda1',
                        'Ebs': {
                            'VolumeSize': 500,
                            'VolumeType': 'gp2',
                            'DeleteOnTermination': True
                        }
                    }],
                    'Monitoring': {
                        'Enabled': False
                    }
                }],
                'AllocationStrategy': 'lowestPrice',
                'Type': 'request'
            }
        )
        req_id = res['SpotFleetRequestId']
        instance_id_list = []
        while True:
            res = client.describe_spot_fleet_instances(SpotFleetRequestId=req_id)
            if len(res['ActiveInstances']) == NUM:
                instance_id_list = [ i['InstanceId'] for i in res['ActiveInstances'] ]
                break
            time.sleep(2)

        active_ins = 0
        while True:
            res = client.describe_instance_status(InstanceIds=instance_id_list)
            count = len([ s for s in res['InstanceStatuses'] if s['InstanceStatus']['Status'] == 'ok' ])
            if count > active_ins:
                latency = gap_time(start)
                for _ in range(count - active_ins):
                    latencies.append(latency)
                active_ins = count
                
            if active_ins == NUM:
                break
            time.sleep(1)
        sum = reduce(operator.add, latencies)
        type_latencies[typ] = (sum + 0.0) / NUM
        print(typ, ' : ', type_latencies[typ])
        client.cancel_spot_fleet_requests(
            SpotFleetRequestIds=[req_id],
            TerminateInstances=True
        )
        time.sleep(5)
    return type_latencies

if __name__ == '__main__':
    # res = on_demand_test('us-east-1')
    res = spot_test('us-east-1')
    for typ, latency in sorted(res.items()):
        print(f'{typ:15} {latency:15}')
