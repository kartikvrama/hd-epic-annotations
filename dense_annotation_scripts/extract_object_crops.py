"""
Extract object crops from video using mask IDs from scene graphs.

Usage:
    python extract_object_crops.py \
        --jsonl_path outputs/scene_graphs_P01-20240202-171220.jsonl \
        --video_path /path/to/video/P01-20240202-171220.mp4 \
        --output_dir outputs/object_crops_P01-20240202-171220

The script will:
1. Read mask_ids from the scene graphs JSONL file
2. Look up frame numbers and bounding boxes from mask_info.json
3. Extract crops from the video at the specified frames
4. Save crops as PNG files in the output directory
"""

import os
import json
import cv2
import argparse
from pathlib import Path


def load_scene_graphs(jsonl_path):
    """Load scene graphs from JSONL file."""
    entries = []
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))
    return entries


def load_mask_info(video_id):
    """Load mask info for a specific video."""
    with open("scene-and-object-movements/mask_info.json", 'r', encoding='utf-8') as f:
        mask_info_all = json.load(f)
    
    if video_id not in mask_info_all:
        raise ValueError(f"Video ID {video_id} not found in mask_info.json")
    
    return mask_info_all[video_id]


def extract_crops_from_video(video_path, mask_info, scene_graphs, output_dir):
    """Extract object crops from video using mask IDs."""
    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {video_path}")
    
    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Video properties: {total_frames} frames, {fps:.2f} fps")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Collect all mask_ids from scene graphs
    mask_entries = []
    for entry in scene_graphs:
        mask_id = entry.get("mask_id")
        if mask_id and mask_id != "unknown" and mask_id is not None:
            object_name = entry.get("object_name", "unknown")
            action = entry.get("action", "unknown")
            time = entry.get("time", 0)
            mask_entries.append({
                "mask_id": mask_id,
                "object_name": object_name,
                "action": action,
                "time": time
            })
    
    print(f"Found {len(mask_entries)} mask IDs to process")
    
    # Group by frame number for efficiency
    frame_to_masks = {}
    missing_masks = []
    
    for entry in mask_entries:
        mask_id = entry["mask_id"]
        if mask_id not in mask_info:
            missing_masks.append(mask_id)
            continue
        
        frame_number = mask_info[mask_id]["frame_number"]
        bbox = mask_info[mask_id]["bbox"]
        
        if frame_number not in frame_to_masks:
            frame_to_masks[frame_number] = []
        
        frame_to_masks[frame_number].append({
            "mask_id": mask_id,
            "bbox": bbox,
            "object_name": entry["object_name"],
            "action": entry["action"],
            "time": entry["time"]
        })
    
    if missing_masks:
        print(f"Warning: {len(missing_masks)} mask IDs not found in mask_info.json")
        print(f"Sample missing IDs: {missing_masks[:5]}")
    
    print(f"Processing {len(frame_to_masks)} unique frames")
    
    # Process frames (sorted for efficient sequential reading)
    processed_count = 0
    sorted_frames = sorted(frame_to_masks.keys())
    
    for frame_num in sorted_frames:
        # Seek directly to the frame (more efficient than reading sequentially)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        
        # Read the target frame
        ret, frame = cap.read()
        if not ret:
            print(f"Warning: Could not read frame {frame_num}")
            continue
        
        # Extract crops for all masks in this frame
        for mask_data in frame_to_masks[frame_num]:
            mask_id = mask_data["mask_id"]
            bbox = mask_data["bbox"]
            object_name = mask_data["object_name"]
            action = mask_data["action"]
            time = mask_data["time"]
            
            # Extract bounding box coordinates
            xmin, ymin, xmax, ymax = bbox
            xmin, ymin, xmax, ymax = int(xmin), int(ymin), int(xmax), int(ymax)
            
            # Ensure coordinates are within frame bounds
            height, width = frame.shape[:2]
            xmin = max(0, min(xmin, width - 1))
            ymin = max(0, min(ymin, height - 1))
            xmax = max(xmin + 1, min(xmax, width))
            ymax = max(ymin + 1, min(ymax, height))
            
            # Extract crop
            crop = frame[ymin:ymax, xmin:xmax]
            
            # Create filename: mask_id_objectname_action_time_frame.png
            # Sanitize object name for filename
            if object_name:
                safe_object_name = object_name.replace(" ", "_").replace("/", "_").replace("'", "")
                # Remove any other invalid filename characters
                safe_object_name = "".join(c for c in safe_object_name if c.isalnum() or c in ('_', '-', '.'))
            else:
                safe_object_name = "unknown"
            
            # Limit filename length to avoid filesystem issues
            if len(safe_object_name) > 50:
                safe_object_name = safe_object_name[:50]
            
            filename = f"{mask_id}_{safe_object_name}_{action}_{time:.2f}s_frame{frame_num}.png"
            filepath = os.path.join(output_dir, filename)
            
            # Save crop
            cv2.imwrite(filepath, crop)
            processed_count += 1
            
            if processed_count % 100 == 0:
                print(f"Processed {processed_count} crops...")
    
    cap.release()
    print(f"\nExtracted {processed_count} object crops to {output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description='Extract object crops from video using mask IDs from scene graphs'
    )
    parser.add_argument(
        '--jsonl_path',
        type=str,
        required=True,
        help='Path to scene graphs JSONL file'
    )
    parser.add_argument(
        '--video_path',
        type=str,
        required=True,
        help='Path to video file'
    )
    parser.add_argument(
        '--output_dir',
        type=str,
        default=None,
        help='Output directory for crops (default: outputs/object_crops/<video_id>)'
    )
    
    args = parser.parse_args()
    
    # Load scene graphs
    print(f"Loading scene graphs from {args.jsonl_path}")
    scene_graphs = load_scene_graphs(args.jsonl_path)
    
    # Extract video_id from JSONL (from first entry)
    if not scene_graphs:
        raise ValueError("No entries found in JSONL file")
    video_id = scene_graphs[0]["video_id"]
    print(f"Video ID: {video_id}")
    
    # Load mask info
    mask_info = load_mask_info(video_id)
    print(f"Loaded {len(mask_info)} mask entries")
    
    # Determine output directory
    if args.output_dir is None:
        output_dir = f"outputs/object_crops/{video_id}"
    else:
        output_dir = args.output_dir
    
    # Extract crops
    print(f"Extracting crops from video: {args.video_path}")
    extract_crops_from_video(args.video_path, mask_info, scene_graphs, output_dir)
    
    print("Done!")


if __name__ == "__main__":
    main()

