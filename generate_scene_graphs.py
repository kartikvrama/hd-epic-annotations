import os
import json
import pickle
import pandas as pd
import argparse
from utils import generate_time_wise_scene_graphs, seconds_to_minutes_seconds

parser = argparse.ArgumentParser(description='Generate time-wise scene graphs for a video.')
parser.add_argument('--video_id', required=True, type=str, help='ID of the video')
args = parser.parse_args()


def format_scene_graph(scene_graph: dict) -> str:
    """Format a scene graph dictionary into a human-readable string."""
    lines = []
    # Sort nodes for consistent output
    sorted_nodes = sorted(scene_graph.keys())
    for node in sorted_nodes:
        objects = scene_graph[node]
        if objects:  # Only show nodes with objects
            objects_str = ", ".join(sorted(objects))
            lines.append(f"  {node}: [{objects_str}]")
    return "\n".join(lines)


def get_participant_id(video_id: str) -> str:
    """Extract participant ID from video ID (e.g., 'P01' from 'P01-20240202-110250')."""
    return video_id.split('-')[0]


def load_high_level_activities(participant_id: str) -> pd.DataFrame:
    """Load high-level activities CSV for the given participant."""
    csv_path = f"high-level/activities/{participant_id}_recipe_timestamps.csv"
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"High-level activities file not found: {csv_path}")
    return pd.read_csv(csv_path)


def get_activity_at_time(activities_df: pd.DataFrame, video_id: str, timestamp: float, video_end_time: float = None) -> dict:
    """
    Get the high-level activity active at the given timestamp.
    
    Returns a dictionary with:
    - 'high_level_activity_label': activity label or None
    - 'recipe_id': recipe ID or None
    """
    # Filter activities for this video
    video_activities = activities_df[activities_df['video_id'] == video_id].copy()
    
    if len(video_activities) == 0:
        return {'high_level_activity_label': None, 'recipe_id': None}
    
    # Convert end_time to float, handling "end" values
    def parse_end_time(end_time, default_end):
        if isinstance(end_time, str) and end_time.lower() == 'end':
            return default_end if default_end is not None else float('inf')
        try:
            return float(end_time)
        except (ValueError, TypeError):
            return default_end if default_end is not None else float('inf')
    
    # Find activity that contains this timestamp
    # Activities appear to use exclusive end times (next activity starts where previous ends)
    # But "end" activities should be inclusive up to video_end_time
    for _, row in video_activities.iterrows():
        start_time = float(row['start_time'])
        end_time_raw = row['end_time']
        is_end_activity = isinstance(end_time_raw, str) and end_time_raw.lower() == 'end'
        end_time = parse_end_time(end_time_raw, video_end_time)
        
        # For "end" activities, use <= to include video_end_time
        # For regular activities, use < to match the exclusive boundary
        if is_end_activity:
            if start_time <= timestamp <= end_time:
                return {
                    'high_level_activity_label': row['high_level_activity_label'] if pd.notna(row['high_level_activity_label']) else None,
                    'recipe_id': row['recipe_id'] if pd.notna(row['recipe_id']) else None
                }
        else:
            if start_time <= timestamp < end_time:
                return {
                    'high_level_activity_label': row['high_level_activity_label'] if pd.notna(row['high_level_activity_label']) else None,
                    'recipe_id': row['recipe_id'] if pd.notna(row['recipe_id']) else None
                }
    
    return {'high_level_activity_label': None, 'recipe_id': None}


def get_narrations_at_time(narrations_df: pd.DataFrame, video_id: str, timestamp: float) -> list:
    """
    Get all narrations active at the given timestamp.
    
    Returns a list of dictionaries, each containing:
    - 'narration': narration text
    - 'start_timestamp': start time
    - 'end_timestamp': end time
    """
    # Filter narrations for this video
    video_narrations = narrations_df[
        narrations_df['unique_narration_id'].str.startswith(video_id)
    ].copy()
    
    if len(video_narrations) == 0:
        return []
    
    # Find narrations that overlap with this timestamp
    active_narrations = []
    for _, row in video_narrations.iterrows():
        start_ts = float(row['start_timestamp'])
        end_ts = float(row['end_timestamp'])
        
        if start_ts <= timestamp <= end_ts:
            active_narrations.append({
                'narration': row['narration'] if pd.notna(row['narration']) else '',
                'start_timestamp': start_ts,
                'end_timestamp': end_ts
            })
    
    # Sort by start timestamp
    active_narrations.sort(key=lambda x: x['start_timestamp'])
    return active_narrations


def main():
    # Load data files
    print(f"Loading data for video: {args.video_id}")
    
    with open("scene-and-object-movements/assoc_info.json", "r", encoding='utf-8') as f:
        object_movements_all = json.load(f)
    
    with open("scene-and-object-movements/mask_info.json", "r", encoding='utf-8') as f:
        mask_fixtures_all = json.load(f)
    
    # Get data for the specific video
    if args.video_id not in object_movements_all:
        raise ValueError(f"Video ID {args.video_id} not found in assoc_info.json")
    
    if args.video_id not in mask_fixtures_all:
        raise ValueError(f"Video ID {args.video_id} not found in mask_info.json")
    
    object_movements = object_movements_all[args.video_id]
    mask_fixtures = mask_fixtures_all[args.video_id]
    
    # Load high-level activities
    participant_id = get_participant_id(args.video_id)
    print(f"Loading high-level activities for participant: {participant_id}")
    activities_df = load_high_level_activities(participant_id)
    
    # Load narrations
    print("Loading narrations...")
    with open("narrations-and-action-segments/HD_EPIC_Narrations.pkl", "rb") as f:
        narrations_df = pickle.load(f)
    
    # Generate time-wise scene graphs
    print("Generating time-wise scene graphs...")
    scene_graphs = generate_time_wise_scene_graphs(object_movements, mask_fixtures)
    
    # Determine video end time (use the last timestamp in scene graphs)
    video_end_time = None
    if len(scene_graphs) > 0:
        video_end_time = max(entry["time"] for entry in scene_graphs)
    
    # Prepare JSONL entries
    jsonl_entries = []
    
    # Format output (text file)
    output_lines = []
    output_lines.append("=" * 80)
    output_lines.append(f"Time-wise Scene Graphs for Video: {args.video_id}")
    output_lines.append("=" * 80)
    output_lines.append("")
    output_lines.append("Scene graphs are generated from object movements.")
    output_lines.append("Each entry shows the state after an event (PICK or DROP) occurs.")
    output_lines.append("")
    output_lines.append("-" * 80)
    output_lines.append("")
    
    event_num = 0
    for i, entry in enumerate(scene_graphs):
        time = entry["time"]
        action = entry["action"]
        object_name = entry["object_name"]
        mask_id = entry.get("mask_id")
        scene_graph = entry["scene_graph"]
        time_str = seconds_to_minutes_seconds(time)
        
        # Get high-level activity at this timestamp
        activity_info = get_activity_at_time(activities_df, args.video_id, time, video_end_time)
        
        # Get narrations at this timestamp
        narrations = get_narrations_at_time(narrations_df, args.video_id, time)
                
        # Format header
        if action == "INITIAL":
            output_lines.append(f"Initial State | Time: {time:.2f}s ({time_str})")
        else:
            event_num += 1
            output_lines.append(f"Event #{event_num} | Time: {time:.2f}s ({time_str}) | {action}: {object_name}")
        
        # Add high-level activity information
        if activity_info['high_level_activity_label']:
            activity_str = activity_info['high_level_activity_label']
            if activity_info['recipe_id']:
                activity_str += f" [Recipe: {activity_info['recipe_id']}]"
            output_lines.append(f"High-Level Activity: {activity_str}")
        
        # Add narrations if any
        if narrations:
            output_lines.append("Active Narrations:")
            for narr in narrations:
                narr_time_str = f"{narr['start_timestamp']:.2f}s - {narr['end_timestamp']:.2f}s"
                output_lines.append(f"  [{narr_time_str}] {narr['narration']}")
        
        output_lines.append("-" * 80)
        formatted_graph = format_scene_graph(scene_graph)
        if formatted_graph:
            output_lines.append(formatted_graph)
        else:
            output_lines.append("  (empty scene graph)")
        output_lines.append("")
        
        # Create JSONL entry
        jsonl_entry = {
            "video_id": args.video_id,
            "time": time,
            "time_str": time_str,
            "action": action,
            "object_name": object_name,
            "mask_id": mask_id,
            "high_level_activity": activity_info,
            "narrations": narrations,
            "scene_graph": scene_graph
        }
        jsonl_entries.append(jsonl_entry)
    
    # Write text file
    os.makedirs("outputs/scene_graphs", exist_ok=True)
    output_filename = f"outputs/scene_graphs/scene_graphs_{args.video_id}.txt"
    
    with open(output_filename, "w", encoding='utf-8') as f:
        f.write("\n".join(output_lines))
    
    print(f"Scene graphs saved to: {output_filename}")
    
    # Write JSONL file
    jsonl_filename = f"outputs/scene_graphs/scene_graphs_{args.video_id}.jsonl"
    with open(jsonl_filename, "w", encoding='utf-8') as f:
        for entry in jsonl_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    print(f"JSONL file saved to: {jsonl_filename}")
    print(f"Total events processed: {len(scene_graphs)}")


if __name__ == "__main__":
    main()

