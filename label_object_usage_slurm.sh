#!/bin/bash
#SBATCH --job-name=link_actions_to_objects_llm
#SBATCH --partition=overcap
#SBATCH --ntasks=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=32
#SBATCH --gpus=a40:1
#SBATCH --qos=long
#SBATCH --output=logs/R-%x.%j.out
#SBATCH --error=logs/R-%x.%j.err
#SBATCH --exclude=xaea-12

cd /coc/flash5/kvr6/repos
./ollama/bin/ollama serve&
export PYTHONPATH=/coc/flash5/kvr6/containers/envs/llmEnv/bin/python
cd /coc/flash5/kvr6/repos/hd-epic-annotations

# Read video IDs from file and loop over them
# VIDEO_IDS_FILE="video_ids_long.txt"
# VIDEO_IDS_FILE="video_ids_short.txt"
VIDEO_IDS_FILE="video_ids_twentyExamples.txt"

MODEL_NAME="gpt-oss:20b"
# MODEL_NAME="qwen3:30b"
TEMPERATURE=0.8
MAX_NUM_PREDICT=2000
NUM_TRIES=3
MAX_SEGMENT_LENGTH=30

# Which quarter of the file to process (1, 2, 3, or 4)
# Quarter 1: 0% - 25%
# Quarter 2: 25% - 50%
# Quarter 3: 50% - 75%
# Quarter 4: 75% - 100%
# Usage: sbatch label_object_usage_slurm.sh [QUARTER]
# If no argument provided, defaults to 1
QUARTER=${1:-1}

# Validate quarter argument
if [[ ! "$QUARTER" =~ ^[1-4]$ ]]; then
    echo "Error: QUARTER must be 1, 2, 3, or 4. Got: $QUARTER"
    exit 1
fi

# Calculate line ranges for the selected quarter
TOTAL_LINES=$(wc -l < "$VIDEO_IDS_FILE")
QUARTER_SIZE=$((TOTAL_LINES / 4))

case $QUARTER in
    1)
        START_LINE=1
        END_LINE=$QUARTER_SIZE
        ;;
    2)
        START_LINE=$((QUARTER_SIZE + 1))
        END_LINE=$((QUARTER_SIZE * 2))
        ;;
    3)
        START_LINE=$((QUARTER_SIZE * 2 + 1))
        END_LINE=$((QUARTER_SIZE * 3))
        ;;
    4)
        START_LINE=$((QUARTER_SIZE * 3 + 1))
        END_LINE=$TOTAL_LINES
        ;;
    *)
        echo "Invalid QUARTER value. Must be 1, 2, 3, or 4."
        exit 1
        ;;
esac

echo "Processing quarter $QUARTER: lines $START_LINE to $END_LINE (out of $TOTAL_LINES total lines)"

# Extract the quarter and reverse it
sed -n "${START_LINE},${END_LINE}p" "$VIDEO_IDS_FILE" | cat | while IFS= read -r video_id || [ -n "$video_id" ]; do
    # Skip empty lines
    [ -z "$video_id" ] && continue
    
    echo "Processing video_id: $video_id"
    CMD="$PYTHONPATH -u generate_scene_graphs.py --video_id $video_id; $PYTHONPATH -u label_object_usage_llm.py --video_id $video_id --model_name $MODEL_NAME --temperature $TEMPERATURE --max_num_predict $MAX_NUM_PREDICT --num_tries $NUM_TRIES --max_segment_length $MAX_SEGMENT_LENGTH --long"
    echo $CMD
    eval $CMD
    
    # Check if command was successful
    if [ $? -ne 0 ]; then
        echo "Error processing video_id: $video_id"
    else
        echo "Successfully processed video_id: $video_id"
    fi
    echo "---"

done
