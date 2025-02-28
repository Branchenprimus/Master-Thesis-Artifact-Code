#!/bin/bash

# sourve .env and venv
source /p/project1/hai_kg-rag-thesis/scripts/KG_Agent_MK2/.env
source /p/project1/hai_kg-rag-thesis/env/KG_Agent_MK2_venv/bin/activate

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

python ./util/extract_entity_list.py \
  --input-file "/p/project1/hai_kg-rag-thesis/benchmark/QLAD_Benchmark/QALD_9_plus/data/qald_9_plus_test_wikidata.json" \
  --output-file "/p/project1/hai_kg-rag-thesis/scripts/KG_Agent_MK2/benchmark/extracted_nlq_sparql_with_entities.json" \
  > "$LOG_DIR/extract_entity_list.out" 2> "$LOG_DIR/extract_entity_list.err"

# python generate_shape.py \
#   --shape-output-path "$TEMP_OUTPUT_DIR/shapes" \
#   --json-file "/p/project1/hai_kg-rag-thesis/benchmark/QLAD_Benchmark/QALD_9_plus/data/extracted_nlq_sparql_with_entities_short.json" \
#   > "$LOG_DIR/generate_shape.out" 2> "$LOG_DIR/generate_shape.err"

# python call_llm_api.py \
#   --model $MODEL \
#   --openai_api_key $OPENAI_API_KEY \
#   --json_path $JSON_PATH \
#   --system_prompt_path $SYSTEM_PROMPT_PATH \
#   --shape_path "$TEMP_OUTPUT_DIR/shapes" \
#   --output_dir $TEMP_OUTPUT_DIR/llm_responses \
#   > "$LOG_DIR/call_llm_api.out" 2> "$LOG_DIR/call_llm_api.err"

