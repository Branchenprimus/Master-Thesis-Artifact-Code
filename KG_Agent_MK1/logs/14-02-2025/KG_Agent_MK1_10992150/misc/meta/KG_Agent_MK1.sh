#!/bin/bash
#SBATCH --job-name=KG_Agent_MK1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:4
#SBATCH --time=02:00:00
#SBATCH --partition=booster  # Ensure using the correct partition
#SBATCH --output=/p/project1/hai_kg-rag-thesis/SLURM_logs/%x-%j.out
#SBATCH --error=/p/project1/hai_kg-rag-thesis/SLURM_logs/%x-%j.err

# Use SLURM_SUBMIT_DIR to get the actual directory where the script was submitted
SCRIPT_ROOT_DIR="$SLURM_SUBMIT_DIR"
echo "SCRIPT_ROOT_DIR: $SCRIPT_ROOT_DIR"

# Load required modules
module load Stages/2024 GCCcore/.12.3.0 NVHPC/23.7-CUDA-12 Python/3.11.3

# sourve .env and venv
source "$SCRIPT_ROOT_DIR/.env"
source /p/project1/hai_kg-rag-thesis/env/llamacpp/bin/activate

# Logging Setup
LOG_DATE=$(date +"%d-%m-%Y")
LOG_DIR="$SCRIPT_ROOT_DIR/logs/$LOG_DATE/KG_Agent_MK1_${SLURM_JOB_ID}"
TEMP_OUTPUT_DIR="$LOG_DIR/misc/temp"

GPU_LOG_DIR="$LOG_DIR/misc/monitor"
GPU_USAGE_PLOT="$GPU_LOG_DIR/gpu_usage.png"
GPU_CSV_FILE="$GPU_LOG_DIR/gpu_usage.csv"

# Path to LLM-generated SPARQL query
SPARQL_QUERY_FILE="$TEMP_OUTPUT_DIR/llm_response.txt"
SPARQL_OUTPUT_FILE="$TEMP_OUTPUT_DIR/SPARQL_response.csv"

mkdir -p "$LOG_DIR/misc/meta"
mkdir -p "$TEMP_OUTPUT_DIR"
mkdir -p "$GPU_LOG_DIR"

echo "LOG_DIR: $LOG_DIR"
echo "TEMP_OUTPUT_DIR: $TEMP_OUTPUT_DIR"

exec > >(tee -a "$LOG_DIR/job.out") 2> >(tee -a "$LOG_DIR/job.err" >&2)
set -x  # Enable debugging

# GPU configuration
export CUDA_VISIBLE_DEVICES=0,1,2,3

# Ensure port is free
if lsof -i :"$LLAMA_CPP_PORT" >/dev/null 2>&1; then
    echo "ERROR: Port $LLAMA_CPP_PORT is already in use!"
    exit 1
fi

# Start GPU monitoring in the background
if [ ! -f "$GPU_CSV_FILE" ]; then
    echo "timestamp,index,name,utilization.gpu [%],memory.used [MiB],memory.total [MiB]" > "$GPU_CSV_FILE"
fi

(
    while true; do
        nvidia-smi --query-gpu=timestamp,index,name,utilization.gpu,memory.used,memory.total \
                   --format=csv,noheader >> "$GPU_CSV_FILE"
        sleep $GPU_LOG_INTERVAL
    done
) &
GPU_MONITOR_PID=$!

# Extended Logging for `track_files.py`
echo "Starting file tracking..." | tee -a "$LOG_DIR/track_files.log"
python "$SCRIPT_ROOT_DIR/track_files.py" \
  --root-dir "$SCRIPT_ROOT_DIR" --output "$LOG_DIR/misc/meta" \
  > "$LOG_DIR/track_files.out" 2> "$LOG_DIR/track_files.err"


if [ $? -ne 0 ]; then
    echo "ERROR: File tracking failed. Check logs: $LOG_DIR/track_files.err" | tee -a "$LOG_DIR/track_files.log"
    exit 1
fi
echo "File tracking completed successfully!" | tee -a "$LOG_DIR/track_files.log"

export CUDA_VISIBLE_DEVICES=0,1,2,3  # Explicitly assign 4 GPUs

# Start the DeepSeek model server container
apptainer exec --nv --pwd /app \
  --bind /p/project1/hai_kg-rag-thesis/models:/models \
  /p/project1/hai_kg-rag-thesis/llama_server.sif \
  ./llama-server \
  -m "/models/unsloth/DeepSeek-V3-GGUF/DeepSeek-V3-Q2_K_XS/DeepSeek-V3-Q2_K_XS-00001-of-00005.gguf" \
  --host 0.0.0.0 \
  --port 8000 \
  --n-gpu-layers 30 \
  --flash-attn \
  --mlock \
  --verbose 2>&1 | tee -a "$LOG_DIR/server.log"

# Wait for server AND model readiness
echo "Waiting for server & model initialization..."

for ((i=1; i<=$LLM_SERVER_WAIT; i++)); do
    # Check if port is open and model is fully loaded
    if nc -z "$LLAMA_CPP_HOST" "$LLAMA_CPP_PORT" && \
       curl -sSf http://$LLAMA_CPP_HOST:$LLAMA_CPP_PORT/v1/health | grep -q '"model_loaded":true'; then
        echo -e "\n Server & model fully ready after $i seconds!"
        break
    fi
    
    # Show progress bar with elapsed time
    printf "\r Retrying... [%d/%d] | Elapsed: %02d:%02d" $i $LLM_SERVER_WAIT $((i/60)) $((i%60))
    
    sleep $LLM_SERVER_RETRY_INTERVAL
done

# If the loop exits without breaking, timeout occurred
if [[ $i -eq $MAX_RETRIES ]]; then
    echo -e "\n ERROR: Server & model did not initialize within $(($LLM_SERVER_WAIT / 60)) minutes."
fi

# Extract shacl and shex shapes from a given turtle file (TURTLE_INPUT_PATH) and save the result to the output path (SHAPE_OUTPUT_PATH)
python "/p/project1/hai_kg-rag-thesis/scripts/KG_Agent_MK1/extract_shapes.py" \
  --turtle_input_path "$TURTLE_INPUT_PATH" \
  --shape_output_path "$SHAPE_OUTPUT_PATH" \
  > "$LOG_DIR/extract_shapes.out" 2> "$LOG_DIR/extract_shapes.err"

# Define paths
SYSTEM_PROMPT_PATH="$SCRIPT_ROOT_DIR/system_prompt.txt"

# Extract the base filename from TURTLE_INPUT_PATH (removes directory and .ttl extension)
BASE_FILENAME=$(basename "$TURTLE_INPUT_PATH" .ttl)

# Determine shape path dynamically based on USE_SHAPE
if [ "$USE_SHAPE" == "shacl" ]; then
    SHAPE_PATH="$SHAPE_OUTPUT_PATH/${BASE_FILENAME}_shacl.ttl"
elif [ "$USE_SHAPE" == "shex" ]; then
    SHAPE_PATH="$SHAPE_OUTPUT_PATH/${BASE_FILENAME}.shex"
else
    echo "❌ ERROR: USE_SHAPE must be either 'shacl' or 'shex'" | tee -a "$LOG_DIR/call_llm_api.log"
fi

# Ensure the shape file exists
if [ ! -f "$SHAPE_PATH" ]; then
    echo "❌ ERROR: Shape file not found: $SHAPE_PATH" | tee -a "$LOG_DIR/call_llm_api.log"
fi

# Call LLM API script with dynamically set SHAPE_PATH
echo "Calling LLM API..." | tee -a "$LOG_DIR/call_llm_api.log"
python "$SCRIPT_ROOT_DIR/call_llm_api.py" \
  --host "$LLAMA_CPP_HOST" \
  --port "$LLAMA_CPP_PORT" \
  --model_path "$MODEL_PATH" \
  --user_prompt_path "$USER_PROMPT_PATH" \
  --system_prompt_path "$SYSTEM_PROMPT_PATH" \
  --shape_path "$SHAPE_PATH" \
  --output_dir "$TEMP_OUTPUT_DIR" \
  --max_tokens "$MAX_TOKENS" \
  --temperature "$TEMPERATURE" \
  --model_name "$MODEL_NAME" \
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

while [ ! -f "$SPARQL_QUERY_FILE" ]; do
    if [ "$WAITED" -ge "$SPARQL_VERIFIER_MAX_WAIT_TIME" ]; then
        echo "ERROR: Timed out waiting for SPARQL query file: $SPARQL_QUERY_FILE"
        exit 1
    fi
    sleep $SPARQL_VERIFIER_SLEEP_INTERVAL
    (($SPARQL_VERIFIER_WAITED+=SPARQL_VERIFIER_SLEEP_INTERVAL))
done

# Run SPARQL verifier, that does some sanity checks on the query and executes it against $SPARQL_ENDPOINT_URL
echo "Verifying and executing SPARQL query..." | tee -a "$LOG_DIR/sparql_verifier.log"
python "$SCRIPT_ROOT_DIR/sparql_verifier.py" \
  --sparql_endpoint_url "$SPARQL_ENDPOINT_URL" \
  --ttl_file "$TURTLE_INPUT_PATH" \
  --response_file "$SPARQL_QUERY_FILE" \
  --output_dir "$TEMP_OUTPUT_DIR" \
  > "$LOG_DIR/sparql_verifier.out" 2> "$LOG_DIR/sparql_verifier.err"

if [ $? -ne 0 ]; then
    echo "ERROR: SPARQL verification failed. Check logs: $LOG_DIR/sparql_verifier.err" | tee -a "$LOG_DIR/sparql_verifier.log"
fi
echo "SPARQL verification and execution completed successfully!" | tee -a "$LOG_DIR/sparql_verifier.log"

# Stop GPU logging after everything is done
kill "$GPU_MONITOR_PID" 2>/dev/null
sleep 5  # Ensure logs are fully written

# Extended Logging for `gpu_graph.py`
echo "Generating GPU usage graph..." | tee -a "$LOG_DIR/gpu_graph.log"
python "$SCRIPT_ROOT_DIR/gpu_graph.py" \
    --csv_file "$GPU_CSV_FILE" \
    --output_image "$GPU_USAGE_PLOT" \
    > "$LOG_DIR/gpu_graph.out" 2> "$LOG_DIR/gpu_graph.err"

if [ $? -ne 0 ]; then
    echo "ERROR: GPU visualization failed. Check logs: $LOG_DIR/gpu_graph.err" | tee -a "$LOG_DIR/gpu_graph.log"
    exit 1
fi
echo "GPU usage visualization saved at: $GPU_USAGE_PLOT" | tee -a "$LOG_DIR/gpu_graph.log"