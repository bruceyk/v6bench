#!/bin/sh

# shellcheck disable=SC1091
. /shared/env/test_vars.env
if [ -f /shared/env/credentials.env ]; then
    . /shared/env/credentials.env
fi

if timeout 300 sh -c "until nslookup ${BASE_DOMAIN} >/dev/null 2>&1; do sleep 1; done"; then
    echo "DNS server is up"
else
    echo "Timed out (300s) waiting for DNS server" >&2
fi


pip install "curlify2<2.0.0,>=1.0.1" --break-system-packages --no-cache-dir # workarround for version compatibility issue with scanapi
pip install scanapi==2.13.2 --break-system-packages --no-cache-dir
HOSTNAME="$(/usr/bin/hostname)"



URL_TEMPLATE="lab.${BASE_DOMAIN}"
for sdom in ${SDOMS}; do

    SKIP=""
    if [ "${sdom}" = "siit" ]; then
        # waiting to SIIT to startup: jool is built by DKMS on first boot, ~2 min
        if [ "${BASE_PROTO}" = "https" ]; then
            TEST_PORT=443
        else
            TEST_PORT=80
        fi

        if timeout 300 sh -c "until nc -z 192.168.46.1 ${TEST_PORT}; do sleep 1; done"; then
            echo "SIIT server is up"
        else
            echo "Timed out (300s) waiting for SIIT server; skipping the siit test" >&2
            SKIP=1
        fi
    elif [ "${HOSTNAME}" = "ipv6_nat64_client" ] && [ "${sdom}" = "ipv4" ]; then
        # waiting to NAT64 to startup: jool is built by DKMS on first boot, ~2 min
        if timeout 300 sh -c 'until ping -c 1 -W 1 64:ff9b::192.168.0.64 >/dev/null 2>&1; do sleep 1; done'; then
            echo "NAT64 server is up"
        else
            echo "Timed out (300s) waiting for NAT64 server; skipping the ipv4-over-NAT64 test" >&2
            SKIP=1
        fi
    fi

    # A test that runs against a translator that is not up yet reports
    # "[Errno 101] Network is unreachable" and writes no CSV row; skipping is honest.
    if [ -n "${SKIP}" ]; then
        continue
    fi

    export BASE_URL="${BASE_PROTO}://${sdom}.${URL_TEMPLATE}"
    OUTPUT_FILE="/shared/results/${HOSTNAME}-${sdom}-report.csv"
    scanapi run \
    -o "${OUTPUT_FILE}" \
    -t "/shared/shared_data/csv_template.jinja" \
    /shared/shared_data/scanapi.yaml > "/shared/results/logs/${HOSTNAME}-${sdom}.log" 2>&1

    sed -i "2,\$s/^/\"${HOSTNAME}\",/" "${OUTPUT_FILE}"
done
