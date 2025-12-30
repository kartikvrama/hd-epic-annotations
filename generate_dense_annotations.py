import os
import json
import argparse
import torch
import numpy as np
import subprocess
import tempfile
from pathlib import Path

# Assuming SAM 2 is installed and available in the environment
try:
    from sam2.build_sam import build_sam2_video_predictor
except ImportError:
    print("SAM 2 not found. Please ensure it is installed.")

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("Warning: OpenCV not available. Video resizing will require ffmpeg.")

def load_jsonl(path):
    data = []
    with open(path, 'r') as f:
        for line in f:
            data.append(json.loads(line))
    return data

def get_video_resolution(video_path):
    """Get the width and height of a video file."""
    if CV2_AVAILABLE:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        return width, height
    else:
        # Fallback: use ffprobe
        try:
            cmd = [
                'ffprobe', '-v', 'error', '-select_streams', 'v:0',
                '-show_entries', 'stream=width,height', '-of', 'json',
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            info = json.loads(result.stdout)
            width = info['streams'][0]['width']
            height = info['streams'][0]['height']
            return width, height
        except (subprocess.CalledProcessError, KeyError, json.JSONDecodeError) as e:
            raise ValueError(f"Could not get video resolution: {e}")

def resize_video(input_path, output_path, scale_factor):
    """
    Resize a video using ffmpeg (preferred) or OpenCV (fallback).
    
    Args:
        input_path: Path to input video
        output_path: Path to output resized video
        scale_factor: Scale factor (0.1 to 1.0)
    
    Returns:
        Tuple of (new_width, new_height)
    """
    if scale_factor <= 0 or scale_factor > 1.0:
        raise ValueError(f"scale_factor must be between 0.1 and 1.0, got {scale_factor}")
    
    # Get original resolution
    orig_width, orig_height = get_video_resolution(input_path)
    new_width = int(orig_width * scale_factor)
    new_height = int(orig_height * scale_factor)
    
    # Ensure even dimensions for video codecs
    new_width = new_width - (new_width % 2)
    new_height = new_height - (new_height % 2)
    
    # Try ffmpeg first (faster and more efficient)
    try:
        cmd = [
            'ffmpeg', '-i', input_path,
            '-vf', f'scale={new_width}:{new_height}',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
            '-y',  # Overwrite output file
            output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"Resized video using ffmpeg: {orig_width}x{orig_height} -> {new_width}x{new_height}")
        return new_width, new_height
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback to OpenCV if ffmpeg is not available
        if not CV2_AVAILABLE:
            raise RuntimeError("Neither ffmpeg nor OpenCV is available for video resizing")
        
        print(f"ffmpeg not available, using OpenCV fallback")
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {input_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (new_width, new_height))
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            resized_frame = cv2.resize(frame, (new_width, new_height))
            out.write(resized_frame)
        
        cap.release()
        out.release()
        print(f"Resized video using OpenCV: {orig_width}x{orig_height} -> {new_width}x{new_height}")
        return new_width, new_height

def get_stationary_objects(scene_graph_path, assoc_info, video_id):
    scene_graph = load_jsonl(scene_graph_path)
    all_objects = set()
    for frame in scene_graph:
        for obj in frame.get('objects', []):
            all_objects.add(obj['name'])
    
    moved_objects = set()
    if video_id in assoc_info:
        for assoc_id, assoc_data in assoc_info[video_id].items():
            moved_objects.add(assoc_data['name'])
            
    stationary_objects = all_objects - moved_objects
    return sorted(list(stationary_objects))

def process_video(video_id, video_path, scene_graph_path, assoc_info_path, mask_info_path, output_dir, frame_interval=1, video_scale_factor=1.0):
    print(f"Processing video: {video_id}")
    
    with open(assoc_info_path, 'r') as f:
        assoc_info = json.load(f)
    with open(mask_info_path, 'r') as f:
        mask_info = json.load(f)
        
    # 1. Identify and save stationary objects
    stationary = get_stationary_objects(scene_graph_path, assoc_info, video_id)
    stationary_file = os.path.join(output_dir, f"stationary_objects_{video_id}.txt")
    with open(stationary_file, 'w') as f:
        for obj in stationary:
            f.write(f"{obj}\n")
    print(f"Saved stationary objects to {stationary_file}")

    if video_id not in assoc_info:
        print(f"No movement data for {video_id}. Skipping tracking.")
        return

    # 1.5. Handle video resolution scaling if needed
    original_video_path = video_path
    temp_video_path = None
    scale_factor = video_scale_factor
    original_width, original_height = None, None
    processed_width, processed_height = None, None
    
    try:
        if video_scale_factor < 1.0:
            # Get original resolution
            original_width, original_height = get_video_resolution(video_path)
            print(f"Original video resolution: {original_width}x{original_height}")
            
            # Create temporary resized video
            temp_dir = tempfile.gettempdir()
            temp_video_path = os.path.join(temp_dir, f"resized_{video_id}_{os.getpid()}.mp4")
            processed_width, processed_height = resize_video(video_path, temp_video_path, video_scale_factor)
            video_path = temp_video_path
            print(f"Using resized video: {processed_width}x{processed_height} (scale factor: {video_scale_factor})")
        else:
            # No scaling needed, but we still need original dimensions for bbox scaling
            original_width, original_height = get_video_resolution(video_path)
            processed_width, processed_height = original_width, original_height
            scale_factor = 1.0
    except Exception as e:
        print(f"Warning: Could not resize video: {e}. Proceeding with original video.")
        original_width, original_height = get_video_resolution(video_path)
        processed_width, processed_height = original_width, original_height
        scale_factor = 1.0

    try:
        # 2. Initialize SAM 2 Video Predictor
        # Note: Model paths and config should be adjusted based on server setup
        sam2_checkpoint = "/coc/flash5/kvr6/repos/sam2/checkpoints/sam2.1_hiera_small.pt"
        model_cfg = "configs/sam2.1/sam2.1_hiera_s.yaml"
        predictor = build_sam2_video_predictor(model_cfg, sam2_checkpoint)
        print("SAM 2 predictor initialized")

        # 3. Process each manipulated object (association)
        dense_annotations = []
        
        # We need to organize frames for SAM 2. SAM 2 usually takes a directory of JPEG frames.
        # For this implementation, we assume frames are extracted or SAM 2 can handle the video.
        # Here we focus on the logic of multi-point initialization.
        
        # Clear GPU cache before loading video
        torch.cuda.empty_cache()
        if torch.cuda.is_available():
            print(f"GPU memory before init: {torch.cuda.memory_allocated() / 1024**3:.2f} GB")

        print(f"Initializing inference state for video {video_id}: video path {video_path}")
        inference_state = predictor.init_state(
            video_path=video_path,
            offload_video_to_cpu=True,  # Keep video frames in CPU memory
            offload_state_to_cpu=True  # Tip: Keep state on GPU for better performance
        )
        print("Inference state initialized")
        if torch.cuda.is_available():
            print(f"GPU memory after init: {torch.cuda.memory_allocated() / 1024**3:.2f} GB")

        for assoc_id, assoc_data in assoc_info[video_id].items():
            obj_name = assoc_data['name']
            print(f"Tracking object: {obj_name} (ID: {assoc_id})")
            
            # Collect all available bboxes for this association as prompts
            prompts = []
            for track in assoc_data['tracks']:
                for mask_id in track['masks']:
                    if mask_id in mask_info[video_id]:
                        m_data = mask_info[video_id][mask_id]
                        prompts.append({
                            "frame_idx": m_data['frame_number'],
                            "bbox": m_data['bbox'] # [xmin, ymin, xmax, ymax]
                        })
            
            if not prompts:
                continue

            # Add multiple prompts to the predictor for this object
            for prompt in prompts:
                print(f"Adding prompt for frame {prompt['frame_idx']}")
                # Scale bbox from original resolution to processed resolution if needed
                bbox = prompt['bbox']
                if scale_factor < 1.0:
                    scaled_bbox = [coord * scale_factor for coord in bbox]
                else:
                    scaled_bbox = bbox
                
                _, out_obj_ids, out_mask_logits = predictor.add_new_points_or_box(
                    inference_state=inference_state,
                    frame_idx=prompt['frame_idx'],
                    obj_id=int(assoc_id.split('_')[-1]) if '_' in assoc_id else hash(assoc_id) % 1000,
                    box=np.array(scaled_bbox, dtype=np.float16),
                )

        # 4. Propagate bidirectionally
        print("Starting video propagation...")
        video_segments = {} # obj_id -> frame_idx -> bbox
        frame_count = 0
        last_print_frame = -1
        print_interval = 50  # Print progress every 50 frames
        
        for out_frame_idx, out_obj_ids, out_mask_logits in predictor.propagate_in_video(inference_state):
            frame_count += 1
            
            # Print progress periodically
            if out_frame_idx - last_print_frame >= print_interval or frame_count == 1:
                print(f"Processing frame {out_frame_idx} (processed {frame_count} frames so far)")
                last_print_frame = out_frame_idx
            
            for i, out_obj_id in enumerate(out_obj_ids):
                mask = (out_mask_logits[i] > 0.0).cpu().numpy()
                if mask.any():
                    # Convert mask to bbox
                    y, x = np.where(mask[0])
                    bbox = [float(np.min(x)), float(np.min(y)), float(np.max(x)), float(np.max(y))]
                    
                    if out_obj_id not in video_segments:
                        video_segments[out_obj_id] = {}
                    video_segments[out_obj_id][out_frame_idx] = bbox
        
        print(f"Completed propagation: processed {frame_count} frames total")

        # 5. Save results (only every Nth frame)
        output_file = os.path.join(output_dir, f"dense_annotations_{video_id}.jsonl")
        all_frame_indices = sorted(set(idx for seg in video_segments.values() for idx in seg.keys()))
        filtered_frame_indices = [idx for idx in all_frame_indices if idx % frame_interval == 0]
        
        with open(output_file, 'w') as f:
            for frame_idx in filtered_frame_indices:
                frame_data = {"frame_number": frame_idx, "objects": []}
                for obj_id, segments in video_segments.items():
                    if frame_idx in segments:
                        # Scale bbox back to original resolution if video was resized
                        bbox = segments[frame_idx]
                        if scale_factor < 1.0:
                            # Scale back to original resolution
                            original_bbox = [coord / scale_factor for coord in bbox]
                        else:
                            original_bbox = bbox
                        
                        # Find original assoc_id and name
                        # (In a real implementation, we'd maintain a mapping)
                        frame_data["objects"].append({
                            "assoc_id": str(obj_id),
                            "bbox": original_bbox
                        })
                f.write(json.dumps(frame_data) + "\n")
        
        predictor.reset_state(inference_state)
        print(f"Saved dense annotations to {output_file}")
    finally:
        # 6. Cleanup temporary video file if it was created (even on errors)
        if temp_video_path and os.path.exists(temp_video_path):
            try:
                os.remove(temp_video_path)
                print(f"Cleaned up temporary video file: {temp_video_path}")
            except Exception as e:
                print(f"Warning: Could not remove temporary video file {temp_video_path}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video_id", type=str, required=True)
    parser.add_argument("--video_path", type=str, default="/Users/kartikramachandruni/Documents/data/hd-epic-videos")
    parser.add_argument("--scene_graph_dir", type=str, default="outputs")
    parser.add_argument("--assoc_info", type=str, default="scene-and-object-movements/assoc_info.json")
    parser.add_argument("--mask_info", type=str, default="scene-and-object-movements/mask_info.json")
    parser.add_argument("--output_dir", type=str, default="outputs")
    parser.add_argument("--frame_interval", type=int, default=1, 
                        help="Annotate every Nth frame (default: 1, annotates all frames)")
    parser.add_argument("--video_scale_factor", type=float, default=1.0,
                        help="Scale factor for video resolution (0.1 to 1.0, default: 1.0 = no scaling). "
                             "Reduces memory usage for high-resolution videos.")
    args = parser.parse_args()
    
    # Validate scale factor
    if args.video_scale_factor < 0.1 or args.video_scale_factor > 1.0:
        parser.error("--video_scale_factor must be between 0.1 and 1.0")

    person_id = args.video_id.split('-')[0]
    v_path = os.path.join(args.video_path, f"{person_id}", f"{args.video_id}.mp4")
    sg_path = os.path.join(args.scene_graph_dir, f"scene_graphs_{args.video_id}.jsonl")
    print(f"Video path: {v_path}")
    print(f"Scene graph path: {sg_path}")
    
    process_video(args.video_id, v_path, sg_path, args.assoc_info, args.mask_info, args.output_dir, args.frame_interval, args.video_scale_factor)
