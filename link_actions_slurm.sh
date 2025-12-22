#!/bin/bash
#SBATCH --job-name=link_actions_to_objects_llm
#SBATCH --partition=rail-lab
#SBATCH --ntasks=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=16
#SBATCH --gpus=a40:1
#SBATCH --qos=short
#SBATCH --output=logs/R-%x.%j.out
#SBATCH --error=logs/R-%x.%j.err

cd /coc/flash5/kvr6/repos
./ollama/bin/ollama serve&
export PYTHONPATH=/coc/flash5/kvr6/anaconda3/envs/llmEnv/bin/python
cd /coc/flash5/kvr6/repos/hd-epic-annotations
CMD="$PYTHONPATH -u /coc/flash5/kvr6/repos/hd-epic-annotations/link_actions_to_objects_llm.py --video_id P01-20240203-123350"
echo $CMD
eval $CMD
