#!/bin/sh

# Set error handling: exit on error, unset variable usage
set -eu

# Test if scanapi is installed
if ! command -v scanapi >/dev/null 2>&1; then
    printf '%s\n' "Error: required command 'scanapi' not found." >&2
    exit 1
fi

# Print usage information
usage() {
    cat << EOF
Usage: $(basename "$0") -i OPENAPI_PATH [-c CONFIG_PATH] [-l LOG_LEVEL]

Wrapper script to convert an OpenAPI document into ScanAPI format.

Required:
  -i  PATH    OpenAPI file path (JSON or YAML)

Options:
  -c  PATH    Configuration file path
  -l  LEVEL   Log level (DEBUG|INFO|WARNING|ERROR|CRITICAL)
  -h          Display this help message
EOF
    exit 1
}

# Initialize variables
openapi_path=""
config_path=""
log_level=""

# Parse flags using getopts
while getopts "i:c:l:h" opt; do
    case "$opt" in
        i) openapi_path="$OPTARG" ;;
        c) config_path="$OPTARG" ;;
        l) log_level="$OPTARG" ;;
        h) usage ;;
        ?) usage ;;
    esac
done

# --- 1. Validation: Required argument ---
if [ -z "$openapi_path" ]; then
    echo "Error: Missing required argument (-i OPENAPI_PATH)." >&2
    usage
fi

if [ ! -f "$openapi_path" ]; then
    echo "Error: OpenAPI file '$openapi_path' does not exist or is not a regular file." >&2
    exit 1
fi

# --- 2. Validation: Optional arguments ---

# Validate config path if provided
if [ -n "$config_path" ] && [ ! -f "$config_path" ]; then
    echo "Error: Config file '$config_path' does not exist." >&2
    exit 1
fi

# Validate log level if provided
if [ -n "$log_level" ]; then
    case "$log_level" in
        DEBUG|INFO|WARNING|ERROR|CRITICAL) ;;
        *)
            echo "Error: Invalid log level '$log_level'. Must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL." >&2
            exit 1
            ;;
    esac
fi

# --- 3. Build Command Array / String safely ---
set -- "$openapi_path"
set -- "$@" -o "scanapi.yaml"

if [ -n "$config_path" ]; then
    set -- "$@" -c "$config_path"
fi

if [ -n "$log_level" ]; then
    set -- "$@" -ll "$log_level"
fi

echo "Executing: scanapi from openapi $*"
scanapi from openapi "$@"

echo "Normalizing 'scanapi.yaml' Environment variable naming"
sed -Eri 's/(\$\{\w+)\.?(\w*\})/\U\1\2/g' scanapi.yaml

SCRIPT_PATH="$(dirname "$(realpath "$0")")"
SHARED_DIR="${SCRIPT_PATH}/kathara/shared"
TEST_VARS_PATH="${SHARED_DIR}/env/test_vars.env"

if [ ! -d "${SHARED_DIR}/env/" ]; then
    echo "Creating directory ${SHARED_DIR}/env/"
    mkdir -p "${SHARED_DIR}/env/"
fi

if [ ! -d "${SHARED_DIR}/results/logs/" ]; then
    echo "Creating directory ${SHARED_DIR}/results/logs/"
    mkdir -p "${SHARED_DIR}/results/logs/"
fi

echo "Creating '${TEST_VARS_PATH}'"
grep -Po '(?<=\$\{)\w+(?=\})' scanapi.yaml |\
    grep -vFx 'BASE_URL' |\
    sort -u |\
    sed 's/^/export /;s/$/=""/' > "${TEST_VARS_PATH}"
echo 'export BASE_DOMAIN="" # add here the same domain you used in the "zonefile_creator.py" script' >> "${TEST_VARS_PATH}"
echo 'export BASE_PROTO="https" # set here http or https for the requests' >> "${TEST_VARS_PATH}"

python3.12 "${SCRIPT_PATH}/add_host_header.py"
mv -v scanapi.yaml "${SHARED_DIR}/shared_data/scanapi.yaml"

echo "Done!"
