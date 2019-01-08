set -euo pipefail

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Let the user start this script from anywhere in the filesystem.
source $DIR/utils.sh
ROOT=$DIR/..
cd $ROOT

PID_FILE=${ROOT}/debug/pid
STATE_FILE=${ROOT}/debug/state
LOG_DIR=${ROOT}/debug/logs
mkdir -p ${LOG_DIR}

UPDATER="True"
TAG=0

start_redis() {
    if ! type "redis-server" &> /dev/null; then
        echo -e "\nERROR:"
        echo -e "\tPlease install redis-server"
        exit 1
    fi

    # start Redis if it's not already running
    redis-server &> /dev/null &
    echo "Redis has started."
    sleep 1
}

flush_redis() {
    redis-cli flushall
}

start_mongodb() {

    mongod --dbpath /var/lib/mongodb &> /dev/null &
    echo "MongoDB has started."
    sleep 1
}

start_celery() {
    celery -A modules.aws_manager purge -f
    celery -A modules.aws_manager worker -l info >${LOG_DIR}/celery.log 2>&1 &
    CLRY_PID="$!"
    echo "Celery started! PID : $CLRY_PID"
    echo "$CLRY_PID " >> ${PID_FILE}
}

clean_logs() {
    if [ -d ${LOG_DIR} ]; then
        rm -rf ${LOG_DIR}
    fi
}

move_logs() {
    if [ -d ${LOG_DIR} ]; then
        LOG_PLACE=$(get_log_dir_name ${TAG})
        mkdir -p ${LOG_PLACE}
        mv ${LOG_DIR}/* ${LOG_PLACE}/
    fi
}

start_all() {
    if [ ! -f ${STATE_FILE} ]; then
      touch ${STATE_FILE}
    fi

    if [[ `cat ${STATE_FILE}` == "1" ]]; then
        echo "Continuum has started! "
        exit 1
    fi


    clean_logs
    mkdir -p ${LOG_DIR}

    start_redis
    flush_redis
    start_mongodb
    start_celery

    nohup python3 main.py --signal=0 --need-updater=${UPDATER} --tag=${TAG} > ${LOG_DIR}/serving.log 2>&1 &
    MAIN_PID="$!"
    echo "serving system started! PID : ${MAIN_PID}"
    echo "$MAIN_PID " >> ${PID_FILE}

    echo "1" > ${STATE_FILE}
}

launch() {
    start_mongodb
    python3 main.py --signal=1 --tag=${TAG} &
}

backup() {
    start_mongodb
    python3 main.py --signal=3 --tag=${TAG} &
}

stopback() {
    start_mongodb
    python3 main.py --signal=4 &
}

destroy() {
    start_mongodb
    python3 main.py --signal=2 &
}

send_request() {
    if [[ `cat ${STATE_FILE}` != "0" ]]; then
        nohup python3 experiment/request_sender.py --burst ${TAG} >${LOG_DIR}/sender.log 2>&1 &
        SENDER_PID="$!"
        echo "sender started! PID : ${SENDER_PID}"
        echo "$SENDER_PID " >> ${PID_FILE}
    else
        echo "system not running!"
    fi
}

sagemaker_request() {
    mkdir -p ${LOG_DIR}
    nohup python3 experiment/request_sender_post.py --burst ${TAG} >${LOG_DIR}/sender.log 2>&1 &
    SENDER_PID="$!"
    echo "sender started! PID : ${SENDER_PID}"
    echo "$SENDER_PID " >> ${PID_FILE}
}

stop_all() {
    if [[ ! -f ${STATE_FILE} ]]; then
        touch ${STATE_FILE}
    fi

    if [[ `cat ${STATE_FILE}` != "0" ]]; then
        kill_process
        echo "0" > ${STATE_FILE}
    else
        echo "system not running!"
    fi
}

kill_process(){
    for PID in `cat ${PID_FILE}`; do
        kill ${PID} || echo "${PID} does not exist."  # avoid non-zero return code
    done
    rm ${PID_FILE}
}

if [[ "$#" == 0 ]]; then
    echo "Usage: $0 start|stop|restart|clean"
    exit 1
else
    if [[ "$#" == 2 ]]; then  
        TAG=$2
    fi
    case $1 in
        start)                  start_all
                                ;;
        launch)                 launch
                                ;;
        backup)                 backup
                                ;;
        stopback)               stopback
                                ;;
        destroy)                destroy
                                ;;
        stop)                   stop_all
                                ;;
        restart)                stop_all
                                start_all
                                ;;
        send)                   send_request
                                ;;
        sage)                   sagemaker_request
                                ;;
        kill)                   kill_process
                                ;;
        move)                   move_logs
                                ;;
        clean )                 clean_logs
                                ;;
        * )                     echo "Usage: $0 start|stop|restart|clean"
    esac
fi