#!/bin/bash
#SBATCH --job-name=dense_annotations_sam2
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

# Frame interval: annotate every Nth frame (default: 1 = all frames)
FRAME_INTERVAL=30

# Read video IDs from file and loop over them
VIDEO_IDS_FILE="video_ids_twentyExamples.txt"

cd /coc/flash5/kvr6/repos/hd-epic-annotations

while IFS= read -r video_id || [ -n "$video_id" ]; do
    # Skip empty lines
    [ -z "$video_id" ] && continue
    
    echo "Processing video_id: $video_id"
    
    # Run the dense annotation script
    CMD="$PYTHONPATH -u generate_scene_graphs.py --video_id $video_id; $PYTHONPATH -u generate_dense_annotations.py \
        --video_id $video_id \
        --video_path $VIDEO_DATA_DIR \
        --scene_graph_dir outputs/scene_graphs \
        --assoc_info scene-and-object-movements/assoc_info.json \
        --mask_info scene-and-object-movements/mask_info.json \
        --output_dir outputs/dense_annotations \
        --video_scale_factor 0.5 \
        --frame_interval $FRAME_INTERVAL"
    
    echo $CMD
    eval $CMD
    
    # Check if command was successful
    if [ $? -ne 0 ]; then
        echo "Error processing video_id: $video_id"
    else
        echo "Successfully processed video_id: $video_id"
    fi
    echo "---"
done < "$VIDEO_IDS_FILE"
