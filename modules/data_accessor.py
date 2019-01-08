# coding: utf-8
import json
from pymongo import MongoClient
from .constants import *

class _BaseAccessor():
    def __init__(self, host_, port_, col):
        self.client = MongoClient(host=host_, port=port_, connect=False)
        self.collection = self.client.serving[col]

    def subscribe(self, func):
        """
        subscribe to the change of DB
        Require: func (dict) 
        """
        self.call_back = func


class PrizeAccessor(_BaseAccessor):
    def save_prizes(self, prizes):
        for region, sizes in prizes.items():
            self.collection.update(
                {'region' : region},
                {'region' : region, 'sizes' : sizes},
                upsert=True
            )
    
    def get_prize(self, region):
        record = self.collection.find_one({'region' : region})
        if record:
            return record['sizes']

class AWSAccessor(_BaseAccessor):
    def save_cluster(self, name, info):
        doc = self.get_cluster(name)
        if doc:
            doc['info'].update(info)
        else:
            doc = {'name' : name, 'info' : info} 
        self.collection.update({'name' : name}, doc, upsert=True)
    
    def get_by_region_typ(self, name, region, typ):
        record = self.collection.find_one({'name' : name})
        if record:
            for r, info in record['info'].items():
                if info['region'] == region and info['type'] == typ:
                    return (r, info['instance_id_list'])

    def get_cluster(self, name):
        return self.collection.find_one({'name' : name})

    def get_all_cluster(self):
        return self.collection.find({})
        
    def del_request(self, name, request_id):
        records = self.collection.find_one({'name' : name})
        del records['info'][request_id]
        self.collection.update({'name' : name}, records)
    
    def del_requests(self, name, ids):
        [self.del_request(name, id) for id in ids]

    def get_requests(self, name):
        record = self.collection.find_one({'name' : name})
        if record:
            return record['info'].keys()

class InstanceAccessor(_BaseAccessor):
    def update_instances(self, name, instance_list):
        doc = self.collection.find_one({'name' : name})
        if doc:
            doc['instances'] += instance_list
        else:
            doc = {'name' : name, 'instances' : instance_list} 
        self.collection.update({'name' : name}, doc, upsert=True)

    def get_instances(self, name):
        record = self.collection.find_one({'name' : name})
        if record:
            return record['instances']
    
    def get_all_instances(self):
        return self.collection.find({})

    def del_all_instance(self):
        self.collection.drop()

    def del_instance(self, name, instances):
        records = self.collection.find_one({'name' : name})
        [ records['instances'].remove(instance) for instance in instances]
        self.collection.update({'name' : name}, records)

on_demand_prize_accessor = PrizeAccessor(DB_HOST, MONGO_PORT, ON_DEMAND_PRIZE_DB)
spot_prize_accessor = PrizeAccessor(DB_HOST, MONGO_PORT, SPOT_PRIZE_DB)

# spot instance
aws_accessor = AWSAccessor(DB_HOST, MONGO_PORT, AWS_DB)
pre_aws_accessor = AWSAccessor(DB_HOST, MONGO_PORT, PRE_AWS_DB)
instance_accessor = InstanceAccessor(DB_HOST, MONGO_PORT, INS_DB)
backup_ins_accessor = InstanceAccessor(DB_HOST, MONGO_PORT, BACKUP_DB)

# on-demand instance
demand_aws_accessor = AWSAccessor(DB_HOST, MONGO_PORT, DEMAND_AWS_DB)
pre_demand_aws_accessor = AWSAccessor(DB_HOST, MONGO_PORT, PRE_DEMAND_AWS_DB)

