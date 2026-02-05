import os
import glob
import json
import csv
from utils import seconds_to_minutes_seconds
import pdb
from math import floor, ceil

manual_usage_dir = "manual_usage_annotations"
annotation_files = glob.glob(os.path.join(manual_usage_dir, "annotation_segments_*.json"))
if not annotation_files:
    raise FileNotFoundError("No annotation_segments_*.json files found in manual_usage_annotations/")
annotation_filepath = max(annotation_files, key=os.path.getmtime)
timestamp_annotation = os.path.basename(annotation_filepath).split("_segments_")[1].split(".")[0]

with open(annotation_filepath, "r") as f:
    annotation_segments = json.load(f)

label_filepath = f"manual_usage_annotations/usage_labels_manual-FILE{timestamp_annotation}.json"
object_usage_annotations = {}
if os.path.exists(label_filepath):
    print(f"Loading existing object usage annotations from {label_filepath}")
    with open(label_filepath, "r") as f:
        object_usage_annotations = json.load(f)

video_ids = list(annotation_segments.keys())

for video_id in video_ids:
    if not video_id in object_usage_annotations:
        object_usage_annotations[video_id] = {
            "objects_ignore": [],
            "labels": []
        }
    # Now sorting by time start first, then time end (numerically)
    time_segments = sorted(annotation_segments[video_id], key=lambda x: (x[0], x[1]))

    participant_id = video_id.split("-")[0]
    with open(f"high-level/activities/{participant_id}_recipe_timestamps.csv", "r") as f:
        reader = csv.DictReader(f)
        recipe_timestamps = list(row for row in reader if row["video_id"] == video_id)

    for segment in time_segments:
        ## Skip if object annotation already exists
        ## TODO: Resume does not work after allowing custom end time.
        if any(annotation["object_name"] == segment[3] and annotation["time_start"] == floor(segment[0]) and annotation["time_end"] == ceil(segment[1]) for annotation in object_usage_annotations[video_id]["labels"]):
            print(f"Object {segment[3]} already annotated between {seconds_to_minutes_seconds(segment[0])} and {seconds_to_minutes_seconds(segment[1])}, skipping...")
            continue
        if segment[3].startswith("Track"):
            continue
        if segment[3] in object_usage_annotations[video_id]["objects_ignore"]:
            continue

        ## TODO: Can we skip first passive segment?
        if segment[0] == 0:
            continue

        segment_start = floor(segment[0])
        segment_end = ceil(segment[1])

        ## Get high level activity at this timestamp
        activity_label = []
        for activity in recipe_timestamps:
            if activity["end_time"] == "end":
                if float(activity["start_time"]) > segment_end:
                    continue
                else:
                    activity_label.append(activity["high_level_activity_label"])
            else:
                if float(activity["start_time"]) > segment_end or float(activity["end_time"]) < segment_start:
                    continue
                else:
                    activity_label.append(activity["high_level_activity_label"])

        print(f"\nVideo {video_id}: {seconds_to_minutes_seconds(segment_start)} - {seconds_to_minutes_seconds(segment_end)}")
        print(f"Segment category: {segment[2]}")
        if activity_label:
            print("High level activities:")
            for activity in activity_label:
                print(f"  - {activity}")
        else:
            print("No high level activity labels")

        print("Object to annotate: ", segment[3])
        annotation = input("Enter annotation: Used (u), Not used (n), Ignore object (i), Skip (any other key): ").lower()
        if annotation == "u" or annotation == "n":
            end_time_custom = input("Enter end time as MM:SS. To skip, enter any key: ")
            if len(end_time_custom.split(":")) == 2 and all(part.isdigit() for part in end_time_custom.split(":")):
                end_time_custom = int(end_time_custom.split(":")[0]) * 60 + int(end_time_custom.split(":")[1])
                print(f"Creating additional segment from {end_time_custom} to {segment_end}")
                ## Create a new segment from end_time_custom to segment_end
                new_segment = (
                    end_time_custom,
                    segment_end,
                    segment[2],
                    segment[3],
                )
                time_segments.append(new_segment)
                ## TODO: Update annotation segments file as well
        if annotation == "i":
            object_usage_annotations[video_id]["objects_ignore"].append(segment[3])
            continue
        elif annotation == "u":
            object_usage_annotations[video_id]["labels"].append({
                "object_name": segment[3],
                "time_start": segment_start,
                "time_end": end_time_custom,
                "annotation": "used",
            })
        elif annotation == "n":
            object_usage_annotations[video_id]["labels"].append({
                "object_name": segment[3],
                "time_start": segment_start,
                "time_end": end_time_custom,
                "annotation": "not used",
            })
        else:
            print("Skipping segment...")
            continue

        with open(label_filepath, "w") as f:
            json.dump(object_usage_annotations, f, indent=1)
        print("Annotations saved to file")