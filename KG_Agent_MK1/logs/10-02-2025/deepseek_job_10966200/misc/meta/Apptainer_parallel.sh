#!/bin/bash
#SBATCH --job-name=deepseek_v3
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
LOG_DIR="$SCRIPT_ROOT_DIR/logs/$LOG_DATE/deepseek_job_${SLURM_JOB_ID}"
OUTPUT_DIR="$LOG_DIR/misc/temp"

mkdir -p "$LOG_DIR/misc/meta"
mkdir -p "$OUTPUT_DIR"

GPU_USAGE_PLOT="$LOG_DIR/misc/gpu_usage.png"
GPU_CSV_FILE="$LOG_DIR/misc/gpu_usage.csv"

echo "LOG_DIR: $LOG_DIR"
echo "OUTPUT_DIR: $OUTPUT_DIR"

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

# Start the DeepSeek model server
apptainer exec --nv --pwd /app \
  --bind /p/project1/hai_kg-rag-thesis/models:/models \
  /p/project1/hai_kg-rag-thesis/llama_server.sif \
  ./llama-server \
  -m "$MODEL_PATH" \
  --port $LLAMA_CPP_PORT --host $LLAMA_CPP_HOST \
  -n 512 -c 4096 \
  --n-gpu-layers $GPU_LAYERS \
  --parallel $TENSOR_PARALLEL_SIZE \
  --cache-type-k q5_0 \
  --mlock \
  --rope-freq-base 1000000 \
  2>&1 | tee -a "$LOG_DIR/server.log" &

# SERVER_PID=$!
# echo "Server PID: $SERVER_PID"
# sleep $LLM_SERVER_WAIT  # Give time for the server to start

# # Wait for LLM server to bind to port
# echo "Waiting for LLM server to start on port $LLAMA_CPP_PORT..."
# for i in $(seq 1 $LLM_SERVER_RETRIES); do
#     if nc -z "$LLAMA_CPP_HOST" "$LLAMA_CPP_PORT"; then
#         echo "LLM server is ready!"
#         break
#     fi
#     echo "Retrying to connect to port $LLAMA_CPP_PORT... ($i/$LLM_SERVER_RETRIES)"
#     sleep 1
# done

# if ! nc -z "$LLAMA_CPP_HOST" "$LLAMA_CPP_PORT"; then
#     echo "ERROR: LLM server did not start after $LLM_SERVER_RETRIES seconds."
#     kill "$SERVER_PID" 2>/dev/null
#     exit 1
# fi

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
    exit 1
fi


# Define paths
SYSTEM_PROMPT_PATH="$SCRIPT_ROOT_DIR/system_prompt.txt"

# Extended Logging for `call_llm_api.py`
echo "Calling LLM API..." | tee -a "$LOG_DIR/call_llm_api.log"
python "$SCRIPT_ROOT_DIR/call_llm_api.py" \
  --host "$LLAMA_CPP_HOST" \
  --port "$LLAMA_CPP_PORT" \
  --model_path "$MODEL_PATH" \
  --user_prompt_path "$USER_PROMPT_PATH" \
  --system_prompt_path "$SYSTEM_PROMPT_PATH" \
  --output_dir "$OUTPUT_DIR" \
  --max_tokens "$MAX_TOKENS" \
  --temperature "$TEMPERATURE" \
  --model_name "$MODEL_NAME" \
  > "$LOG_DIR/call_llm_api.out" 2> "$LOG_DIR/call_llm_api.err"

if [ $? -ne 0 ]; then
    echo "ERROR: LLM API call failed. Check logs: $LOG_DIR/call_llm_api.err" | tee -a "$LOG_DIR/call_llm_api.log"
    exit 1
fi
echo "LLM API call completed successfully!" | tee -a "$LOG_DIR/call_llm_api.log"

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
