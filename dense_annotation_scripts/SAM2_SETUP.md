# SAM 2 Setup Guide for Dense Annotations

This guide provides step-by-step instructions to set up SAM 2 (Segment Anything Model 2) for running the dense bounding box annotation script.

## Prerequisites

- **Python 3.8+** installed
- **NVIDIA GPU with CUDA support** (recommended: A40 or better)
- **At least 32GB RAM** for processing longer videos
- **CUDA 11.8+** and **cuDNN 8+** for optimal performance

## Installation Steps

### 1. Install SAM 2

Install SAM 2 from the official repository:

```bash
# Clone the SAM 2 repository
git clone https://github.com/facebookresearch/sam2.git
cd sam2

# Install the package with all dependencies
pip install -e ".[build]"
```

Alternatively, if you have a Conda environment:

```bash
conda create -n sam2 python=3.10
conda activate sam2
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install -e ".[build]"
```

### 2. Download Model Checkpoints

SAM 2 provides several model sizes. For dense annotations, we recommend the `large` model for best accuracy:

```bash
# Create checkpoints directory
mkdir -p checkpoints

# Download the large model (recommended)
wget https://dl.fbaipublicfiles.com/sam2/sam2_hiera_large.pt -O checkpoints/sam2_hiera_large.pt

# Optionally download smaller models for testing
wget https://dl.fbaipublicfiles.com/sam2/sam2_hiera_base_plus.pt -O checkpoints/sam2_hiera_base_plus.pt
wget https://dl.fbaipublicfiles.com/sam2/sam2_hiera_small.pt -O checkpoints/sam2_hiera_small.pt
```

### 3. Verify Installation

Test the installation with a simple script:

```python
from sam2.build_sam import build_sam2_video_predictor

# Test model loading
predictor = build_sam2_video_predictor(
    model_cfg="sam2_hiera_l.yaml", 
    sam2_checkpoint="checkpoints/sam2_hiera_large.pt"
)
print("SAM 2 installation successful!")
```

## Configuration for Dense Annotations

### 1. Update Model Configuration

Edit the `generate_dense_annotations.py` script to point to your model paths:

```python
# For large model (best quality)
sam2_checkpoint = "checkpoints/sam2_hiera_large.pt"
model_cfg = "sam2_hiera_l.yaml"

# For base model (faster)
sam2_checkpoint = "checkpoints/sam2_hiera_base_plus.pt" 
model_cfg = "sam2_hiera_base_plus.yaml"

# For small model (fastest)
sam2_checkpoint = "checkpoints/sam2_hiera_small.pt"
model_cfg = "sam2_hiera_small.yaml"
```

### 2. Environment Variables

Set the following environment variables for optimal performance:

```bash
# For GPU acceleration
export CUDA_VISIBLE_DEVICES=0,1

# For memory optimization
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512

# Optional: Disable gradient computation for inference
export TOKENIZERS_PARALLELISM=false
```

### 3. Dependencies Installation

Install required dependencies:

```bash
pip install numpy opencv-python pathlib argparse
```

## Troubleshooting

### Common Issues

1. **CUDA Out of Memory**
   - Use a smaller SAM 2 model (`small` or `base` instead of `large`)
   - Reduce video resolution during processing
   - Process videos in smaller chunks

2. **SAM 2 Import Error**
   - Ensure you're in the correct Conda/Python environment
   - Reinstall with `pip install -e ".[build]"` in the SAM 2 directory

3. **Slow Performance**
   - Check GPU utilization with `nvidia-smi`
   - Ensure CUDA is properly installed and recognized
   - Consider using a smaller model for initial testing

4. **Video Path Issues**
   - Verify video files exist at the specified paths
   - Check file permissions and accessibility

### Performance Optimization

- **Use the `large` model** for best quality on the sky2 server
- **Enable mixed precision** by setting `torch.set_grad_enabled(False)`
- **Process multiple videos** concurrently using the Slurm batch script
- **Monitor GPU memory** usage during processing

## File Structure

After setup, your directory structure should look like:

```
hd-epic-annotations/
├── checkpoints/
│   ├── sam2_hiera_large.pt
│   ├── sam2_hiera_base_plus.pt
│   └── sam2_hiera_small.pt
├── sam2/ (if cloned locally)
├── generate_dense_annotations.py
├── dense_annotations_slurm.sh
└── ...
```

## Testing

Run a single video test before processing the entire dataset:

```bash
python generate_dense_annotations.py --video_id P01-20240203-123350
```

Check the output files:
- `outputs/stationary_objects_P01-20240203-123350.txt`
- `outputs/dense_annotations_P01-20240203-123350.jsonl`

## Next Steps

Once SAM 2 is properly installed and tested, you can:

1. Run the full batch processing with `sbatch dense_annotations_slurm.sh`
2. Monitor progress using the log files in the `logs/` directory
3. Use the test script (`test_single_video_slurm.sh`) for individual video processing
