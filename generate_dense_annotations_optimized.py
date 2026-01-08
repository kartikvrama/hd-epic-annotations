import os
import json
import argparse
import torch
import numpy as np
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import List, Tuple, Dict, Iterator
import gc

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
    """Load JSONL file line by line to save memory."""
    data = []
    with open(path, 'r') as f:
        for line in f:
            data.append(json.loads(line))
    return data


def get_video_info(video_path: str) -> Tuple[int, int, float, int]:
    """
    Get video information: width, height, fps, and total frame count.
    """
    if CV2_AVAILABLE:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")
        
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        cap.release()
        return width, height, fps, total_frames
    else:
        # Fallback: use ffprobe
        try:
            cmd = [
                'ffprobe', '-v', 'error', '-select_streams', 'v:0',
                '-show_entries', 'stream=width,height,r_frame_rate,nb_frames',
                '-of', 'json', video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            info = json.loads(result.stdout)
            stream = info['streams'][0]
            
            width = stream['width']
            height = stream['height']
            
            # Parse fps fraction
            fps_str = stream['r_frame_rate']
            if '/' in fps_str:
                num, den = fps_str.split('/')
                fps = float(num) / float(den)
            else:
                fps = float(fps_str)
            
            total_frames = int(stream['nb_frames'])
            
            return width, height, fps, total_frames
        except (subprocess.CalledProcessError, KeyError, json.JSONDecodeError) as e:
            raise ValueError(f"Could not get video info: {e}")


def create_video_segment(input_path: str, output_path: str, start_frame: int, end_frame: int) -> bool:
    """
    Create a video segment from start_frame to end_frame using ffmpeg.
    Returns True if successful, False otherwise.
    """
    try:
        cmd = [
            'ffmpeg', '-i', input_path,
            '-vf', f'start_frame={start_frame}:end_frame={end_frame}',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
            '-y',  # Overwrite output file
            output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Failed to create video segment: {e}")
        return False


def get_stationary_objects(scene_graph_path: str, assoc_info: Dict, video_id: str) -> List[str]:
    """Get stationary objects that don't move in the video."""
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


class TemporalWindowProcessor:
    """Handles processing video in temporal windows to reduce memory usage."""
    
    def __init__(self, video_path: str, window_duration_seconds: int = 300, overlap_seconds: int = 30):
        """
        Initialize temporal window processor.
        
        Args:
            video_path: Path to the video file
            window_duration_seconds: Duration of each window in seconds (default: 5 minutes)
            overlap_seconds: Overlap between consecutive windows in seconds (default: 30 seconds)
        """
        self.video_path = video_path
        self.window_duration = window_duration_seconds
        self.overlap = overlap_seconds
        
        # Get video info
        self.width, self.height, self.fps, self.total_frames = get_video_info(video_path)
        self.total_duration = self.total_frames / self.fps
        
        # Calculate window boundaries
        self.window_duration_frames = int(self.window_duration * self.fps)
        self.overlap_frames = int(self.overlap * self.fps)
        
        print(f"Video info: {self.width}x{self.height}, {self.fps:.2f} fps, "
              f"{self.total_frames} frames, {self.total_duration:.1f}s duration")
        print(f"Window config: {self.window_duration}s ({self.window_duration_frames} frames) "
              f"with {self.overlap}s ({self.overlap_frames} frames) overlap")
    
    def get_windows(self) -> List[Tuple[int, int, str]]:
        """
        Get list of temporal windows as (start_frame, end_frame, temp_video_path) tuples.
        """
        windows = []
        current_start = 0
        
        while current_start < self.total_frames:
            # Calculate end frame for this window
            current_end = min(current_start + self.window_duration_frames, self.total_frames)
            
            # Create temporary video segment
            temp_dir = tempfile.gettempdir()
            window_id = len(windows)
            temp_video_path = os.path.join(temp_dir, f"window_{window_id}_{os.getpid()}.mp4")
            
            if create_video_segment(self.video_path, temp_video_path, current_start, current_end):
                windows.append((current_start, current_end, temp_video_path))
                print(f"Created window {window_id}: frames {current_start}-{current_end} "
                      f"({(current_end-current_start)/self.fps:.1f}s)")
            else:
                print(f"Failed to create window {window_id}, skipping")
            
            # Move to next window with overlap
            if current_end >= self.total_frames:
                break
            current_start = current_end - self.overlap_frames
        
        return windows
    
    def cleanup_windows(self, windows: List[Tuple[int, int, str]]):
        """Clean up temporary video files."""
        for _, _, temp_path in windows:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                    print(f"Cleaned up: {temp_path}")
                except Exception as e:
                    print(f"Warning: Could not remove {temp_path}: {e}")


class MemoryEfficientProcessor:
    """Main processor with memory-efficient video processing."""
    
    def __init__(self, args, assoc_info: Dict, mask_info: Dict):
        self.args = args
        self.assoc_info = assoc_info
        self.mask_info = mask_info
        self.temp_files = []  # Track temporary files for cleanup
        
        # Initialize SAM2 predictor
        self.predictor = self._init_sam2_predictor()
    
    def _init_sam2_predictor(self):
        """Initialize SAM2 video predictor."""
        sam2_checkpoint = "/coc/flash5/kvr6/repos/sam2/checkpoints/sam2.1_hiera_large.pt"
        model_cfg = "configs/sam2.1/sam2.1_hiera_l.yaml"
        
        predictor = build_sam2_video_predictor(model_cfg, sam2_checkpoint)
        print("SAM 2 predictor initialized")
        
        # Enable optimizations
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        
        return predictor
    
    def _cleanup_memory(self):
        """Aggressive memory cleanup."""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()
    
    def _stream_results_to_file(self, output_file: str, window_results: List[Dict]) -> Iterator[str]:
        """
        Stream results directly to file to avoid memory buildup.
        Yields JSON lines for writing.
        """
        # Sort all results by frame number across all windows
        all_frame_data = {}
        for window_result in window_results:
            for frame_idx, objects in window_result.items():
                if frame_idx not in all_frame_data:
                    all_frame_data[frame_idx] = []
                all_frame_data[frame_idx].extend(objects)
        
        # Sort by frame number and yield JSON lines
        for frame_idx in sorted(all_frame_data.keys()):
            frame_data = {
                "frame_number": frame_idx,
                "objects": all_frame_data[frame_idx]
            }
            yield json.dumps(frame_data)
    
    def _process_single_window(self, window_info: Tuple[int, int, str], 
                              obj_prompts: Dict, frame_interval: int) -> Dict[int, List[Dict]]:
        """
        Process a single temporal window.
        Returns dictionary mapping frame_idx to list of object annotations.
        """
        start_frame, end_frame, temp_video_path = window_info
        print(f"\nProcessing window: frames {start_frame}-{end_frame}")
        
        window_results = {}
        
        try:
            # Initialize inference state for this window
            self._cleanup_memory()
            print(f"Initializing inference state for window")
            
            with torch.autocast(device_type='cuda', dtype=torch.bfloat16):
                inference_state = self.predictor.init_state(
                    video_path=temp_video_path,
                    offload_video_to_cpu=True,
                    offload_state_to_cpu=False
                )
                
                print(f"Inference state initialized. GPU memory: "
                      f"{torch.cuda.memory_allocated() / 1024**3:.2f} GB")
                
                # Add prompts for objects that have data in this window
                obj_id_to_assoc_id = {}
                
                for assoc_id, assoc_data in self.assoc_info[self.args.video_id].items():
                    obj_name = assoc_data['name']
                    obj_id = int(assoc_id.split('_')[-1]) if '_' in assoc_id else hash(assoc_id) % 1000
                    obj_id_to_assoc_id[obj_id] = assoc_id
                    
                    # Check if this object has data in current window
                    window_prompts = []
                    for track in assoc_data['tracks']:
                        for mask_id in track['masks']:
                            if mask_id in self.mask_info[self.args.video_id]:
                                m_data = self.mask_info[self.args.video_id][mask_id]
                                frame_num = m_data['frame_number']
                                if start_frame <= frame_num < end_frame:
                                    window_prompts.append({
                                        "frame_idx": frame_num - start_frame,  # Adjust for window
                                        "bbox": m_data['bbox']
                                    })
                    
                    if window_prompts:
                        print(f"Adding {len(window_prompts)} prompts for {obj_name}")
                        
                        # Add prompts to predictor
                        for prompt in window_prompts:
                            bbox = prompt['bbox']
                            # Apply scale factor if needed
                            if self.args.video_scale_factor < 1.0:
                                scaled_bbox = [coord * self.args.video_scale_factor for coord in bbox]
                            else:
                                scaled_bbox = bbox
                            
                            _, out_obj_ids, out_mask_logits = self.predictor.add_new_points_or_box(
                                inference_state=inference_state,
                                frame_idx=prompt['frame_idx'],
                                obj_id=obj_id,
                                box=np.array(scaled_bbox, dtype=np.float32),
                            )
                
                # Propagate through window
                print("Starting window propagation...")
                frame_count = 0
                last_print = -1
                
                for out_frame_idx, out_obj_ids, out_mask_logits in self.predictor.propagate_in_video(inference_state):
                    # Adjust frame index to original video coordinates
                    global_frame_idx = out_frame_idx + start_frame
                    
                    # Apply frame interval filter
                    if global_frame_idx % frame_interval != 0:
                        continue
                    
                    frame_count += 1
                    
                    # Print progress
                    if global_frame_idx - last_print >= 100 or frame_count == 1:
                        print(f"Window frame {global_frame_idx} (local: {out_frame_idx}) - "
                              f"processed {frame_count} frames")
                        last_print = global_frame_idx
                    
                    # Process detected objects
                    for i, out_obj_id in enumerate(out_obj_ids):
                        mask = (out_mask_logits[i] > 0.0).cpu().numpy()
                        if mask.any():
                            # Convert mask to bbox
                            y, x = np.where(mask[0])
                            bbox = [float(np.min(x)), float(np.min(y)), 
                                   float(np.max(x)), float(np.max(y))]
                            
                            # Scale bbox back if video was resized
                            if self.args.video_scale_factor < 1.0:
                                original_bbox = [coord / self.args.video_scale_factor for coord in bbox]
                            else:
                                original_bbox = bbox
                            
                            # Store result
                            assoc_id = obj_id_to_assoc_id.get(out_obj_id, str(out_obj_id))
                            
                            if global_frame_idx not in window_results:
                                window_results[global_frame_idx] = []
                            
                            window_results[global_frame_idx].append({
                                "assoc_id": assoc_id,
                                "assoc_name": self.assoc_info[self.args.video_id][assoc_id]['name'],
                                "bbox": original_bbox
                            })
                
                print(f"Window completed: {frame_count} frames processed")
                
                # Clean up inference state
                self.predictor.reset_state(inference_state)
                
        except Exception as e:
            print(f"Error processing window: {e}")
            raise
        
        finally:
            # Clean up temporary video file
            if os.path.exists(temp_video_path):
                try:
                    os.remove(temp_video_path)
                    print(f"Cleaned up window video: {temp_video_path}")
                except Exception as e:
                    print(f"Warning: Could not remove {temp_video_path}: {e}")
        
        return window_results
    
    def process_video(self):
        """Main processing function with temporal windows."""
        print(f"Starting memory-efficient processing for video: {self.args.video_id}")
        
        # Create output directory
        os.makedirs(self.args.output_dir, exist_ok=True)
        
        # Save stationary objects
        scene_graph_path = os.path.join(self.args.scene_graph_dir, 
                                       f"scene_graphs_{self.args.video_id}.jsonl")
        stationary = get_stationary_objects(scene_graph_path, self.assoc_info, self.args.video_id)
        stationary_file = os.path.join(self.args.output_dir, 
                                      f"stationary_objects_{self.args.video_id}.txt")
        with open(stationary_file, 'w') as f:
            for obj in stationary:
                f.write(f"{obj}\n")
        print(f"Saved stationary objects to {stationary_file}")
        
        if self.args.video_id not in self.assoc_info:
            print(f"No movement data for {self.args.video_id}. Skipping tracking.")
            return
        
        # Initialize temporal window processor
        window_processor = TemporalWindowProcessor(
            video_path=self.args.video_path,
            window_duration_seconds=300,  # 5 minutes
            overlap_seconds=30           # 30 seconds
        )
        
        # Get temporal windows
        windows = window_processor.get_windows()
        if not windows:
            print("No windows could be created, aborting")
            return
        
        print(f"Created {len(windows)} temporal windows")
        
        # Process each window
        all_window_results = []
        
        try:
            for i, window_info in enumerate(windows):
                print(f"\n{'='*60}")
                print(f"PROCESSING WINDOW {i+1}/{len(windows)}")
                print(f"{'='*60}")
                
                # Check memory before processing
                if torch.cuda.is_available():
                    memory_before = torch.cuda.memory_allocated() / 1024**3
                    print(f"GPU memory before window {i}: {memory_before:.2f} GB")
                
                window_results = self._process_single_window(
                    window_info, 
                    self.assoc_info[self.args.video_id], 
                    self.args.frame_interval
                )
                
                all_window_results.append(window_results)
                
                # Check memory after processing
                if torch.cuda.is_available():
                    memory_after = torch.cuda.memory_allocated() / 1024**3
                    print(f"GPU memory after window {i}: {memory_after:.2f} GB")
                
                # Aggressive cleanup between windows
                self._cleanup_memory()
                
                if torch.cuda.is_available():
                    memory_cleaned = torch.cuda.memory_allocated() / 1024**3
                    print(f"GPU memory after cleanup: {memory_cleaned:.2f} GB")
        
        finally:
            # Clean up all windows
            window_processor.cleanup_windows(windows)
        
        # Write results to file using streaming approach
        output_file = os.path.join(self.args.output_dir, 
                                  f"dense_annotations_{self.args.video_id}.jsonl")
        
        print(f"\nWriting results to {output_file}")
        with open(output_file, 'w') as f:
            for json_line in self._stream_results_to_file(output_file, all_window_results):
                f.write(json_line + "\n")
        
        print(f"\nProcessing completed successfully!")
        print(f"Results saved to: {output_file}")
        print(f"Total windows processed: {len(windows)}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video_id", type=str, required=True)
    parser.add_argument("--video_path", type=str, 
                       default="/coc/flash5/kvr6/data/hd-epic-data-files/HD-EPIC/Videos")
    parser.add_argument("--scene_graph_dir", type=str, default="outputs/scene_graphs")
    parser.add_argument("--assoc_info", type=str, 
                       default="scene-and-object-movements/assoc_info.json")
