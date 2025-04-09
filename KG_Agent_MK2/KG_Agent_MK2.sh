#!/bin/bash

# sourve .env and venv
source /p/project1/hai_kg-rag-thesis/scripts/KG_Agent_MK2/.env
source /p/project1/hai_kg-rag-thesis/env/KG_Agent_MK2_venv/bin/activate

set -e  # Exit script if any command fails

# Logging Setup
LOG_DATE=$(date +"%d-%m-%Y")

# Find the highest existing index in logs/$LOG_DATE
LOG_BASE="logs/$LOG_DATE/KG_Agent_MK2"
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

mkdir -p "$LOG_DIR/misc/meta"
mkdir -p "$TEMP_OUTPUT_DIR"

exec > >(tee -a "$LOG_DIR/job.out") 2> >(tee -a "$LOG_DIR/job.err" >&2)

# Extended Logging for `track_files.py`
python "track_files.py" \
  --root-dir "./" --output "$LOG_DIR/misc/meta" \
  > "$LOG_DIR/track_files.log" 2> "$LOG_DIR/track_files.err"

if [ $? -ne 0 ]; then
    echo "ERROR: File tracking failed. Check logs: $LOG_DIR/track_files.err" | tee -a "$LOG_DIR/track_files.log"
    exit 1
fi
echo "File tracking completed successfully!" | tee -a "$LOG_DIR/track_files.log"
echo ""  # Blank line for separation

echo "🔧 Running KG_Agent_MK2.sh with the following parameters:"
echo "NUM_QUESTIONS           = $NUM_QUESTIONS" #if set to 0, it will process all questions
echo "MAX_CONSECUTIVE_RETRIES = $MAX_CONSECUTIVE_RETRIES"
echo "LOG_DIR                 = $LOG_DIR"
echo "TEMP_OUTPUT_DIR         = $TEMP_OUTPUT_DIR"
echo "LLM_PROVIDER            = $LLM_PROVIDER"
echo "API_KEY                 = ${API_KEY:0:10}... (truncated)"
echo "MODEL_ENTITY_EXTRACTION = $MODEL_ENTITY_EXTRACTION"
echo "MODEL_SPARQL_GENERATION = $MODEL_SPARQL_GENERATION"
echo "BASE_JSON_FILE          = $BASE_JSON_FILE"
echo "SYSTEM_PROMPT_PATH      = $SYSTEM_PROMPT_PATH"
echo "IS_LOCAL_GRAPH          = $IS_LOCAL_GRAPH"
echo "LOCAL_GRAPH_LOCATION    = $LOCAL_GRAPH_LOCATION"
echo "SPARQL_ENDPOINT_URL     = $SPARQL_ENDPOINT_URL"
echo "ANNOTATION              = $ANNOTATION"
echo ""  # Blank line for separation

set -x  # Enable debugging

python ./extract_entity_list.py \
  --input_file $BASE_JSON_FILE \
  --output_file "$TEMP_OUTPUT_DIR/extracted_nlq_sparql_with_entities.json" \
  --api_key $API_KEY_ENTITY_EXTRACTION \
  --num_questions $NUM_QUESTIONS \
  --model $MODEL_ENTITY_EXTRACTION \
  --llm_provider $LLM_PROVIDER_ENTITY_EXTRACTION \
  --max_tokens $MAX_TOKENS_ENTITY_EXTRACTION \
  --temperature $TEMPERATURE_ENTITY_EXTRACTION \
  --is_local_graph $IS_LOCAL_GRAPH \
  --system_prompt_path $SYSTEM_PROMPT_ENTITY_EXTRACTION \
  > "$LOG_DIR/extract_entity_list.out" 2> "$LOG_DIR/extract_entity_list.err"
echo ""  # Blank line for separation


python generate_shape.py \
  --shape_output_path "$TEMP_OUTPUT_DIR/shapes" \
  --target_json_file "$TEMP_OUTPUT_DIR/extracted_nlq_sparql_with_entities.json" \
  --is_local_graph $IS_LOCAL_GRAPH \
  --local_graph_location $LOCAL_GRAPH_LOCATION \
  --annotation $ANNOTATION \
  > "$LOG_DIR/generate_shape.out" 2> "$LOG_DIR/generate_shape.err"
echo ""  # Blank line for separation

  # Generate SPARQL with LLM
  python call_llm_api.py \
    --json_path $TEMP_OUTPUT_DIR/extracted_nlq_sparql_with_entities.json \
    --system_prompt_path $SYSTEM_PROMPT_SPARQL_GENERATION \
    --shape_path $TEMP_OUTPUT_DIR/shapes \
    --model $MODEL_SPARQL_GENERATION \
    --api_key $API_KEY_SPARQL_GENERATION \
    --max_tokens $MAX_TOKENS_SPARQL_GENERATION \
    --temperature $TEMPERATURE_SPARQL_GENERATION \
    --llm_provider $LLM_PROVIDER_SPARQL_GENERATION \
    --is_local_graph $IS_LOCAL_GRAPH \
    --max_retries $MAX_CONSECUTIVE_RETRIES \
    --sparql_endpoint_url $SPARQL_ENDPOINT_URL \
    --local_graph_path $LOCAL_GRAPH_LOCATION \
  > "$LOG_DIR/call_llm_api.out" 2> "$LOG_DIR/call_llm_api.err"
echo ""  # Blank line for separation

python call_sparql_endpoint.py \
  --sparql_endpoint_url "https://query.wikidata.org/sparql" \
  --json_path "$TEMP_OUTPUT_DIR/extracted_nlq_sparql_with_entities.json" \
  --is_local_graph $IS_LOCAL_GRAPH \
  --local_graph_location $LOCAL_GRAPH_LOCATION \
  > "$LOG_DIR/call_sparql_endpoint.out" 2> "$LOG_DIR/call_sparql_endpoint.err"
echo ""  # Blank line for separation

python verify_sparql.py \
 --json_path "$TEMP_OUTPUT_DIR/extracted_nlq_sparql_with_entities.json" \
  > "$LOG_DIR/verify_sparql.out" 2> "$LOG_DIR/verify_sparql.err"