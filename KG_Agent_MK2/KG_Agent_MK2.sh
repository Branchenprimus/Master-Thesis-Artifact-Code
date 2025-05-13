#!/bin/bash

# sourve .env and venv
source /root/KG_Agent/KG_Agent_MK2/.env
source /root/KG_Agent/KG_Agent_MK2/venv/bin/activate

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
JSON_PATH_FILE_NAME="$TEMP_OUTPUT_DIR/experiment_nr_${RUN_INDEX}.json"

mkdir -p "$LOG_DIR/misc/meta"
mkdir -p $TEMP_OUTPUT_DIR

exec > >(tee -a "$LOG_DIR/6_job.out") 2> >(tee -a "$LOG_DIR/6_job.err" >&2)

# Extended Logging for `track_files.py`
python "track_files.py" \
  --root-dir "./" --output "$LOG_DIR/misc/meta" \
  > "$LOG_DIR/5_track_files.log" 2> "$LOG_DIR/5_track_files.err"

if [ $? -ne 0 ]; then
    echo "ERROR: File tracking failed. Check logs: $LOG_DIR/track_files.err" | tee -a "$LOG_DIR/track_files.log"
    exit 1
fi
echo "File tracking completed successfully!" | tee -a "$LOG_DIR/track_files.log"
echo ""  # Blank line for separation

echo "🔧 Running KG_Agent_MK2.sh with the following parameters:"
echo "NUM_QUESTIONS                         = $NUM_QUESTIONS" #if set to 0, it will process all questions
echo "MAX_CONSECUTIVE_RETRIES               = $MAX_CONSECUTIVE_RETRIES"
echo "LOG_DIR                               = $LOG_DIR"
echo "JSON_PATH_FILE_NAME                   = $JSON_PATH_FILE_NAME"
echo "TEMP_OUTPUT_DIR                       = $TEMP_OUTPUT_DIR"
echo "LLM_PROVIDER_SPARQL_GENERATION        = $LLM_PROVIDER_SPARQL_GENERATION"
echo "LLM_PROVIDER_ENTITY_EXTRACTION        = $LLM_PROVIDER_ENTITY_EXTRACTION"
echo "API_KEY                               = ${API_KEY:0:10}... (truncated)"
echo "MODEL_ENTITY_EXTRACTION               = $MODEL_ENTITY_EXTRACTION"
echo "MODEL_SPARQL_GENERATION               = $MODEL_SPARQL_GENERATION"
echo "SYSTEM_PROMPT_SPARQL_GENERATION       = $SYSTEM_PROMPT_SPARQL_GENERATION"
echo "SYSTEM_PROMPT_ENTITY_EXTRACTION       = $SYSTEM_PROMPT_ENTITY_EXTRACTION"
echo "BENCHMARK_DATASET                     = $BENCHMARK_DATASET"
echo "IS_LOCAL_GRAPH                        = $IS_LOCAL_GRAPH"
echo "LOCAL_GRAPH_LOCATION                  = $LOCAL_GRAPH_LOCATION"
echo "SPARQL_ENDPOINT_URL                   = $SPARQL_ENDPOINT_URL"
echo "EXISTING_SHAPE_PATH                   = $EXISTING_SHAPE_PATH"
echo "SHAPE_TYPE                            = $SHAPE_TYPE"
echo "DATASET_TYPE                          = $DATASET_TYPE"
echo "ANNOTATION                            = $ANNOTATION"
echo "BASELINE_RUN                          = $BASELINE_RUN"
echo ""  # Blank line for separation

set -x  # Enable debugging

python ./extract_entity_list.py \
  --benchmark_dataset $BENCHMARK_DATASET \
  --output_file $JSON_PATH_FILE_NAME \
  --api_key $API_KEY_ENTITY_EXTRACTION \
  --num_questions $NUM_QUESTIONS \
  --model $MODEL_ENTITY_EXTRACTION \
  --llm_provider $LLM_PROVIDER_ENTITY_EXTRACTION \
  --max_tokens $MAX_TOKENS_ENTITY_EXTRACTION \
  --temperature $TEMPERATURE_ENTITY_EXTRACTION \
  --is_local_graph $IS_LOCAL_GRAPH \
  --system_prompt_path $SYSTEM_PROMPT_ENTITY_EXTRACTION \
  --dataset_type $DATASET_TYPE \
  --sparql_endpoint_url $SPARQL_ENDPOINT_URL \
  --local_graph_location $LOCAL_GRAPH_LOCATION \
  --baseline_run $BASELINE_RUN \
  > "$LOG_DIR/1_extract_entity_list.out" 2> "$LOG_DIR/1_extract_entity_list.err"
echo ""  # Blank line for separation

python generate_shape.py \
  --shape_output_path "$TEMP_OUTPUT_DIR/shapes" \
  --target_json_file $JSON_PATH_FILE_NAME \
  --is_local_graph $IS_LOCAL_GRAPH \
  --local_graph_location $LOCAL_GRAPH_LOCATION \
  --shape_type $SHAPE_TYPE \
  --existing_shape_path $EXISTING_SHAPE_PATH \
  --dataset_type $DATASET_TYPE \
  --annotation $ANNOTATION \
  --sparql_endpoint_url $SPARQL_ENDPOINT_URL \
  --baseline_run $BASELINE_RUN \
  > "$LOG_DIR/2_generate_shape.out" 2> "$LOG_DIR/2_generate_shape.err"
echo ""  # Blank line for separation

  # Generate SPARQL with LLM
python call_llm_api.py \
  --json_path $JSON_PATH_FILE_NAME \
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
  --shape_type $SHAPE_TYPE \
  --dataset_type $DATASET_TYPE \
  --baseline_run $BASELINE_RUN \
  --system_prompt_path_baseline_run $SYSTEM_PROMPT_SPARQL_GENERATION_BASELINE_RUN \
  > "$LOG_DIR/3_call_llm_api.out" 2> "$LOG_DIR/3_call_llm_api.err"
echo ""  # Blank line for separation

python verify_sparql.py \
  --json_path $JSON_PATH_FILE_NAME \
  --sparql_endpoint_url $SPARQL_ENDPOINT_URL \
  --is_local_graph $IS_LOCAL_GRAPH \
  --local_graph_location $LOCAL_GRAPH_LOCATION \
  --num_questions $NUM_QUESTIONS \
  --max_retries $MAX_CONSECUTIVE_RETRIES \
  --log_dir $LOG_DIR \
  --llm_provider_sparql_generation $LLM_PROVIDER_SPARQL_GENERATION \
  --llm_provider_entity_extraction $LLM_PROVIDER_ENTITY_EXTRACTION \
  --model_entity_extraction $MODEL_ENTITY_EXTRACTION \
  --model_sparql_generation $MODEL_SPARQL_GENERATION \
  --benchmark_dataset $BENCHMARK_DATASET \
  --is_local_graph $IS_LOCAL_GRAPH \
  --local_graph_location $LOCAL_GRAPH_LOCATION \
  --sparql_endpoint_url $SPARQL_ENDPOINT_URL \
  --shape_type $SHAPE_TYPE \
  --dataset_type $DATASET_TYPE \
  --annotation $ANNOTATION \
  --baseline_run $BASELINE_RUN \
  --run_index $RUN_INDEX \
  > "$LOG_DIR/4_verify_sparql.out" 2> "$LOG_DIR/4_verify_sparql.err"
  
  # Copy results to Experiment_Results if NUM_QUESTIONS is 50
  if [ "$NUM_QUESTIONS" -eq 50 ]; then
    RESULTS_DIR="/root/KG_Agent/KG_Agent_MK2/Experiment_Results/$LOG_DIR"
    mkdir -p "$RESULTS_DIR"
    cp "$JSON_PATH_FILE_NAME" "$RESULTS_DIR/"
    SUMMARY_FILE="${JSON_PATH_FILE_NAME%.json}_summary.txt"
    if [ -f "$SUMMARY_FILE" ]; then
      cp "$SUMMARY_FILE" "$RESULTS_DIR/"
    fi
  fi

  python /root/KG_Agent/KG_Agent_MK2/util/convert_summaries_to_csv.py \
    --base "/root/KG_Agent/KG_Agent_MK2/Experiment_Results" \
    --output "/root/KG_Agent/KG_Agent_MK2/Experiment_Results/results.csv" \
    > "$LOG_DIR/7_convert_summaries_to_csv.out" 2> "$LOG_DIR/7_convert_summaries_to_csv.err"