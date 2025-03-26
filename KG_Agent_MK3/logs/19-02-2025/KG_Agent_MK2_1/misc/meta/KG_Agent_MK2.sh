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

# Call LLM to generate shexer parameters in structured json format
# python generate_shexer_params.py \
#   --model "$GENERATE_SHEXER_PARAMS_MODEL" \
#   --openai_api_key "$OPENAI_API_KEY" \
#   --user_prompt_path $USER_PROMPT_PATH \
#   --system_prompt_path $GENERATE_SHEXER_PARAMS_SYSTEM_PROMPT_PATH \
#   --shexer_params_path "$TEMP_OUTPUT_DIR/shexer_params" \
#   > "$LOG_DIR/generate_shexer_params.out" 2> "$LOG_DIR/generate_shexer_params.err"

# python generate_shape.py \
#   --shexer_params_path "/p/project1/hai_kg-rag-thesis/scripts/KG_Agent_MK2/logs/17-02-2025/KG_Agent_MK2_8/misc/temp/shexer_params" \
#   --shape_output_dir "/p/project1/hai_kg-rag-thesis/scripts/KG_Agent_MK2/logs/17-02-2025/KG_Agent_MK2_8/misc/temp" \
#   > "$LOG_DIR/generate_shape.out" 2> "$LOG_DIR/generate_shape.err"

python call_llm_api.py \
  --model $GENERATE_SPARQL_QUERY_MODEL \
  --openai_api_key $OPENAI_API_KEY \
  --user_prompt_path $USER_PROMPT_PATH \
  --system_prompt_path $GENERATE_SPARQL_QUERY_SYSTEM_PROMPT_PATH \
  --shexer_params_path $SHEXER_PARAMS_PATH \
  --output_dir $TEMP_OUTPUT_DIR \

