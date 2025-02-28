#!/bin/bash

# sourve .env and venv
source /p/project1/hai_kg-rag-thesis/scripts/KG_Agent_MK1/.env
source /p/project1/hai_kg-rag-thesis/env/llamacpp/bin/activate

# Logging Setup
LOG_DATE=$(date +"%d-%m-%Y")

# Find the highest existing index in logs/$LOG_DATE
LOG_BASE="logs/$LOG_DATE/KG_Agent_MK1"
LAST_INDEX=$(ls -d ${LOG_BASE}_* 2>/dev/null | awk -F'_' '{print $NF}' | sort -n | tail -1)

# Increment index or start from 1
if [[ -z "$LAST_INDEX" ]]; then
    RUN_INDEX=1
else
    RUN_INDEX=$((LAST_INDEX + 1))
fi

# Define indexed log directory
LOG_DIR="${LOG_BASE}_${RUN_INDEX}"
TEMP_OUTPUT_DIR="$LOG_DIR/misc/temp"

# Path to LLM-generated SPARQL query
SPARQL_QUERY_FILE="$TEMP_OUTPUT_DIR/llm_response.txt"
SPARQL_OUTPUT_FILE="$TEMP_OUTPUT_DIR/SPARQL_response.csv"

mkdir -p "$LOG_DIR/misc/meta"
mkdir -p "$TEMP_OUTPUT_DIR"

echo "LOG_DIR: $LOG_DIR"
echo "TEMP_OUTPUT_DIR: $TEMP_OUTPUT_DIR"

exec > >(tee -a "$LOG_DIR/job.out") 2> >(tee -a "$LOG_DIR/job.err" >&2)
set -x  # Enable debugging


# Extended Logging for `track_files.py`
echo "Starting file tracking..." | tee -a "$LOG_DIR/track_files.log"
python "track_files.py" \
  --root-dir "./" --output "$LOG_DIR/misc/meta" \
  > "$LOG_DIR/track_files.out" 2> "$LOG_DIR/track_files.err"


if [ $? -ne 0 ]; then
    echo "ERROR: File tracking failed. Check logs: $LOG_DIR/track_files.err" | tee -a "$LOG_DIR/track_files.log"
    exit 1
fi
echo "File tracking completed successfully!" | tee -a "$LOG_DIR/track_files.log"

# Extract shacl and shex shapes from a given turtle file (TURTLE_INPUT_PATH) and save the result to the output path (SHAPE_OUTPUT_PATH)
python extract_shapes.py \
  --turtle_input_path "$TURTLE_INPUT_PATH" \
  --shape_output_path "$SHAPE_OUTPUT_PATH" \
  > "$LOG_DIR/extract_shapes.out" 2> "$LOG_DIR/extract_shapes.err"

# Define paths
SYSTEM_PROMPT_PATH="system_prompt.txt"

# Extract the base filename from TURTLE_INPUT_PATH (removes directory and .ttl extension)
BASE_FILENAME=$(basename "$TURTLE_INPUT_PATH" .ttl)

# Determine shape path dynamically based on USE_SHAPE
if [ "$USE_SHAPE" == "shacl" ]; then
    SHAPE_PATH="$SHAPE_OUTPUT_PATH/${BASE_FILENAME}_shacl.ttl"
elif [ "$USE_SHAPE" == "shex" ]; then
    SHAPE_PATH="$SHAPE_OUTPUT_PATH/${BASE_FILENAME}.shex"
else
    echo "❌ ERROR: USE_SHAPE must be either 'shacl' or 'shex'" | tee -a "$LOG_DIR/call_llm_api.log"
    exit 1
fi

# Ensure the shape file exists
if [ ! -f "$SHAPE_PATH" ]; then
    echo "❌ ERROR: Shape file not found: $SHAPE_PATH" | tee -a "$LOG_DIR/call_llm_api.log"
    exit 1
fi

# Call LLM API script with dynamically set SHAPE_PATH
echo "Calling LLM API..." | tee -a "$LOG_DIR/call_llm_api.log"
python call_llm_api.py \
  --use_chatgpt \
  --model $MODEL \
  --openai_api_key $OPENAI_API_KEY \
  --user_prompt_path $USER_PROMPT_PATH \
  --system_prompt_path $SYSTEM_PROMPT_PATH \
  --shape_path $SHAPE_PATH \
  --output_dir $TEMP_OUTPUT_DIR \
  --max_tokens $MAX_TOKENS \
  --temperature $TEMPERATURE \
  > "$LOG_DIR/call_llm_api.out" 2> "$LOG_DIR/call_llm_api.err"

# Extract the first line of the response to check for errors
API_RESPONSE=$(head -n 1 "$LOG_DIR/call_llm_api.err")

# Check if Python command failed
if [ $? -ne 0 ]; then
    echo "ERROR: LLM API script execution failed. Check logs: $LOG_DIR/call_llm_api.err" | tee -a "$LOG_DIR/call_llm_api.log"
    exit 1

fi

# Check if the API response contains an error
if echo "$API_RESPONSE" | grep -qi "error"; then
    echo "ERROR: LLM API returned an error: $API_RESPONSE" | tee -a "$LOG_DIR/call_llm_api.log"
fi

echo "LLM API call completed successfully!" | tee -a "$LOG_DIR/call_llm_api.log"

echo "Waiting for SPARQL query file: $SPARQL_QUERY_FILE"

SPARQL_VERIFIER_WAITED=0

while [ ! -f "$SPARQL_QUERY_FILE" ]; do
    if [ "$SPARQL_VERIFIER_WAITED" -ge "$SPARQL_VERIFIER_MAX_WAIT_TIME" ]; then
        echo "ERROR: Timed out waiting for SPARQL query file: $SPARQL_QUERY_FILE"
        exit 1
    fi
    sleep "$SPARQL_VERIFIER_SLEEP_INTERVAL"
    ((SPARQL_VERIFIER_WAITED += SPARQL_VERIFIER_SLEEP_INTERVAL))  # Fix arithmetic error
done

# Run SPARQL verifier, that does some sanity checks on the query and executes it against $SPARQL_ENDPOINT_URL
echo "Verifying and executing SPARQL query..." | tee -a "$LOG_DIR/sparql_verifier.log"
python "sparql_verifier.py" \
  --sparql_endpoint_url "$SPARQL_ENDPOINT_URL" \
  --ttl_file "$TURTLE_INPUT_PATH" \
  --response_file "$SPARQL_QUERY_FILE" \
  --output_dir "$TEMP_OUTPUT_DIR" \
  > "$LOG_DIR/sparql_verifier.out" 2> "$LOG_DIR/sparql_verifier.err"

if [ $? -ne 0 ]; then
    echo "ERROR: SPARQL verification failed. Check logs: $LOG_DIR/sparql_verifier.err" | tee -a "$LOG_DIR/sparql_verifier.log"
fi
echo "SPARQL verification and execution completed successfully!" | tee -a "$LOG_DIR/sparql_verifier.log"
