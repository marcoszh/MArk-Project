#!/usr/bin/env bash
set -euo pipefail

PAST_LOGS=/home/ubuntu/logs
mkdir -p ${PAST_LOGS}

get_log_dir_name() {
    NAME=v
    case $1 in
        mx) NAME=mx-v ;;
        tf) NAME=tf-v ;;
        kr) NAME=kr-v ;;
        al) NAME=al-v ;;
        # backup for interruption
        bc) NAME=bc-v ;;
        # stress test
        st) NAME=st-v ;;
        *) ;;
    esac
    INDEX=1
    while [ -d ${PAST_LOGS}/${NAME}${INDEX} ]
    do
        let INDEX++
    done

    echo ${PAST_LOGS}/${NAME}${INDEX}
}
