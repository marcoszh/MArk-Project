import time
import requests
import json
from .constants import *

from .data_accessor import on_demand_prize_accessor, spot_prize_accessor

def update_prize():
    '''
    Update on demand price one time, then try to update spot price in a certain internal continuelly
    Run in another thread
    '''
    update_on_demand_prize()

    while True:
        update_spot_prize()
        time.sleep(UPDATER_INTERVAL)

def update_on_demand_prize():
    res = requests.get(ON_DEMAND_PRIZE_URL).content
    json_response = res[203 : -3]

    dict_json = json.loads(json_response)
    all_prizes = _parse_prize(dict_json['config']['regions'])
    on_demand_prize_accessor.save_prizes(all_prizes)     

def update_spot_prize():
    response = requests.get(SPOT_PRIZE_URL).content
    json_response = response[9 : -2]

    dict_json = json.loads(json_response)
    all_prizes = _parse_prize(dict_json['config']['regions'])
    spot_prize_accessor.save_prizes(all_prizes)

def _parse_prize(prize_dict):
    all_prizes = {}
    for region_prizes in prize_dict:
            
        region_prize = {}
        region = region_prizes['region']
        for instances in region_prizes['instanceTypes']:
            for prizes in instances['sizes']:
                typ = prizes['size'].replace('.', '_')
                prize = prizes['valueColumns'][0]['prices']['USD']
                region_prize[typ] = prize

        all_prizes[region] = region_prize
    return all_prizes


def get_price():
    '''
    Return a prize list ($ / hour)
    '''
    prize_list = []
    east_instance_types = ['c5_large', 'c5_xlarge', 'c5_2xlarge', 'p2_xlarge']
    west_instance_types = ['c5_large', 'c5_xlarge', 'c5_2xlarge']

    sizes = on_demand_prize_accessor.get_prize('us-east-1')
    [ prize_list.append(sizes[typ]) for typ in east_instance_types ]
    
    sizes = spot_prize_accessor.get_prize('us-east')
    [ prize_list.append(sizes[typ]) for typ in east_instance_types ]

    sizes = on_demand_prize_accessor.get_prize('us-west-1')
    [ prize_list.append(sizes[typ]) for typ in west_instance_types ]
    
    sizes = spot_prize_accessor.get_prize('us-west')
    [ prize_list.append(sizes[typ]) for typ in west_instance_types ]

    return prize_list

def get_spot_prize_by_region_type(region, types):
    '''
    Return a prize list based on the input region and types ($ / sec)
    '''
    if region == 'us-east-1' or region == 'us-west-1':
        region = region[0:7]
    
    types = [ t.replace('.', '_') for t in types ]
    prize_list = []
    sizes = spot_prize_accessor.get_prize(region)
    [ prize_list.append(float(sizes[typ])/3600) for typ in types ]
    return prize_list

def get_demand_prize_by_region_type(region, types):
    types = [ t.replace('.', '_') for t in types ]
    prize_list = []
    sizes = on_demand_prize_accessor.get_prize(region)
    [ prize_list.append(float(sizes[typ])/3600) for typ in types ]
    return prize_list