import asyncio
import json
import logging
import threading
import time
from base64 import b64encode
from collections import deque

import requests
from .constants import *
from . import utils

TYPE_CONFING = {
    'c5.large' : 'nginxc5large.conf', 
    'c5.xlarge' : 'nginxc5xlarge.conf',
    'c5.2xlarge' : 'nginxc52xlarge.conf', 
    'c5.4xlarge' : 'nginxc54xlarge.conf',
    'p2.xlarge8' : 'nginxp2xlarge_8.conf',
    'p2.xlarge16' : 'nginxp2xlarge_16.conf'
}

KR_CONFING = {
    'c5.xlarge' : 'nginx_c5xlarge.conf',
    'c5.2xlarge' : 'nginx_c52xlarge.conf',
    'c5.4xlarge' : 'nginx_c54xlarge.conf'
}

NMT_CONFING = {
    'c5.xlarge' : 'nginx_c5xlarge.conf',
    'c5.2xlarge' : 'nginx_c52xlarge.conf',
    'c5.4xlarge' : 'nginx_c54xlarge.conf'
}

class _ModelSource():
    def get_request(self, data, ip):
        pass

    def setup_config(self, ins, region, typ):
        pass

    def get_lambda_req(self):
        return 'https://example'

    def collect_result(self, res):
        return res['predictions']

class MXNetSource(_ModelSource):
    def get_request(self, data, ip):
        url = f'http://{ip}:8080/invocations'
   
        return dct

    def setup_config(self, ins, region, typ):
        for i in ins:
            ses = utils.get_session(i.ip)
            utils.check_command(ses, 'docker run -p 8080:8080 mxnet-lstm-local &> /dev/null &')

        test_data = "[{'input_sentence': 'on the exchange floor as soon as ual stopped trading we <unk> for a panic said one top floor trader'}]"
        for i in ins:
            while True:
                try:
                    start_time = utils.now()
                    response = requests.post(url=f'http://{i.ip}:8080/invocations',data={'data': test_data})
                    if response.status_code == 200:
                        latency = utils.gap_time(start_time)
                        if latency <= 30:
                            logging.info(f'Successful warm up for ip: {i.ip}; Latency: {latency}')
                            break
                        else:
                            logging.info(f'Warming up for ip: {i.ip}; Latency: {latency}')
                    else:
                        logging.info(f'Warming up for ip: {i.ip}')
                except requests.exceptions.RequestException as e:
                    print(f'Serving request exception for ip: {i.ip}')
                time.sleep(10)

    def get_lambda_req(self):
        return 'https://example'

    def collect_result(self, res):
        return [res['prediction']]

class TensorFlowSource(_ModelSource):

    def __init__(self):
        test_file = f'{utils.upper_folder}/resources/test.jpg'
        with open(test_file, 'rb') as f:
            raw_data = f.read()
            base64_bytes = b64encode(raw_data)
            self.test_data = base64_bytes.decode('utf-8')

    def get_request(self, data, ip):
      
        dct = {'url': url, 'headers': headers, 'data': data, 'timeout': 2}
        return dct

    def setup_config(self, ins, region, typ):
        self. _start_nginx(ins)
        logging.info('Nginx started')
        cmd = TF_DEPLOY_CMD['GPU'] if typ.startswith('p2') else TF_DEPLOY_CMD['CPU']
        self._deploy_model(region, [ i.ip for i in ins ], cmd)
        logging.info('Models are Deployed now')

        image_data = [{ "b64": self.test_data},]

        if typ.startswith('p2'):
            image_data = image_data * HANDLE_SIZE_P2

        for i in ins:
            while True:
                try:
                    response = requests.post(url=f'http://{i.ip}:8080/invocations', 
                                            headers = {"Content-type": "application/json"},
                                            data=json.dumps({ 
                                                'signature_name':'predict_images',
                                                'instances': image_data
                                            }),
                                            timeout=3)
                    if response.status_code == 200:
                        logging.info(f'Successful warm up for ip: {i.ip}')
                        break
                    logging.info(f'Warming up for ip: {i.ip}')
                except requests.exceptions.RequestException as e:
                    print(e)
                time.sleep(5)

    def get_lambda_req(self):
        return 'https://example'

    def _start_nginx(self, instances):
        for i in instances:
            nginx_conf = ''
            if i.typ.startswith('p2'):
                nginx_conf = TYPE_CONFING[f'{i.typ}{HANDLE_SIZE}']
            else:
                nginx_conf = TYPE_CONFING[i.typ] if i.typ in TYPE_CONFING else TYPE_CONFING['c5.large']
            ses = utils.get_session(i.ip)
            utils.check_command(ses, f'sudo cp /etc/nginx/{nginx_conf} /etc/nginx/nginx.conf && sudo systemctl restart nginx')
        
    def _deploy_model(self, region, ips, cmd):
        return all([utils.check_command(utils.get_session(i), cmd, debug=True) for i in ips])

class KerasSource(_ModelSource):

    def __init__(self):
        test_file = f'{utils.upper_folder}/keras/SageMaker/cat.jpg'
        with open(test_file, "rb") as f:
            raw_data = f.read()
            self.test_data = raw_data

    def get_request(self, data, ip):
        
        url = f'http://{ip}:8301/invocations'
        files = payload

        dct = {'url': url, 'data': files, 'timeout': 2.5}
        return dct

    def _get_data(self):
        test_file = f'{utils.upper_folder}/keras/SageMaker/cat.jpg'
        with open(test_file, "rb") as f:
            raw_data = f.read()
            return raw_data

    def setup_config(self, ins, region, typ):
        for i in ins:
            ses = utils.get_session(i.ip)
            utils.check_command(ses, 'sudo service supervisor stop && sudo service nginx stop')

            if i.typ.startswith('c5'):
                nginx_conf = KR_CONFING[i.typ]
                utils.check_command(ses, f'sudo cp /etc/nginx/{nginx_conf} /etc/nginx/nginx.conf') 
                
            utils.check_command(ses, 'sudo supervisord -c /etc/supervisor/conf.d/supervisord.conf -n &> /dev/null &')

        test_file = f'{utils.upper_folder}/keras/SageMaker/cat.jpg'
        with open(test_file, "rb") as f:
            raw_data = f.read()
            payload = {"image": raw_data}
            for i in ins:
                while True:
                    try:
                        response = requests.post(url=f'http://{i.ip}:8301/invocations',files=payload, timeout=3)
                        if response.status_code == 200:
                            logging.info(f'Successful warm up for ip: {i.ip}')
                            break
                        logging.info(f'Warming up for ip: {i.ip}')
                    except requests.exceptions.RequestException as e:
                        print(e)
                    time.sleep(5)

    def get_lambda_req(self):
        return 'https://example'


class NMTSource(_ModelSource):
    def get_request(self, data, ip):
        url = f'http://{ip}:8301/invocations'
        
        return dct

    def setup_config(self, ins, region, typ):
        for i in ins:
            ses = utils.get_session(i.ip)
            utils.check_command(ses, 'sudo service supervisor stop && sudo service nginx stop')

            if i.typ.startswith('c5'):
                nginx_conf = KR_CONFING[i.typ]
                utils.check_command(ses, f'sudo cp /etc/nginx/{nginx_conf} /etc/nginx/nginx.conf') 
                
            utils.check_command(ses, 'sudo supervisord -c /etc/supervisor/conf.d/supervisord.conf -n &> /dev/null &')

        for i in ins:
            while True:
                try:
                    response = requests.post(url=f'http://{i.ip}:8301/invocations',
                                                headers = {"Content-type": "application/json"},
                                                data=json.dumps({ 
                                                    'instances': ["hellow"]
                                                }),
                                                timeout=3)
                    if response.status_code == 200:
                        logging.info(f'Successful warm up for ip: {i.ip}')
                        break
                    logging.info(f'Warming up for ip: {i.ip}')
                except requests.exceptions.RequestException as e:
                    print(e)
                time.sleep(5)

    def get_lambda_req(self):
        return 'exaple'


all_source = {
    'kr': KerasSource(),
    'tf': TensorFlowSource(),
    'mx': MXNetSource(),
    'nmt': NMTSource()
}

mdl_source = all_source[MODEL]