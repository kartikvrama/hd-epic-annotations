#!/bin/bash
#SBATCH --job-name=dense_annotations_optimized
#SBATCH --partition=rail-lab
#SBATCH --ntasks=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=64
#SBATCH --gpus=a40:1
#SBATCH --qos=long
#SBATCH --output=logs/R-%x.%j.out
#SBATCH --error=logs/R-%x.%j.err

# Set up environment
export PYTHONPATH=/coc/flash5/kvr6/containers/envs/llmEnv/bin/python

# Video data path on server
VIDEO_DATA_DIR="/coc/flash5/kvr6/data/hd-epic-data-files/HD-EPIC/Videos"

# Optimized parameters for memory efficiency
FRAME_INTERVAL=30
VIDEO_SCALE_FACTOR=0.5
WINDOW_DURATION=300  # 5 minutes
WINDOW_OVERLAP=30    # 30 seconds

# Read video IDs from file and loop over them
VIDEO_IDS_FILE="video_ids_twentyExamples.txt"

cd /coc/flash5/kvr6/repos/hd-epic-annotations

echo "Starting memory-optimized dense annotations with temporal window processing"
echo "Parameters:"
echo "  Frame interval: $FRAME_INTERVAL"
echo "  Video scale factor: $VIDEO_SCALE_FACTOR"
echo "  Window duration: ${WINDOW_DURATION}s"
echo "  Window overlap: ${WINDOW_OVERLAP}s"
echo "Memory optimization features enabled:"
echo "  - Temporal window processing (5-minute windows)"
echo "  - Video offloading to CPU"
echo "  - Streaming result management"
echo "  - Aggressive memory cleanup between windows"
echo "Expected memory reduction: 70-85%"
echo ""

while IFS= read -r video_id || [ -n "$video_id" ]; do
    # Skip empty lines
    [ -z "$video_id" ] && continue
    
    echo "Processing video_id: $video_id"
    echo "Estimated memory usage: ~7-14GB (down from ~48GB)"
    
    # Run the optimized dense annotation script
    CMD="$PYTHONPATH -u generate_dense_annotations_optimized.py \
        --video_id $video_id \
        --video_path $VIDEO_DATA_DIR \
        --scene_graph_dir outputs/scene_graphs \
        --assoc_info scene-and-object-movements/assoc_info.json \
        --mask_info scene-and-object-movements/mask_info.json \
        --output_dir outputs/dense_annotations \
        --video_scale_factor $VIDEO_SCALE_FACTOR \
        --frame_interval $FRAME_INTERVAL \
        --window_duration $WINDOW_DURATION \
        --window_overlap $WINDOW_OVERLAP"
    
    echo "Executing: $CMD"
    eval $CMD
    
    # Check if command was successful
    if [ $? -ne 0 ]; then
        echo "Error processing video_id: $video_id"
    else
        echo "Successfully processed video_id: $video_id"
    fi
    echo "---"
done < "$VIDEO_IDS_FILE"

echo "Memory-optimized processing completed!"
echo "Check outputs/dense_annotations/ for results"
