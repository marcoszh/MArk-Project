# MArk


## Instructions

You need to build your own AWS AMI that encapsulates the actual serving backend first to be able to run the experiments, the AMI must be able to be requested following the patterns in model_source.py. The easiest way to do so would be using a MXNet Model Server image.

### pre-launch instances
- modify the instance type and model type in constants.py (INS_SOURCE, MODEL)
- cmd : ./bin/start_server.sh launch $tag(optional,default 0)

### run experiment
- run frontend: ./bin/start_server.sh start $tag(optional,default 0)
- modify which sender to use in experiment/request_sender.py
- run request sending process: ./bin/start_server.sh send $burst(optional)

### collect log
- move log to assigned dir: ./bin/start_server.sh move $tag(prefix name of log dir, e.g. $tag-v1)
- parse latency from log: python3 experiment/parser/parse_latency.py $path_to_log_dir
