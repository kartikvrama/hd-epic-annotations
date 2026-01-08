#!/usr/bin/env python3
"""
Simple debugging script to visualize bounding boxes on video.
Usage: python visualize_annotations.py <video_path> <annotations_jsonl> [output_video]
"""

import cv2
import json
import sys
import os
from pathlib import Path

def visualize_annotations(video_path, annotations_path, output_path=None):
    """Draw bounding boxes from annotations on video frames."""
    
    # Load annotations
    annotations = {}
    with open(annotations_path, 'r') as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                frame_num = data['frame_number']
                annotations[frame_num] = data.get('objects', [])
    
    print(f"Loaded {len(annotations)} annotated frames")
    
    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video {video_path}")
        return
    
    # Get video properties
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"Video: {width}x{height} @ {fps} fps, {total_frames} frames")
    
    # Setup output video writer
    if output_path is None:
        output_path = annotations_path.replace('.jsonl', '_visualized.mp4')
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    frame_idx = 0
    annotated_count = 0
    
    # Colors for different objects (cycling through a palette)
    colors = [
        (0, 255, 0),    # Green
        (255, 0, 0),    # Blue
        (0, 0, 255),    # Red
        (255, 255, 0),  # Cyan
        (255, 0, 255),  # Magenta
        (0, 255, 255),  # Yellow
        (128, 0, 128),  # Purple
        (255, 165, 0),  # Orange
    ]
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Draw bounding boxes if this frame has annotations
        if frame_idx in annotations:
            objects = annotations[frame_idx]
            annotated_count += 1
            
            for i, obj in enumerate(objects):
                bbox = obj['bbox']  # [xmin, ymin, xmax, ymax]
                assoc_id = obj.get('assoc_id', 'unknown')
                
                # Convert to integers
                x1, y1, x2, y2 = [int(coord) for coord in bbox]
                
                # Get color for this object (based on assoc_id hash)
                color_idx = hash(assoc_id) % len(colors)
                color = colors[color_idx]
                
                # Draw rectangle
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                
                # Draw label
                label = f"{assoc_id}"
                label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                label_y = max(y1 - 5, label_size[1])
                cv2.rectangle(frame, (x1, label_y - label_size[1] - 2), 
                            (x1 + label_size[0], label_y), color, -1)
                cv2.putText(frame, label, (x1, label_y), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Draw frame number
        cv2.putText(frame, f"Frame: {frame_idx}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        out.write(frame)
        frame_idx += 1
        
        if frame_idx % 100 == 0:
            print(f"Processed {frame_idx}/{total_frames} frames...")
    
        if frame_idx > 500: ## Checking if script is running
            break

    cap.release()
    out.release()
    
    print(f"\nDone! Processed {frame_idx} frames, {annotated_count} had annotations")
    print(f"Output saved to: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python visualize_annotations.py <video_path> <annotations_jsonl> [output_video]")
        print("\nExample:")
        print("  python visualize_annotations.py \\")
        print("    /coc/flash5/kvr6/data/hd-epic-data-files/HD-EPIC/Videos/P01/P01-20240202-171220.mp4 \\")
        print("    outputs/dense_annotations_P01-20240202-171220.jsonl")
        sys.exit(1)
    
    video_path = sys.argv[1]
    annotations_path = sys.argv[2]
    output_path = sys.argv[3] if len(sys.argv) > 3 else None
    
    if not os.path.exists(video_path):
        print(f"Error: Video file not found: {video_path}")
        sys.exit(1)
    
    if not os.path.exists(annotations_path):
        print(f"Error: Annotations file not found: {annotations_path}")
        sys.exit(1)
    
    visualize_annotations(video_path, annotations_path, output_path)

