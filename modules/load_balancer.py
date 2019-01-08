from . import utils
from .constants import *

class _Balancer():
    def __init__(self):
        self.indexes = {}

    def next_ip(self, name, instance_list):
         pass

class RoundBalancer(_Balancer):
    def next_ip(self, name, instance_list):
        if len(instance_list) <= 0:
            return

        ip_list = [ i.ip for i in instance_list ]
        index = self.indexes[name] if name in self.indexes else -1
        
        if index >= len(ip_list) - 1:
            index = 0
        else:
            index += 1

        self.indexes[name] = index
        return (instance_list[index].ip, instance_list[index].typ)

class WeightedBalancer(_Balancer):
    def next_ip(self, name, instance_list):
        if len(instance_list) <= 0:
            return
        
        weight_list = [ (i.ip, Instance_Weights[i.typ], i.typ) for i in instance_list ]
        max_weight = max([ i[1] for i in weight_list ])
        gcd_weight = utils.gcd([ i[1] for i in weight_list ])

        index, current_weight = self.indexes[name] if name in self.indexes else (-1, max_weight)
        next_ip_index = -1
        while next_ip_index < 0:
            for i in range(index + 1, len(weight_list)):
                if weight_list[i][1] >= current_weight:
                    next_ip_index = i
                    break

            if next_ip_index < 0:
                current_weight = current_weight - gcd_weight if current_weight > 0 else max_weight
                index = -1
        
        self.indexes[name] = (next_ip_index, current_weight)
        return (weight_list[next_ip_index][0], weight_list[next_ip_index][2])

round_balancer = RoundBalancer()
weight_balancer = WeightedBalancer()

_balancers = {
    'round' : round_balancer,
    'weight' : weight_balancer
}

def get_balancer(name=DEFAULT_BALANCER):
    return _balancers[name]

