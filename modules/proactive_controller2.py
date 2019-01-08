from time import time

from math import sqrt
from numpy import array

import numpy as np
# import pandas as pd

STEP_AHEAD = 6


class ProactiveController:
    """plan futurn instances
    Just init this class and use predict function to predict
    """

    def __init__(self, step=50, interval=60, instance_info=None):
        """
        step: how many steps ahead the prediction gives
        interval: the interval between every time step
        instance_info: instance information in array form, instance i capacity price and launch overhead.
        """
        self.step = step
        self.n_instance = len(instance_info)
        self.instance_info = instance_info
        self.instance_plan = None
        self.forecasts = None
        self.existing_limit = None
        self.interval = interval

    def calculateCapacity(self, current_instances):
        totalCapa = 0
        for i in range(len(current_instances)):
            totalCapa += self.instance_info[i][0] * current_instances[i]
        return totalCapa

    def findCheapest(self, t_span, residualForecasts, max_idx):
        cheapest_i = -1
        lowest_cost = 10000000.0
        #print('start find low: ' +' t_span '+str(t_span))
        for i in range(len(self.instance_info)):
            totalCost = self.instance_info[i][1] * t_span * self.interval + self.instance_info[i][2]
            iCapa = self.instance_info[i][0]
            counted = 0
            for j in range(t_span):
                if residualForecasts[max_idx + j] > 0:
                    counted += iCapa if (residualForecasts[max_idx + j] >= iCapa) else residualForecasts[max_idx + j]
            cost_per_r = (totalCost * 1.0) / counted
            #print('i:'+str(i)+' total_cost:'+str(totalCost)+' i_capacity:'+str(iCapa)+' cost_p:'+str(cost_per_r))
            if lowest_cost >= cost_per_r > 0:
                if i >= self.n_instance:
                    if self.existing_limit[i-self.n_instance]<=0:
                        continue
                cheapest_i = i
                lowest_cost = cost_per_r
                #print('new low '+str(i))
        if cheapest_i >= self.n_instance:
            self.existing_limit[cheapest_i - self.n_instance] -= 1
        return cheapest_i

    def fill(self):
        totalCapa = self.calculateCapacity(self.instance_plan)
        residualForecasts = [ x - totalCapa for x in self.forecasts]
        # print('residual: ' + str(residualForecasts))
        residual_head = residualForecasts[:STEP_AHEAD]
        residual_head_max = max(residual_head)
        residual_head_max_idx = residual_head.index(residual_head_max)
        if residual_head_max <= 0:
            return
        t_span = 0
        for i in range(residual_head_max_idx, len(residualForecasts)):
            if residualForecasts[i] >= 0:
                t_span += 1
            else:
                break
        #print('t_span: ' + str(t_span))
        cheapest_i = self.findCheapest(t_span, residualForecasts, residual_head_max_idx)
        self.instance_plan[cheapest_i] += 1
        self.fill()



    def schedule(self, forecasts, current_instances, instance_info):
        """
        forecasts: list of average demands
        current_instances: list, number at index i equals to the number of instance i
        instance_info:
        """
        #
        # print('start new iteration')
        # print(current_instances)
        self.n_instance = len(instance_info)
        self.instance_info = [row[:] for row in instance_info]
        for i in range(len(instance_info)):
            self.instance_info.append([instance_info[i][0],instance_info[i][1], 0])
        self.existing_limit = current_instances.copy()
        #print(self.existing_limit)
        self.instance_plan = [0] * len(self.instance_info)
        self.forecasts = forecasts
        #print(self.instance_plan)
        self.fill()
        # print(self.instance_plan)
        results = [0] * self.n_instance
        for i in range(self.n_instance):
            results[i] = self.instance_plan[i] + self.instance_plan[i+self.n_instance]
        launch = self.instance_plan[:self.n_instance]
        destroy = self.instance_plan[self.n_instance:]
        destroy = [a - b for a, b in zip(current_instances, destroy)]
        # print(launch)
        # print(destroy)
        return results, launch, destroy
       





