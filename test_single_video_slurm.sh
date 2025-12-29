#!/bin/bash
#SBATCH --job-name=test_dense_annotations
#SBATCH --partition=rail-lab
#SBATCH --ntasks=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=16
#SBATCH --gpus=a40:1
#SBATCH --qos=short
#SBATCH --output=logs/test-%x.%j.out
#SBATCH --error=logs/test-%x.%j.err

cd /coc/flash5/kvr6/repos/hd-epic-annotations

# Set up environment
export PYTHONPATH=/coc/flash5/kvr6/anaconda3/envs/llmEnv/bin/python
PYTHON_EXEC=$PYTHONPATH

# Video data path on server
VIDEO_DATA_DIR="/coc/flash5/kvr6/datasets/hd-epic-videos"

# Test video ID (first from the list)
TEST_VIDEO_ID="P01-20240203-123350"

echo "Testing dense annotations with video: $TEST_VIDEO_ID"

# Run the dense annotation script for a single test video
CMD="$PYTHON_EXEC -u generate_dense_annotations.py \
    --video_id $TEST_VIDEO_ID \
    --video_path $VIDEO_DATA_DIR \
    --scene_graph_dir outputs \
    --assoc_info scene-and-object-movements/assoc_info.json \
    --mask_info scene-and-object-movements/mask_info.json \
    --output_dir outputs"

echo "Running command: $CMD"
eval $CMD

# Check if command was successful
if [ $? -ne 0 ]; then
    echo "ERROR: Test failed for video_id: $TEST_VIDEO_ID"
    exit 1
else
    echo "SUCCESS: Test completed for video_id: $TEST_VIDEO_ID"
fi

# Verify output files were created
STATIONARY_FILE="outputs/stationary_objects_${TEST_VIDEO_ID}.txt"
DENSE_FILE="outputs/dense_annotations_${TEST_VIDEO_ID}.jsonl"

if [ -f "$STATIONARY_FILE" ]; then
    echo "Stationary objects file created: $STATIONARY_FILE"
    echo "Number of stationary objects: $(wc -l < "$STATIONARY_FILE")"
else
    echo "WARNING: Stationary objects file not found: $STATIONARY_FILE"
fi

if [ -f "$DENSE_FILE" ]; then
    echo "Dense annotations file created: $DENSE_FILE"
    echo "Number of annotation frames: $(wc -l < "$DENSE_FILE")"
else
    echo "ERROR: Dense annotations file not found: $DENSE_FILE"
fi

echo "Test completed. Check log files for details."
