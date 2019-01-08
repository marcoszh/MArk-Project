import boto3
import time
from functools import reduce
import operator
from datetime import datetime

from os.path import abspath, dirname, join
import sys
sys.path.insert(0, join(dirname(dirname(abspath(__file__))), 'modules'))
#from constants import *
sys.path.pop(0)

now = lambda: time.time()
gap_time = lambda past_time : int((now() - past_time) * 1000)

NUM = 5

region = 'us-east-1'

TYPES = ['t2.medium', 't2.medium', 't2.medium', 't2.medium', 't2.medium']

input_info = {
    'us-east-1': ('ami-xxx', 'sg-xxx', 'east-xxx')  
}

instanceIds = ['i-xxx', 'i-xxx', 'i-xxx', 'i-xxx', 'i-xxx']
ec2 = boto3.client('ec2')

import paramiko

cert = paramiko.RSAKey.from_private_key_file("/Users/marc/Documents/ec2/east-xxx.pem")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

def check_ssh(ip, user='ubuntu', initial_wait=0, interval=0, retries=1):

    time.sleep(initial_wait)

    for x in range(retries):
        try:
            ssh.connect(ip, username=user, pkey=cert)
            return True
        except Exception as e:
            print(e)
            time.sleep(interval)
    return False

def on_demand_test(region):
    type_latencies = {}
    for typ in TYPES:
        latencies = []
        info = input_info[region]
        ec2.stop_instances(InstanceIds=instanceIds)
        print('stopping instances')
        time.sleep(120)
        ec2.start_instances(InstanceIds=instanceIds)
        print('starting instances')
        start = now()
        active_ins = 0
        while True:
            res = ec2.describe_instances(InstanceIds=instanceIds)['Reservations'][0]['Instances']
            count = len([ s for s in res if s['State']['Name']=='running'])
            print('count: '+ str(count))
            if count == NUM:
                ips = []
                for r in res:
                    ips.append(r['PublicIpAddress'])
                print(ips)
                while True:
                    ssh_count = len([ip for ip in ips if check_ssh(ip=ip)])
                    print('ssh_count: '+str(ssh_count))
                    if ssh_count > active_ins:
                        latency = gap_time(start)
                        for _ in range(ssh_count - active_ins):
                            latencies.append(latency)
                        active_ins = ssh_count

                    if active_ins == NUM:
                        break
                    time.sleep(1)
                break
            time.sleep(1)
        sum = reduce(operator.add, latencies)
        type_latencies[typ] = (sum + 0.0) / NUM
        print(typ, ' : ', type_latencies[typ], 'details : ', latencies)
    return type_latencies

if __name__ == '__main__':
    res = on_demand_test('us-east-1')
    # res = spot_test('us-east-1')
    for typ, latency in sorted(res.items()):
        print(f'{typ:15} {latency:15}')
