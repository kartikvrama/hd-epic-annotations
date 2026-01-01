import os
import json
import pickle
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import pandas as pd
import argparse
from utils import extract_touches_from_track, seconds_to_minutes_seconds, return_event_history_sorted
import pdb

parser = argparse.ArgumentParser(description='Process a video by its ID.')
parser.add_argument('--video_id', required=True, type=str, help='ID of the video')
args = parser.parse_args()

BAR_WIDTH = 0.5
VERBOSE = True


def verbose_print(*args, **kwargs):
    """Print only if VERBOSE is True."""
    if VERBOSE:
        print(*args, **kwargs)


def plot_object_touches(track_sequence, axis, y_position):
    """Plot object pick-drop instances."""
    touch_points = extract_touches_from_track(track_sequence)
    plot_x = []
    plot_o = []
    plot_points = []
    for touch in touch_points:
        plot_x.append(touch["pick"])
        plot_o.append(touch["drop"])
        plot_points.extend([touch["pick"], touch["drop"]])
    axis.plot(plot_points, [y_position] * len(plot_points), "-", color="black", linewidth=3, alpha=0.6)
    axis.plot(plot_x, [y_position] * len(plot_x), "x", color="gray", markersize=10, alpha=0.8)
    axis.plot(plot_o, [y_position] * len(plot_o), "o", color="gray", markersize=10, alpha=0.8)


def plot_object_usage_segments(object_labels_array, axis, all_object_labels):
    for object_label in object_labels_array:
        if object_label["object_name"] not in all_object_labels:
            continue
        if object_label.get("is_used") is None:
            print(f"WARNING: Object {object_label['object_name']} has invalid usage label between {object_label['time_start']} and {object_label['time_end']}")
            continue
        elif object_label["is_used"] == False: ## Skip if object was not used
            continue
        y_position = all_object_labels.index(object_label["object_name"])
        verbose_print(f"Object {object_label['object_name']} used between {object_label['time_start']} and {object_label['time_end']}")
        axis.fill_betweenx(
            [y_position - BAR_WIDTH/2, y_position + BAR_WIDTH/2],
            object_label["time_start"],
            object_label["time_end"],
            color="red",
            alpha=0.3,
        )


def combine_object_labels_from_usage_labels(object_usage_labels: [dict], scene_graphs: [dict], mask_fixtures: dict) -> dict:
    """
    Process object_usage_labels jsonl entries to create object_labels_array.
    Includes all entries regardless of is_used status.
    Uses scene graphs instead of event_history to extract mask_frame_ids.
    """
    object_labels_array = []
    
    for i, usage_label in enumerate(object_usage_labels):
        if i % 10 == 0:
            print(f"[Getting inuse segments] Processing usage label {i} of {len(object_usage_labels)}")
        
        object_name = usage_label["object_name"]
        start_timestamp = usage_label["time_start"]
        end_timestamp = usage_label["time_end"]
        
        # Filter scene graphs for this object and time range
        scene_graphs_trimmed = [
            sg for sg in scene_graphs
            if sg.get("object_name") == object_name
            and sg.get("time") is not None
            and start_timestamp <= sg["time"] <= end_timestamp
            and sg.get("action") != "INITIAL"  # Skip INITIAL entries
        ]
        
        mask_frame_ids = []
        for scene_graph in scene_graphs_trimmed:
            mask_id = scene_graph.get("mask_id")
            if mask_id is None:
                continue
            
            frame_number = mask_fixtures[mask_id]["frame_number"] if mask_id in mask_fixtures else None
            mask_bbox = mask_fixtures[mask_id]["bbox"] if mask_id in mask_fixtures else None
            mask_frame_ids.append({
                "time": scene_graph["time"],
                "action_type": scene_graph["action"],
                "mask_id": mask_id,
                "frame_number": frame_number,
                "mask_bbox": mask_bbox,
            })
        
        object_labels_array.append({
            "object_name": object_name,
            "time_start": start_timestamp,
            "time_end": end_timestamp,
            "is_used": usage_label.get("llm_response_json", {}).get("is_used", None),
            "mask_frame_ids": mask_frame_ids,
        })
    
    return object_labels_array


def main():
    with open("scene-and-object-movements/assoc_info.json", encoding='utf-8') as f:
        object_movements_all = json.load(f)

    with open("scene-and-object-movements/mask_info.json", "r", encoding='utf-8') as f:
        mask_fixtures_all = json.load(f)

    with open("narrations-and-action-segments/HD_EPIC_Narrations.pkl", "rb") as f:
        action_narrations_all = pickle.load(f)

    # Read object usage labels from jsonl file
    object_usage_labels_path = f"outputs/object_usage_labels/object_usage_labels_{args.video_id}.jsonl"
    if not os.path.exists(object_usage_labels_path):
        raise FileNotFoundError(f"Object usage labels file not found: {object_usage_labels_path}")
    
    with open(object_usage_labels_path, "r") as f:
        object_usage_labels = [json.loads(line) for line in f]

    # Read scene graphs from jsonl file
    scene_graphs_path = f"outputs/scene_graphs/scene_graphs_{args.video_id}.jsonl"
    if not os.path.exists(scene_graphs_path):
        raise FileNotFoundError(f"Scene graphs file not found: {scene_graphs_path}")
    
    with open(scene_graphs_path, "r") as f:
        scene_graphs = [json.loads(line) for line in f]

    object_movements = object_movements_all[args.video_id]
    ## Sort object movements by start timestamp
    sorted_keys = sorted(object_movements.keys(), key=lambda elem: object_movements[elem]["tracks"][0]["time_segment"][0])
    object_movements = {k: object_movements[k] for k in sorted_keys}
    mask_fixtures = mask_fixtures_all[args.video_id]

    action_narrations = action_narrations_all[action_narrations_all.unique_narration_id.str.startswith(args.video_id)]
    action_narrations = action_narrations.sort_values(by="start_timestamp")

    os.makedirs("plots", exist_ok=True)

    try:    
        object_labels_array = combine_object_labels_from_usage_labels(object_usage_labels, scene_graphs, mask_fixtures)
    except Exception as e:
        print(f"Error returning inuse segments per object: {e}")
        pdb.set_trace()

    fig, ax = plt.subplots(figsize=(25, 15))
    all_object_labels = list(
        [label["name"] for label in object_movements.values() if not label["name"].startswith("Track")]
    )
    for _, association_data in object_movements.items():
        if not association_data["name"] in all_object_labels:
            continue
        plot_object_touches(
            track_sequence=association_data["tracks"], axis=ax, y_position=all_object_labels.index(association_data["name"])
        )
    plot_object_usage_segments(object_labels_array, ax, all_object_labels)

    ax.set_xlabel("Time (minutes:seconds)")
    video_end_time = action_narrations.iloc[-1]["end_timestamp"]
    # ## convert x-axis to minutes:seconds
    tick_interval = 30  # seconds
    xticks = [i for i in range(0, int(video_end_time)+tick_interval, tick_interval)]
    ax.set_xticks(xticks)
    ax.set_xticklabels([seconds_to_minutes_seconds(i) for i in xticks], rotation=60)

    ax.set_ylabel("Object")
    # ## set y axis tick labels to the object names
    ax.set_yticks([i for i in range(len(all_object_labels))])
    ax.set_yticklabels(all_object_labels)
    ax.legend()
    fig.tight_layout()
    ## turn on grid
    ax.grid(True)
    fig.savefig(f"plots/object_touches_usage_{args.video_id}.png")


if __name__ == "__main__":
    main()
