set -x
# Start background system metrics collection using "sar" utility.
# Collection is optional and should not fail the tests if failed.

# Maximum collection time to limit disk grow (seconds)
AUTOKILL_SECONDS=7200
# Collection interval (seconds)
COLLECT_INTERVAL=1

yum -y install sysstat || exit 0

sar -o /var/log/sarstats.bin $COLLECT_INTERVAL >/dev/null 2>&1 &

pid=$!
count=$(ps -A | grep $pid | wc -l)

if [[ $count -gt 0 ]]; then
    (sleep $AUTOKILL_SECONDS && kill $pid) >/dev/null 2>&1 &
fi

exit 0
