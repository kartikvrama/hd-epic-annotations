import os
import glob
import json
import pickle
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import pandas as pd
import argparse
from utils import extract_touches_from_track, seconds_to_minutes_seconds, return_event_history_sorted
import pdb

parser = argparse.ArgumentParser()
parser.add_argument("--video_id", required=True, help="Video ID to process")
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
        y_position = all_object_labels.index(object_label["object_name"])
        if "llm_response_json" in object_label:
            llm_response = object_label.get("llm_response_json", {})
            if llm_response.get("is_used", False):
                usage_label = "used"
            else:
                usage_label = "not used"
        elif "annotation" in object_label:
            usage_label = object_label["annotation"].lower()
        else:
            print(f"Unknown usage label for object {object_label['object_name']} between {object_label['time_start']} and {object_label['time_end']}")

        if usage_label == "used":
            verbose_print(f"Object {object_label['object_name']} used between {object_label['time_start']} and {object_label['time_end']}")
            axis.fill_betweenx(
                [y_position - BAR_WIDTH/2, y_position + BAR_WIDTH/2],
                object_label["time_start"],
                object_label["time_end"],
                color="red",
                alpha=0.3,
            )


def main():
    with open("scene-and-object-movements/assoc_info.json", encoding='utf-8') as f:
        object_movements_all = json.load(f)

    with open("scene-and-object-movements/mask_info.json", "r", encoding='utf-8') as f:
        mask_fixtures_all = json.load(f)

    with open("narrations-and-action-segments/HD_EPIC_Narrations.pkl", "rb") as f:
        action_narrations_all = pickle.load(f)

    object_movements = object_movements_all[args.video_id]
    ## Sort object movements by start timestamp
    sorted_keys = sorted(object_movements.keys(), key=lambda elem: object_movements[elem]["tracks"][0]["time_segment"][0])
    object_movements = {k: object_movements[k] for k in sorted_keys}
    mask_fixtures = mask_fixtures_all[args.video_id]

    action_narrations = action_narrations_all[action_narrations_all.unique_narration_id.str.startswith(args.video_id)]
    action_narrations = action_narrations.sort_values(by="start_timestamp")

    os.makedirs("plots", exist_ok=True)


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

    # Read object usage labels from jsonl file

    # ## Manual annotations
    # usage_dir = "manual_usage_annotations"
    # annotation_files = glob.glob(os.path.join(usage_dir, "usage_labels_manual-FILE*.json"))
    # if annotation_files:
    #     label_filepath = max(annotation_files, key=os.path.getmtime)
    #     with open(label_filepath, "r") as f:
    #         object_usage_annotations = json.load(f)
    #     if args.video_id in object_usage_annotations:
    #         plot_object_usage_segments(object_usage_annotations[args.video_id]["labels"], ax, all_object_labels)

    ## LLM annotations
    usage_dir = "outputs/object_usage_labels_model-qwen3-vl:30b_max-segment-length-30_long_temp-80_numPredict-2000_tries-3"
    filename = f"object_usage_labels_{args.video_id}.jsonl"
    filepath = os.path.join(usage_dir, filename)
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            object_usage_annotations = [json.loads(line) for line in f]
        plot_object_usage_segments(object_usage_annotations, ax, all_object_labels)

    else:
        print(f"No object usage labels found for video_id: {args.video_id}")

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
    fig.savefig(f"plots/object_labels_combined_{args.video_id}.png")


if __name__ == "__main__":
    main()
