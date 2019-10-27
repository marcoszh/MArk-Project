
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import json
import time
from os.path import abspath, dirname, join
from base64 import b64encode, b64decode

import requests

import numpy as np

upper_folder = abspath(dirname(dirname(__file__)))

sender = lambda data: requests.post(
    f'http://{args.host}:{args.port}/predict/{args.name}',
    headers={"Content-type": "application/json"},
    data=json.dumps({ 
        'type':'image',
        'data': data
    })
)

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', type=str, default='127.0.0.1')
    parser.add_argument('--port', type=int, default=7001)
    parser.add_argument('--name', type=str, default='mx')
    parser.add_argument('--timeout', type=int, default=490)
    parser.add_argument('--burst', type=float, default=0.5)
    return parser.parse_args()

def get_data():
    with open(f'{upper_folder}/resources/test.jpg', 'rb') as f:
        raw_data = f.read()
        base64_bytes = b64encode(raw_data)
        base64_string = base64_bytes.decode('utf-8')
        return base64_string

def send_data(args, reader):
    pool = ThreadPoolExecutor(5000)
    data = get_data()

    for row in reader:
        if reader.line_num > args.timeout:
            break

        num = int(int(row['tweets']) * 1.8)
        lam = (60 * 1000.0) / num
        samples = np.random.poisson(lam, num)
        print(f'line: {reader.line_num}; sample_number: {num}')
        for s in samples:
            pool.submit(sender, data)
            # sender(data)
            # print(f'Send request after {s} ms')
            time.sleep(s/1000.0)

def get_kr_data():
    test_file = f'{upper_folder}/keras/SageMaker/cat.jpg'
    with open(test_file, 'rb') as f:
        raw_data = f.read()
        base64_bytes = b64encode(raw_data)
        base64_string = base64_bytes.decode('utf-8')
        return base64_string

def send_data_kr(args, reader):
    pool = ThreadPoolExecutor(5000)
    data = get_kr_data()

    for row in reader:
        if reader.line_num > args.timeout:
            break

        num = int(int(row['tweets']) / 2)
        lam = (60 * 1000.0) / num
        samples = np.random.poisson(lam, num)
        print(f'line: {reader.line_num}; sample_number: {num}')
        for s in samples:
            pool.submit(sender, data)
            # sender(data)
            # print(f'Send request after {s} ms')
            time.sleep(s/1000.0)




def send_data_nmt(args, reader):
    pool = ThreadPoolExecutor(5000)
    data = "[{'input_sentence': 'Hello world! My name is John. I live on the West coast.'}]"

    for row in reader:
        if reader.line_num > args.timeout:
            break

        num = int(int(row['tweets']) / 2)
        lam = (60 * 1000.0) / num
        samples = np.random.poisson(lam, num)
        print(f'line: {reader.line_num}; sample_number: {num}')
        for s in samples:
            pool.submit(sender, data)
            # sender(data)
            # print(f'Send request after {s} ms')
            time.sleep(s/1000.0)

def get_mx_data():
    return "[{'input_sentence': 'on the exchange floor as soon as ual stopped trading we <unk> for a panic said one top floor trader'}]"

def send_data_mx(args, reader):
    pool = ThreadPoolExecutor(5000)
    data = get_mx_data()

    for row in reader:
        if reader.line_num > args.timeout:
            break

        num = int(row['tweets']) * 3
        lam = (60 * 1000.0) / num
        samples = np.random.poisson(lam, num)
        print(f'line: {reader.line_num}; sample_number: {num}')
        for s in samples:
            pool.submit(sender, data)
            # sender(data)
            # print(f'Send request after {s} ms')
            time.sleep(s/1000.0)


def send_fixed_data(args):
    pool = ThreadPoolExecutor(3000)
    data = get_data()
    for _ in range(20):
        num = 3000
        lam = (60 * 1000.0) / num
        samples = np.random.poisson(lam, num)
        for s in samples:
            pool.submit(sender, data)
            time.sleep(s/1000.0)

def send_stress_test_data(args):
    pool = ThreadPoolExecutor(3000)
    data = get_mx_data()
    burst_rate = args.burst

    for i in range(30):
        num = 5000 * (1 + burst_rate/2) if i == 13 else 5000
        num = 5000 * (1 + burst_rate) if i >= 14 else 5000
        lam = (60 * 1000.0) / num
        samples = np.random.poisson(lam, int(num))
        for s in samples:
            pool.submit(sender, data)
            time.sleep(s/1000.0)



def send_tf_mmpp_data(args):
    pool = ThreadPoolExecutor(5000)
    # data = get_data()
    data = get_data()

    with open(f'{upper_folder}/workload/2map_interval.csv', 'r') as f:
        for row in f:
            interval = float(row) /2.0
            # print(interval)
            pool.submit(sender, data)
            time.sleep(interval)

def send_nmt_mmpp_data(args):
    pool = ThreadPoolExecutor(5000)
    # data = get_data()
    data = "[{'input_sentence': 'Hello world! My name is John. I live on the West coast.'}]"

    with open(f'{upper_folder}/workload/2map_interval.csv', 'r') as f:
        for row in f:
            interval = float(row)
            # print(interval)
            pool.submit(sender, data)
            time.sleep(interval)

def send_kr_mmpp_data(args):
    pool = ThreadPoolExecutor(5000)
    # data = get_data()
    data = get_kr_data()

    with open(f'{upper_folder}/workload/2map_interval.csv', 'r') as f:
        for row in f:
            interval = float(row)
            # print(interval)
            pool.submit(sender, data)
            time.sleep(interval)


def send_mx_mmpp_data(args):
    pool = ThreadPoolExecutor(5000)
    # data = get_data()
    data = get_mx_data()

    with open(f'{upper_folder}/workload/2map_interval.csv', 'r') as f:
        for row in f:
            interval = float(row) / 6.0
            # print(interval)
            pool.submit(sender, data)
            time.sleep(interval)
            


if __name__ == '__main__':
    args = get_args()
    # send_stress_test_data(args)
    #send_data_nmt(args)
    send_mx_mmpp_data(args)
    # with open(f'{upper_folder}/workload/tweet_load.csv', 'r') as f:
    #     reader = csv.DictReader(f)
    #     send_data_nmt(args, reader)
        # send_data(args, reader)
        # send_data_mx(args, reader)
        # send_data_kr(args, reader)