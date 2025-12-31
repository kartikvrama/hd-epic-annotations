#!/bin/bash
#SBATCH --job-name=link_actions_to_objects_llm
#SBATCH --partition=rail-lab
#SBATCH --ntasks=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=32
#SBATCH --gpus=a40:2
#SBATCH --qos=long
#SBATCH --output=logs/R-%x.%j.out
#SBATCH --error=logs/R-%x.%j.err

cd /coc/flash5/kvr6/repos
./ollama/bin/ollama serve&
export PYTHONPATH=/coc/flash5/kvr6/containers/envs/llmEnv/bin/python
cd /coc/flash5/kvr6/repos/hd-epic-annotations

# Read video IDs from file and loop over them
VIDEO_IDS_FILE="video_ids_short.txt"
while IFS= read -r video_id || [ -n "$video_id" ]; do
    # Skip empty lines
    [ -z "$video_id" ] && continue
    
    echo "Processing video_id: $video_id"
    CMD="$PYTHONPATH -u generate_scene_graphs.py --video_id $video_id; $PYTHONPATH -u generate_object_usage_prompts.py --video_id $video_id; $PYTHONPATH -u label_object_usage_llm.py --video_id $video_id"
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
