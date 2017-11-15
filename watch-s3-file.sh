#!/bin/bash
set -e

program=$0

usage(){
    cat << EOF
Usage: $program <params>
Parameters:
    --s3-url <s3-url>                               - S3 file to be watched and fetched
    --file-name <destination-file>                  - Absolute destination filename
    [--cache-dir <cache-dir>]                       - Cached directory (Default: /tmp/.s3.cache)
    [--polling-period <polling-period-in-seconds>]  - Polling in seconds (Default 20)
    [--command <command-to-execute-on-change>]      - Command to be executed if the file was changed
    [--first-time-execute]                          - Should execute command on first time (Default: false)
    [--skip-watch]                                  - Skip watch the file, only fetch it once (Default: false)
    [--debug]                                       - Log debug (Default: false)
    
EOF
    exit 1
}

log(){
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

debug(){
    [[ "$DEBUG" == "YES" ]] && log "$1"
}


fetch_config(){
    debug "Fetching ${S3_URL} to ${S3_SYNC_DIR}"
    aws --region=${S3_BUCKET_LOCATION} s3 cp ${S3_URL} ${S3_SYNC_DIR}/${FILE_BASENAME} --quiet
    debug "Calulating checksum of ${S3_SYNC_DIR}/${FILE_BASENAME}"
    MD5_CHECKSUM=$(md5 -q ${S3_SYNC_DIR}/${FILE_BASENAME})
    debug "MD5_CHECKSUM = $MD5_CHECKSUM"
    if [ -f ${S3_SYNC_DIR}/${FILE_BASENAME}.md5 ]; then
        ORIG_MD5_CHECKSUM=$(cat ${S3_SYNC_DIR}/${FILE_BASENAME}.md5)
    else
        ORIG_MD5_CHECKSUM=''
    fi
    debug "ORIG_MD5_CHECKSUM = $ORIG_MD5_CHECKSUM"
    md5 -q ${S3_SYNC_DIR}/${FILE_BASENAME} > ${S3_SYNC_DIR}/${FILE_BASENAME}.md5
    if [ "$ORIG_MD5_CHECKSUM" != "$MD5_CHECKSUM" ]; then
        cp ${S3_SYNC_DIR}/${FILE_BASENAME} ${OUT_FILENAME}
        return 30
    fi
    return 0
}

update_config(){
    if [ -n "$COMMAND" ]; then
        log "Running $COMMAND."
        eval "$COMMAND"
        log "Running $COMMAND. Done..."
    fi
}

parseArgs(){
    POSITIONAL=()
    while [[ $# -gt 0 ]]
    do
    key="$1"

    case "$key" in
        -u|--s3-url)
        S3_URL="$2"
        shift # past argument
        shift # past value
        ;;
        
        -d|--cache-dir)
        S3_SYNC_DIR="$2"
        shift # past argument
        shift # past value
        ;;
        
        -p|--polling-period)
        S3_POLLING_PERIOD="$2"
        shift # past argument
        shift # past value
        ;;
        
        -f|--filename)
        OUT_FILENAME="$2"
        shift # past argument
        shift # past value
        ;;

        -c|--command)
        COMMAND="$2"
        shift # past argument
        shift # past value
        ;;

        --skip-watch)
        SKIP_WATCH=YES
        shift # past argument
        ;;
        
        --debug)
        DEBUG=YES
        shift # past argument
        ;;
        *)    # unknown option
        POSITIONAL+=("$1") # save it in an array for later
        shift # past argument
        ;;
    esac
    done
    set -- "${POSITIONAL[@]}" # restore positional parameters

    if [[ -z "$S3_URL" ]]; then 
        (>&2 echo "Error: --s3-url must be provided")
        usage
    fi
    if [[ -z "$OUT_FILENAME" ]]; then 
        (>&2 echo "Error: --filename must be provided")
        usage
    fi

    S3_POLLING_PERIOD=${S3_POLLING_PERIOD:-20}
    S3_SYNC_DIR=${S3_SYNC_DIR:-/tmp/.s3.cache}
    S3_BUCKET=$(echo $S3_URL | sed 's/s3:\/\///g' | cut -d'/' -f 1)
    S3_BUCKET_LOCATION="$(aws s3api get-bucket-location --bucket ${S3_BUCKET} --output text)"
    FILE_BASENAME=$(basename $OUT_FILENAME)
}

parseArgs "$@"
log "$program started"
log "S3_URL = $S3_URL"
log "S3_SYNC_DIR = $S3_SYNC_DIR"
log "S3_POLLING_PERIOD = $S3_POLLING_PERIOD"
log "OUT_FILENAME = $OUT_FILENAME"
log "COMMAND = $COMMAND"
log "SKIP_WATCH = $SKIP_WATCH"
log "DEBUG = $DEBUG"

mkdir -p $S3_SYNC_DIR

log "Fetching $OUT_FILENAME for the first time..."
fetch_config && FETCH_RES=$? || FETCH_RES=$?

if [ -n "$SKIP_WATCH" ]; then
    log "SKIP_WATCH = YES, Going out..."
    exit 0
fi

log "Entering watch loop"
while true; do
    sleep $S3_POLLING_PERIOD
    fetch_config && RES=$? || RES=$?
    if [ "$RES" == 30 ]; then
        log "Checksum was changed, executing command"
        update_config
    fi
done
