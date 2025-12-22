import os
import json
import pickle
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import pandas as pd

from utils import extract_touches_from_track, seconds_to_minutes_seconds

BAR_WIDTH = 0.5

def plot_object_touches(track_sequence, ax, y_position):
    """Plot object pick-drop instances."""
    touch_points = extract_touches_from_track(track_sequence)
    
    if len(touch_points) < 2:
        return  # Skip objects with less than 2 touches
    
    # Plot all touch points
    plot_x = []
    plot_o = []
    plot_points = []
    for touch in touch_points:
        plot_x.append(touch["pick"])
        plot_o.append(touch["drop"])
        plot_points.extend([touch["pick"], touch["drop"]])
    
    # Plot main track line (light gray background)
    if plot_points:
        ax.plot(plot_points, [y_position] * len(plot_points), "-", color="black", linewidth=3, alpha=0.2)
        ax.plot(plot_x, [y_position] * len(plot_x), "x", color="gray", markersize=10, alpha=0.8)
        ax.plot(plot_o, [y_position] * len(plot_o), "x", color="gray", markersize=10, alpha=0.8)


def plot_object_inuse_segments(inuse_segments, ax, y_position):
    for segment in inuse_segments:
        ax.fill_betweenx(
            [y_position - BAR_WIDTH/2, y_position + BAR_WIDTH/2],
            segment["start_timestamp"],
            segment["end_timestamp"],
            color="red",
            alpha=0.3,
        )


def return_inuse_segments_per_object(action_object_mapping: [dict], narrations: pd.DataFrame) -> dict:
    inuse_segment_dict = {}
    for i, action_object_dict in enumerate(action_object_mapping):
        if i % 10 == 0:
            print(f"[Getting inuse segments] Processing action object {i} of {len(action_object_mapping)}")
        narration_id = action_object_dict["trace_id"]
        narration = narrations[narrations.unique_narration_id.eq(narration_id)]
        if len(narration) == 0:
            raise ValueError(f"Narration {narration_id} not found in data_narrations")
        elif len(narration) > 1:
            raise ValueError(f"Multiple narrations found for {narration_id}")
        narration = narration.iloc[0]
        start_timestamp = narration["start_timestamp"]
        end_timestamp = narration["end_timestamp"]
        objects_used = action_object_dict["objects_used"]
        for object_used in objects_used:
            if object_used not in inuse_segment_dict:
                inuse_segment_dict[object_used] = []
            inuse_segment_dict[object_used].append({
                    "start_timestamp": start_timestamp,
                    "end_timestamp": end_timestamp,
                    "objects_used": objects_used,
                })
    return inuse_segment_dict


def main():
    with open("linked_objects_gpt-oss:20b_P01-20240203-123350_unfiltered.jsonl", "r") as f:
        action_object_mapping_video = [json.loads(line) for line in f]

    video_id = "P01-20240203-123350"

    # Load association info
    with open("scene-and-object-movements/assoc_info.json") as f:
        object_movements_all = json.load(f)
    object_movements_video = object_movements_all[video_id]

    ## Load action narrations
    with open("narrations-and-action-segments/HD_EPIC_Narrations.pkl", "rb") as f:
        action_narrations = pickle.load(f)
    action_narrations_video = action_narrations[action_narrations.unique_narration_id.str.startswith(video_id)]
    action_narrations_video = action_narrations_video.sort_values(by="start_timestamp")

    os.makedirs("plots", exist_ok=True)

    try:    
        inuse_segment_dict = return_inuse_segments_per_object(action_object_mapping_video, action_narrations_video)
    except Exception as e:
        print(f"Error returning inuse segments per object: {e}")
        import pdb; pdb.set_trace()

    fig, ax = plt.subplots(figsize=(25, 15))
    for i, (_, association_info) in enumerate(object_movements_video.items(), 1):
        if i % 10 == 0:
            print(f"[Plotting object touches] Processing object {i} ({association_info['name']}) of {len(object_movements_video)}")
        y_position = i
        plot_object_touches(association_info["tracks"], ax, y_position)
        if not association_info["name"] in inuse_segment_dict:
            continue
        plot_object_inuse_segments(inuse_segment_dict[association_info["name"]], ax, y_position)


    ax.set_xlabel("Time (minutes:seconds)")
    video_end_time = action_narrations_video.iloc[-1]["end_timestamp"]
    # ## convert x-axis to minutes:seconds
    tick_interval = 30  # seconds
    xticks = [i for i in range(0, int(video_end_time)+tick_interval, tick_interval)]
    ax.set_xticks(xticks)
    ax.set_xticklabels([seconds_to_minutes_seconds(i) for i in xticks], rotation=60)

    ax.set_ylabel("Object")
    # ## set y axis tick labels to the object names
    # ax.set_yticks([i*BAR_WIDTH for i in range(len(object_movements_video))])
    ax.set_yticks([i for i in range(1, len(object_movements_video)+1)])
    ax.set_yticklabels([v["name"] for v in object_movements_video.values()])
    ax.legend()
    fig.tight_layout()
    ## turn on grid
    ax.grid(True)
    fig.savefig(f"plots/object_touches_usage_{video_id}.png")


if __name__ == "__main__":
    main()
