from time import time

from math import sqrt
from math import ceil
# from numpy import array

# import numpy as np
# import pandas as pd

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)

class ReactiveController:

    def __init__(self, interval=5, instance_info):
        """
        interval: the interval between every decision
        instance_info: instance information in list form, instance i capacity price and launch overhead. The first 6 instances types are t2 instances, 
                        on demand and spot instances
        """
        self.step = step
        self.n_instance = len(instance_info)
        self.instance_info = instance_info
        self.interval = interval

    def calculateCapacity(self, current_instances):
        totalCapa = 0
        for i in range(len(current_instances)):
            totalCapa += instance_info[i][0] * current_instances[i]
        return totalCapa

    def findCheap(self, surplus):
        cheapest_i = 0
        lowest_cost = 1000000000
        for i in range(len(self.instance_info)):
            i_cost = self.instance_info[i][1]
            i_capacity = self.instance_info[i][0]
            if lowest_cost >= i_cost:
                cheapest_i = i
                lowest_cost = i_cost
        num_i = ceil(surplus * 0.1 / i_capacity)
        return cheapest_i, num_i


    def greedyFind(self, residual_requests, current_instances, instance_info):
        totalCapa = calculateCapacity(current_instances)
        surplus = totalCapa - residual_requests
        if (surplus > 0) :
            cheapest_i, num_i = findCheap(surplus)
            current_instances[cheapest_i] += num_i



    def schedule(self, residual_requests, current_instances, instance_info):
        self.instance_info = instance_info
        greedyFind(residual_requests, current_instances, instance_info)
       





