from time import time

from math import sqrt
from numpy import array

import numpy as np
# import pandas as pd




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
        self.interval = interval

    def calculateCapacity(self, current_instances):
        totalCapa = 0
        for i in range(len(current_instances)):
            totalCapa += self.instance_info[i][0] * current_instances[i]
        return totalCapa

    def findCheap(self, t_start, t_stop, residualForecasts, time_span):
        cheapest_i = 0
        lowest_cost = 1000000000
        for i in range(len(self.instance_info)):
            total_cost = self.instance_info[i][1] * time_span + self.instance_info[i][2]
            i_capacity = self.instance_info[i][0]
            counted = 0
            for j in range(t_stop - t_start):
                if (residualForecasts[t_start + j] > 0):
                    counted += i_capacity if (residualForecasts[t_start + j] >= i_capacity) else residualForecasts[t_start + j]
            cost_per_r = (total_cost * 1.0) / counted
            #print('i:'+str(i)+' total_cost:'+str(total_cost)+' i_capacity:'+str(i_capacity)+' cost_p:'+str(cost_per_r))
            if lowest_cost >= cost_per_r:
                cheapest_i = i
                lowest_cost = cost_per_r
        return cheapest_i

    def findHigh(self, t_start, t_stop, residualForecasts, time_span):
        highest_i = -1
        highest_cost = 0
        high_demand = max(float(s) for s in residualForecasts)
        # print(residualForecasts)
        # print(high_demand)
        for i in range(len(self.instance_info)):
            if self.instance_plan[t_start][i] <= 0:
                continue
            total_cost = self.instance_info[i][1] * time_span
            i_capacity = self.instance_info[i][0]
            
            if (-1 *high_demand) < i_capacity:
                continue
            counted = 0
            for j in range(t_stop - t_start):
                    counted +=  i_capacity if (residualForecasts[t_start + j] <= i_capacity) else - residualForecasts[t_start + j]
            cost_per_r = (total_cost * 1.0) / counted
            #print('i:'+str(i)+' total_cost:'+str(total_cost)+' i_capacity:'+str(i_capacity)+' cost_p:'+str(cost_per_r))
            if highest_cost <= cost_per_r:
                highest_i = i
                highest_cost = cost_per_r
        return highest_i

    def fill(self, t_start, t_stop, residualForecasts):
        #print('fill t_start: '+str(t_start)+' t_stop: '+str(t_stop))
        time_span = t_stop * self.interval #timespan in seconds
        time_span = time_span if (time_span > 60) else 60
        #print('timespan: '+str(time_span))
        cheapest_i = self.findCheap(t_start, t_stop, residualForecasts, time_span)
        #print('cheapest_i '+str(cheapest_i))
        for i in range(t_stop - t_start):
            self.instance_plan[t_start + i][cheapest_i] += 1
        #print(self.instance_plan)
        residualForecasts[:] = [ x - self.instance_info[cheapest_i][0] for x in residualForecasts]
        #print(residualForecasts)
        try:
            start_inc = next(i for i,v in enumerate(residualForecasts) if v > 0.0)
            #print('start_inc:'+str(start_inc))
            t_start = start_inc + t_start
            t_stop = len(residualForecasts) - next(i for i,v in enumerate(reversed(residualForecasts)) if v > 0.0)
        except StopIteration:
            return
        #print('t_stop:'+str(t_stop))
        if (residualForecasts[2] < 0):
            return
        self.fill(t_start, t_stop, residualForecasts) 

    def kill(self, t_start, t_stop, residualForecasts):
        #print('fill t_start: '+str(t_start)+' t_stop: '+str(t_stop))
        time_span = t_stop * self.interval
        time_span = time_span if (time_span > 60) else 60
        highest_i = self.findHigh(t_start, t_stop, residualForecasts, time_span)
        #print('highest_i '+str(highest_i))
        if highest_i == -1:
            return
        for i in range(t_stop - t_start):
            self.instance_plan[t_start + i][highest_i] -= 1
        #print(self.instance_plan)
        residualForecasts[:] = [ x + self.instance_info[highest_i][0] for x in residualForecasts]
        try:
            start_inc = next(i for i,v in enumerate(residualForecasts) if v < 0.0)
            t_start = start_inc + t_start
            t_stop = len(residualForecasts) - next(i for i,v in enumerate(reversed(residualForecasts)) if v < 0.0)
        except StopIteration:
            return
        self.kill(t_start, t_stop, residualForecasts)
        return 

    def greedyFind(self, t_current):
        if t_current >= 3:
            return
        totalCapa = self.calculateCapacity(self.instance_plan[t_current])
        residualForecasts = [ x - totalCapa for x in self.forecasts]
        #print(residualForecasts)
        if (residualForecasts[t_current] >= 0):
            t_stop = 0
            for i in range(len(residualForecasts) - t_current):
                if (residualForecasts[i + t_current] >= 0):
                    t_stop += 1
                else:
                    break
            #print('fill t_stop:' + str(t_stop))
            self.fill(t_current, t_stop, residualForecasts)
        else:
            t_stop = 0
            for i in range(len(residualForecasts) - t_current):
                if (residualForecasts[i+ t_current] < 0):
                    t_stop +=1
                else:
                    break
            #print('kill t_stop:' + str(t_stop))
            self.kill(t_current, t_stop, residualForecasts)
        self.greedyFind(t_current + t_stop)


    def schedule(self, forecasts, current_instances, instance_info):
        """
        forecasts: list of average demands
        current_instances: list, number at index i equals to the number of instance i
        instance_info:
        """
        self.instance_info = instance_info
        # step + 1, index 0 means current, 1 means the first prediction
        self.instance_plan = [current_instances.copy() for i in range(self.step)]
        self.forecasts = forecasts
        #print(self.instance_plan)
        self.greedyFind(0)
        #revise(instance_plan)
        return self.instance_plan[2], self.instance_plan[0]
       





