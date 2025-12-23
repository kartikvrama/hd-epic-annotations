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
        y_position = all_object_labels.index(object_label["object_name"])
        print(f"Object {object_label['object_name']} used between {object_label['usage_start_timestamp']} and {object_label['usage_end_timestamp']}")
        axis.fill_betweenx(
            [y_position - BAR_WIDTH/2, y_position + BAR_WIDTH/2],
            object_label["usage_start_timestamp"],
            object_label["usage_end_timestamp"],
            color="red",
            alpha=0.3,
        )



def combine_object_labels(action_object_mapping: [dict], narrations: pd.DataFrame, object_movements: dict, mask_fixtures: dict) -> dict:
    ## TODO: come up with a separate array of 0, 1 labels and corresponding msk and frame ids
    ## If an object being picked or dropped, find if it is being used and label accordingly
    object_labels_array = []
    event_history = return_event_history_sorted(object_movements)
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
        event_history_trimmed = event_history[
            (event_history.time >= start_timestamp)
            & (event_history.time <= end_timestamp)
        ]
        for object_used in objects_used:
            event_history_trimmed_object = event_history_trimmed[
                event_history_trimmed.object_name.eq(object_used)
            ]
            if len(event_history_trimmed_object) == 0:
                print(f"WARNING: No event history found for {object_used} in the action {narration_id}")
                continue
            mask_frame_ids = []
            for _, row in event_history_trimmed_object.iterrows():
                frame_number = mask_fixtures[row["mask_id"]]["frame_number"] if row["mask_id"] in mask_fixtures else None
                mask_bbox = mask_fixtures[row["mask_id"]]["bbox"] if row["mask_id"] in mask_fixtures else None
                mask_frame_ids.append({
                    "time": row["time"],
                    "action_type": row["action"],
                    "mask_id": row["mask_id"],
                    "frame_number": frame_number,
                    "mask_bbox": mask_bbox,
                })
            object_labels_array.append({
                "object_name": object_used,
                "usage_start_timestamp": start_timestamp,
                "usage_end_timestamp": end_timestamp,
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

    with open(f"outputs/linked_objects_llm_gpt-oss:20b/linked_objects_gpt-oss:20b_{args.video_id}.jsonl", "r") as f:
        action_object_mapping = [json.loads(line) for line in f]

    object_movements = object_movements_all[args.video_id]
    ## Sort object movements by start timestamp
    sorted_keys = sorted(object_movements.keys(), key=lambda elem: object_movements[elem]["tracks"][0]["time_segment"][0])
    object_movements = {k: object_movements[k] for k in sorted_keys}
    mask_fixtures = mask_fixtures_all[args.video_id]

    action_narrations = action_narrations_all[action_narrations_all.unique_narration_id.str.startswith(args.video_id)]
    action_narrations = action_narrations.sort_values(by="start_timestamp")

    os.makedirs("plots", exist_ok=True)

    try:    
        object_labels_array = combine_object_labels(action_object_mapping, action_narrations, object_movements, mask_fixtures)
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
