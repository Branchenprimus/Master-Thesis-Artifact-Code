#!/bin/bash

# sourve .env and venv
source /p/project1/hai_kg-rag-thesis/scripts/KG_Agent_MK3/.env
source /p/project1/hai_kg-rag-thesis/env/KG_Agent_MK3_venv/bin/activate

# Logging Setup
LOG_DATE=$(date +"%d-%m-%Y")

# Find the highest existing index in logs/$LOG_DATE
LOG_BASE="logs/$LOG_DATE/KG_Agent_MK3"
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

# Get total number of questions from original dataset
TOTAL_QUESTIONS=$(jq '.questions | length' "$BENCHMARK_DATASET")
echo "Total questions in dataset: $TOTAL_QUESTIONS"

# Determine number of questions to process
if [ "$PROCESS_QUESTIONS" = "full" ]; then
  MAX_INDEX=$((TOTAL_QUESTIONS - 1))
else
  # Validate numeric input
  if ! [[ "$PROCESS_QUESTIONS" =~ ^[0-9]+$ ]]; then
    echo "ERROR: PROCESS_QUESTIONS must be 'full' or a positive integer"
    exit 1
  fi
  REQUESTED=$((PROCESS_QUESTIONS - 1))
  MAX_INDEX=$((REQUESTED < TOTAL_QUESTIONS ? REQUESTED : TOTAL_QUESTIONS - 1))
fi

# Process questions in sequence
for question_idx in $(seq 0 $MAX_INDEX); do
  echo "Processing question index $question_idx/$MAX_INDEX"


  # Extract entities
  python ./extract_entity_list.py \
    --benchmark_dataset "$BENCHMARK_DATASET" \
    --output_file "$TEMP_OUTPUT_DIR/extracted_nlq_sparql_with_entities.json" \
    --api_key "$API_KEY" \
    --model "$MODEL_ENTITY_EXTRACTION" \
    --llm_provider "$LLM_PROVIDER" \
    --is_local_graph "$IS_LOCAL_GRAPH" \
    --question_index "$question_idx" \
    >> "$LOG_DIR/extract_entity_list.out" 2>> "$LOG_DIR/extract_entity_list.err"

  # Generate shape
  python generate_shape.py \
    --target_json_file "$TEMP_OUTPUT_DIR/extracted_nlq_sparql_with_entities.json" \
    --shape_output_path "$TEMP_OUTPUT_DIR/shapes" \
    --is_local_graph "$IS_LOCAL_GRAPH" \
    --local_graph_location "$LOCAL_GRAPH_LOCATION" \
    --question_index "$question_idx" \
    >> "$LOG_DIR/generate_shape.out" 2>> "$LOG_DIR/generate_shape.err"

  # Generate SPARQL with LLM
  python call_llm_api.py \
    --model "$MODEL_SPARQL_GENERATION" \
    --api_key "$API_KEY" \
    --json_path "$TEMP_OUTPUT_DIR/extracted_nlq_sparql_with_entities.json" \
    --system_prompt_path "$SYSTEM_PROMPT_PATH" \
    --shape_path "$TEMP_OUTPUT_DIR/shapes" \
    --llm_provider "$LLM_PROVIDER" \
    --is_local_graph "$IS_LOCAL_GRAPH" \
    --question_index "$question_idx" \
    >> "$LOG_DIR/call_llm_api.out" 2>> "$LOG_DIR/call_llm_api.err"

  # Execute SPARQL queries
  python call_sparql_endpoint.py \
    --json_path "$TEMP_OUTPUT_DIR/extracted_nlq_sparql_with_entities.json" \
    --sparql_endpoint_url "https://query.wikidata.org/sparql" \
    --is_local_graph "$IS_LOCAL_GRAPH" \
    --local_graph_location "$LOCAL_GRAPH_LOCATION" \
    --question_index "$question_idx" \
    >> "$LOG_DIR/call_sparql_endpoint.out" 2>> "$LOG_DIR/call_sparql_endpoint.err"

  # Verify results
  python verify_sparql.py \
    --json_path "$TEMP_OUTPUT_DIR/extracted_nlq_sparql_with_entities.json" \
    --question_index "$question_idx" \
    >> "$LOG_DIR/verify_sparql.out" 2>> "$LOG_DIR/verify_sparql.err"

done

echo "Processing completed for $((MAX_INDEX + 1)) questions"