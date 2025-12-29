import os
import json
import argparse
import torch
import numpy as np
from pathlib import Path

# Assuming SAM 2 is installed and available in the environment
try:
    from sam2.build_sam import build_sam2_video_predictor
except ImportError:
    print("SAM 2 not found. Please ensure it is installed.")

def load_jsonl(path):
    data = []
    with open(path, 'r') as f:
        for line in f:
            data.append(json.loads(line))
    return data

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

def process_video(video_id, video_path, scene_graph_path, assoc_info_path, mask_info_path, output_dir):
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

    # 2. Initialize SAM 2 Video Predictor
    # Note: Model paths and config should be adjusted based on server setup
    sam2_checkpoint = "checkpoints/sam2_hiera_large.pt"
    model_cfg = "sam2_hiera_l.yaml"
    predictor = build_sam2_video_predictor(model_cfg, sam2_checkpoint)

    # 3. Process each manipulated object (association)
    dense_annotations = []
    
    # We need to organize frames for SAM 2. SAM 2 usually takes a directory of JPEG frames.
    # For this implementation, we assume frames are extracted or SAM 2 can handle the video.
    # Here we focus on the logic of multi-point initialization.
    
    inference_state = predictor.init_state(video_path=video_path)

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
            _, out_obj_ids, out_mask_logits = predictor.add_new_points_or_box(
                inference_state=inference_state,
                frame_idx=prompt['frame_idx'],
                obj_id=int(assoc_id.split('_')[-1]) if '_' in assoc_id else hash(assoc_id) % 1000,
                box=np.array(prompt['bbox'], dtype=np.float32),
            )

    # 4. Propagate bidirectionally
    video_segments = {} # obj_id -> frame_idx -> bbox
    for out_frame_idx, out_obj_ids, out_mask_logits in predictor.propagate_in_video(inference_state):
        for i, out_obj_id in enumerate(out_obj_ids):
            mask = (out_mask_logits[i] > 0.0).cpu().numpy()
            if mask.any():
                # Convert mask to bbox
                y, x = np.where(mask[0])
                bbox = [float(np.min(x)), float(np.min(y)), float(np.max(x)), float(np.max(y))]
                
                if out_obj_id not in video_segments:
                    video_segments[out_obj_id] = {}
                video_segments[out_obj_id][out_frame_idx] = bbox

    # 5. Save results
    output_file = os.path.join(output_dir, f"dense_annotations_{video_id}.jsonl")
    with open(output_file, 'w') as f:
        for frame_idx in sorted(set(idx for seg in video_segments.values() for idx in seg.keys())):
            frame_data = {"frame_number": frame_idx, "objects": []}
            for obj_id, segments in video_segments.items():
                if frame_idx in segments:
                    # Find original assoc_id and name
                    # (In a real implementation, we'd maintain a mapping)
                    frame_data["objects"].append({
                        "assoc_id": str(obj_id),
                        "bbox": segments[frame_idx]
                    })
            f.write(json.dumps(frame_data) + "\n")
    
    predictor.reset_state(inference_state)
    print(f"Saved dense annotations to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video_id", type=str, required=True)
    parser.add_argument("--video_path", type=str, default="/Users/kartikramachandruni/Documents/data/hd-epic-videos")
    parser.add_argument("--scene_graph_dir", type=str, default="outputs")
    parser.add_argument("--assoc_info", type=str, default="scene-and-object-movements/assoc_info.json")
    parser.add_argument("--mask_info", type=str, default="scene-and-object-movements/mask_info.json")
    parser.add_argument("--output_dir", type=str, default="outputs")
    args = parser.parse_args()

    v_path = os.path.join(args.video_path, f"{args.video_id}.mp4")
    sg_path = os.path.join(args.scene_graph_dir, f"scene_graphs_{args.video_id}.jsonl")
    
    process_video(args.video_id, v_path, sg_path, args.assoc_info, args.mask_info, args.output_dir)
