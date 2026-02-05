"""Divide each object timeline into active and passive segments for object usage labeling."""

import csv
import json
from datetime import datetime
from utils import extract_touches_from_track
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--annotation_video_csv", required=True, help="Path to the annotation CSV file")
args = parser.parse_args()

def main():

    annotation_segments = {}

    with open(f"scene-and-object-movements/assoc_info.json", "r") as f:
        object_movements = json.load(f)

    with open(args.annotation_video_csv, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            video_id = row["video_id"]
            duration = float(row["duration"])
            annotation_segments[video_id] = []

            for object_name, object_data in object_movements[video_id].items():
                touches = extract_touches_from_track(object_data["tracks"])
                for i, touch in enumerate(touches):
                    if i == 0:
                        prev_time = 0
                    else:
                        prev_time = touches[i-1]["drop"]
                    ## Time till current pick is passive
                    segment = (
                        prev_time,
                        touch["pick"],
                        "passive",
                        object_data["name"]
                    )
                    annotation_segments[video_id].append(segment)
                    ## Time from current pick to current drop is active
                    segment = (
                        touch["pick"],
                        touch["drop"],
                        "active",
                        object_data["name"]
                    )
                    annotation_segments[video_id].append(segment)
                annotation_segments[video_id].append(
                    (
                        touches[-1]["drop"],
                        duration,
                        "passive",
                        object_data["name"]
                    )
                )
    
    date_time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"manual_usage_annotations/annotation_segments_{date_time_str}.json", "w") as f:
        json.dump(annotation_segments, f, indent=1)

if __name__ == "__main__":
    main()