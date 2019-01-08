import asyncio
import logging

from . import aws_manager, prize_request, utils
from .constants import *
from .data_accessor import (aws_accessor, demand_aws_accessor,
                            instance_accessor, backup_ins_accessor, pre_aws_accessor,
                            pre_demand_aws_accessor)

CHECK_PERIOD = 120

class _InstanceSource():
    def set_loop(self, loop_):
        self.loop = loop_
        self.run_loop()

    def run_loop(self):
        return

    def launch_backup(self, name, tag):
        return
    
    def stop_backup(self, name):
        return

    def get_ins_alloc(self, name, balancer):
        pass

    def get_current_ins_and_prize(self, name, index_type):
        pass

    def launch_ins(self, name, params):
        pass

    def kill_ins(self, name, region, typ, num):
        pass

    def kill_all_ins(self, name):
        pass

    def initial_ins(self, name, tag):
        pass

class OnDemandSource(_InstanceSource):    
    def get_ins_alloc(self, name, balancer):
        ins_json = demand_aws_accessor.get_cluster(name)
        if ins_json:
            intance_list = [ utils.dict2Instance(i) for i in ins_json['info'].values() ]
            return balancer.next_ip(name, intance_list)

    def get_current_ins_and_prize(self, name, index_type):
        aws_info = demand_aws_accessor.get_cluster(name)
        intance_list = []
        if aws_info:
            intance_list = [utils.dict2Instance(i) for i in aws_info['info'].values()]
        currentInstance = []
        [ currentInstance.append(len([ i for i in intance_list if i.typ == typ and i.region == DEFAULT_REGION])) for typ in index_type ]

        info = pre_demand_aws_accessor.get_cluster(name)
        if info and info['info']:
            c_tmp = []
            [ c_tmp.append(sum([ i['num'] for _, i in info['info'].items() if i['type'] == typ and i['region'] == DEFAULT_REGION])) for typ in index_type ]
            currentInstance = [ (e1 + e2) for e1, e2 in zip(currentInstance, c_tmp)]
        prize_list = prize_request.get_demand_prize_by_region_type(DEFAULT_REGION, index_type)
        return currentInstance, prize_list

    def launch_ins(self, name, params):
        aws_manager.launch_on_demand_instances.delay(name, params)

    def kill_ins(self, name, region, typ, num):
        aws_manager.kill_on_demand_instances.delay(name, region, typ, num)

    def kill_all_ins(self, name):
        aws_manager.kill_all_on_demand_ins(name, DEFAULT_REGION)

    def initial_ins(self, name, tag):
        aws_manager.launch_on_demand_instances(name, {'imageId':AMIS[DEFAULT_REGION]['CPU'], 'instanceType':'c5.xlarge', 'targetCapacity':6, 'key_value':[('exp_round', tag)] })
        # aws_manager.launch_on_demand_instances(name, {'imageId':AMIS[DEFAULT_REGION]['CPU'], 'instanceType':'c5.large', 'targetCapacity':10, 'key_value':[('exp_round', tag)] })
        # aws_manager.launch_on_demand_instances(name, {'imageId':AMIS[DEFAULT_REGION]['GPU'], 'instanceType':'p2.xlarge', 'targetCapacity':4, 'key_value':[('exp_round', tag)] })

class SpotSource(_InstanceSource):
    def run_loop(self):
        self.loop.create_task(self._moniter())

    # detect the state of spot instances
    async def _moniter(self):
        while True:
            await asyncio.sleep(CHECK_PERIOD)
            logging.info('Check states of spot instances')
            aws_manager.check_spot_states.delay()

    def get_ins_alloc(self, name, balancer):
        ins_json = instance_accessor.get_instances(name)
        backup_ins = backup_ins_accessor.get_instances(name)

        if ins_json:
            intance_list = [ utils.dict2Instance(i) for i in ins_json ]

        if backup_ins:
            backup_instance_list = [ utils.Instance(i.ip, 'c5.large', i.region) for i in [ utils.dict2Instance(i) for i in backup_ins ]]
            intance_list += backup_instance_list
        
        return balancer.next_ip(name, intance_list)

    def get_current_ins_and_prize(self, name, index_type):
        # filter the instances by type and region(Default region: us-east-1)
        intance_list = [ utils.dict2Instance(i) for i in instance_accessor.get_instances(name) ]
        currentInstance = []
        [ currentInstance.append(len([ i for i in intance_list if i.typ == typ and i.region == DEFAULT_REGION])) for typ in index_type ]

        info = pre_aws_accessor.get_cluster(name)
        if info['info']:
            c_tmp = []
            [ c_tmp.append(sum([ i['num'] for _, i in info['info'].items() if i['type'] == typ and i['region'] == DEFAULT_REGION])) for typ in index_type ]
            currentInstance = [ (e1 + e2) for e1, e2 in zip(currentInstance, c_tmp)]            

        prize_list = prize_request.get_spot_prize_by_region_type(DEFAULT_REGION, index_type)
        return currentInstance, prize_list

    def launch_ins(self, name, params):
        aws_manager.launch_spot_instances.delay(name, params)

    def kill_ins(self, name, region, typ, num):
        aws_manager.kill_spot_instances_by_num.delay(name, region, typ, num)

    def kill_all_ins(self, name):
        aws_manager.cancel_all_instances(name)

    def launch_backup(self, name, tag):
        # launch on demand ins for fault tolerance
        aws_manager.launch_on_demand_instances(name, {'imageId':AMIS[DEFAULT_REGION]['CPU'], 'instanceType':'t2.medium', 'targetCapacity':10, 'key_value':[('exp_round', tag)] })
        aws_manager.stop_on_demand_instances(name)
        # aws_manager.start_on_demand_instances(name)

    def stop_backup(self, name):
        aws_manager.stop_on_demand_instances(name)

    def initial_ins(self, name, tag):
        # aws_manager.launch_spot_instances(name, {'imageId':AMIS[DEFAULT_REGION]['CPU'], 'instanceType':'c5.large', 'targetCapacity':1, 'key_value':[('exp_round', tag)] })
        # aws_manager.launch_spot_instances(name, {'imageId':AMIS[DEFAULT_REGION]['CPU'], 'instanceType':'c5.xlarge', 'targetCapacity':10, 'key_value':[('exp_round', tag)] })
        aws_manager.launch_spot_instances(name, {'imageId':AMIS[DEFAULT_REGION]['CPU'], 'instanceType':'c5.large', 'targetCapacity':10, 'key_value':[('exp_round', tag)] })
        aws_manager.launch_spot_instances(name, {'imageId':AMIS[DEFAULT_REGION]['GPU'], 'instanceType':'p2.xlarge', 'targetCapacity':1, 'key_value':[('exp_round', tag)] })
        # aws_manager.launch_spot_instances(name, {'imageId':AMIS[DEFAULT_REGION]['CPU'], 'instanceType':'c5.large', 'targetCapacity':8, 'key_value':[('exp_round', tag)] })
        # aws_manager.launch_spot_instances(name, {'imageId':AMIS[DEFAULT_REGION]['GPU'], 'instanceType':'p2.xlarge', 'targetCapacity':1, 'key_value':[('exp_round', tag)] })


all_ins_sources = {
    'spot': SpotSource(),
    'ondemand': OnDemandSource()
}

ins_source = all_ins_sources[INS_SOURCE]
