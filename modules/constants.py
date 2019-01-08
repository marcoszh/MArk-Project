# coding: utf-8


UPPER_LATENCY_BOUND = 200
SLA_BOUND = 0.02

HANDLE_SIZE = 8

#batch size config
HANDLE_SIZE_P2 = 8
HANDLE_SIZE_C5=1
HANDLE_SIZE_C5X = 2
HANDLE_SIZE_C52X = 2
HANDLE_SIZE_C54X = 2

#proactive scheduler update interval
UPDATER_INTERVAL = 600

SERVING_PORT = 7001
API_PORT = 8301

API_TIMEOUT = 10.0

# use weighted load balancer
DEFAULT_BALANCER = 'weight'

# MangoDB is used to manage instance info
DB_HOST = 'localhost'
# REDIS_PORT = 6379
MONGO_PORT = 27017

# DB configs
ON_DEMAND_PRIZE_DB = 'on_demand'
SPOT_PRIZE_DB = 'spot'
AWS_DB = 'aws'
PRE_AWS_DB = 'pre_aws'
INS_DB = 'instance'
BACKUP_DB = 'back_up'
DEMAND_AWS_DB = 'demand_aws'
PRE_DEMAND_AWS_DB = 'pre_demand_aws'

SPOT_PRIZE_URL = 'http://spot-price.s3.amazonaws.com/spot.js'
ON_DEMAND_PRIZE_URL = 'http://a0.awsstatic.com/pricing/1/ec2/linux-od.js'

# the data amount to warm up predictor, the re-schedule period(seconds)
PREDICTOR_PARAM = [5, 60]

# the arrival rate smaple window
PREDICTOR_WINDOW = 5

SECURITY_GROUPS = {
    'us-west-2': ['sg-xxx'],
    'us-west-1': ['sg-xxx'],
    'us-east-1': ['sg-xxx']
}
KEYS = {
    'us-east-1': 'xxx',
    'us-west-1': 'xxx',
    'us-west-2': 'xxx'
}

# which market to use
INS_SOURCE = 'spot'

# which model to serve
MODEL = 'tf'

# AMIs for each model
AMIS_TF = {
    'us-east-1': {'CPU': 'ami-xxx', 'GPU': 'ami-xxx'}
}
AMIS_KR = {
    'us-east-1': {'CPU': 'ami-xxx', 'GPU': 'ami-xxx'}
}
AMIS_MX = {
    'us-east-1': {'CPU': 'ami-xxx'}
}
AMIS_NMT = {
    'us-east-1': {'CPU': 'ami-xxx', 'GPU': 'ami-xxx'}
}

AMIS_MODEL = {
    'kr': AMIS_KR,
    'tf': AMIS_TF,
    'mx': AMIS_MX,
    'nmt': AMIS_NMT
}

AMIS = AMIS_MODEL[MODEL]

# the instances to use in each model
AllIndexType = {
    'tf': ['c5.large', 'c5.xlarge', 'c5.2xlarge', 'c5.4xlarge', 'p2.xlarge'],
    'kr': ['c5.xlarge', 'c5.2xlarge', 'c5.4xlarge', 'p2.xlarge'],
    'mx': ['c5.xlarge', 'c5.2xlarge', 'c5.4xlarge', 'p2.xlarge'],
    'nmt': ['c5.xlarge', 'c5.2xlarge', 'c5.4xlarge', 'p2.xlarge']
}

# the profiled capacity for all instances (r/m)
AllCapacity = {
    'tf': [284, 490, 771, 1080, 415 * HANDLE_SIZE ],
    'kr': [85, 135, 187, 95 * HANDLE_SIZE ],
    'mx': [3100, 1, 1, 1],
    'nmt': [40 * HANDLE_SIZE_C5X, 54 * HANDLE_SIZE_C52X, 75 * HANDLE_SIZE_C54X, 80 * HANDLE_SIZE_P2]
}

# load balancer weight
AllWeight = {
    'tf': [284, 490, 771, 1080, 415],
    'kr': [85, 135, 187, 95],
    'mx': [3100, 1, 1, 1],
    'nmt': [40, 54, 75, 80]
}

IndexType = AllIndexType[MODEL]
Capacity = AllCapacity[MODEL]
Weights = AllWeight[MODEL]

Instance_Weights = {}
[ Instance_Weights.update({t: w}) for t, w in zip(IndexType, Weights) ]

# AWS credentials
DEFAULT_REGION = 'us-east-1'
CREDENTIALS = {
    'aws_access_key_id' : 'xxx',
    'aws_secret_access_key' : 'xxx'
}

# model deploy cmd
TF_DEPLOY_CMD ={
    'CPU': f'nohup /home/ubuntu/serving/bazel-bin/tensorflow_serving/model_servers/tensorflow_model_server --port=8500 \
            --rest_api_port={API_PORT} --model_name=inception --model_base_path=/home/ubuntu/model > server.log 2>&1 &',
    'GPU': f'nohup docker run -p {API_PORT}:{API_PORT} --runtime=nvidia \
            --mount type=bind,source=/home/ubuntu/mymodel/,target=/models \
            -e MODEL_NAME=inception -t \
            --entrypoint tensorflow_model_server \
            tensorflow/serving:latest-gpu --rest_api_port={API_PORT} --model_name=inception --model_base_path=/models/inception \
            --enable_batching=false --rest_api_timeout_in_ms=10000 > server.log 2>&1 &'
}


ITEM_DELIMITER = ','
