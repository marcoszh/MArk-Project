# coding: utf-8
import asyncio
import json
import logging
import threading
import time

from sanic import Sanic
from sanic.response import json

from . import utils
from . import query_processor
from . import scheduler
from .instance_source import ins_source
from .constants import *
# from .query_processor import processor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)

app = Sanic(__name__)
processor = query_processor.QueryProcessor()
sch = scheduler.Scheduler()


@app.route('/predict/<model_name>',  methods=['POST'])
async def predict(request, model_name):
    if request.method == 'POST':
        receive_time = utils.now()
        logging.info(f'Received request for model: {model_name}')

        typ = request.json['type']
        # use a general decoder to handle different types
        # data =  utils.decode_image(request.json['data']) if typ == 'image' else request.json['data']
        data = request.json['data']

        sch.record_request(model_name)
        res, typ, handel_time = await processor.send_query(model_name, receive_time, data)

        if (typ > 3):
            scheduler.Scheduler.failed_rate = scheduler.Scheduler.failed_rate * 0.999 + 0.001
        elif (handel_time > UPPER_LATENCY_BOUND):
            scheduler.Scheduler.failed_rate = scheduler.Scheduler.failed_rate * 0.999 +  0.001
        else:
            scheduler.Scheduler.failed_rate = scheduler.Scheduler.failed_rate * 0.999

        if sch.failed_rate > SLA_BOUND:
            sch.launch_standby('c5.xlarge', 1, model_name)
            scheduler.Scheduler.failed_rate = 0.0

        
        logging.info(f'Model: {model_name}; typ: {typ}; handel_time: {handel_time}; failed_rate: {scheduler.Scheduler.failed_rate}')
        return json({
            'res' : res,
            'latency' : handel_time
        })

@app.listener('after_server_start')
async def notify_server_started(app, loop):
    logging.info('enter after_server_start')
    processor.set_loop(loop)
    sch.set_loop(loop)
    ins_source.set_loop(loop)

def main(port_, tag_):
    scheduler.Tag = tag_
    app.run(port=port_, access_log=False)