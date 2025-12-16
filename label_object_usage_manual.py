import json
import os
import pickle
import random
import pandas as pd
import textwrap
from utils import extract_touches_from_track, retrieve_action_descriptions

## Structure of assoc_info.json
# {
#   "video_id": {
#     "association_id": {
#       "name": "string",
#       "tracks": [
#         {
#           "track_id": "string",
#           "time_segment": [start_time, end_time],
#           "masks": ["string", ...]
#         },
#         ...
#       ]
#     },
#     ...
#   }
# }

LABELS = ["idle", "inuse"]



def get_touch_action_details(track_sequence, data_narrations, video_id):
    """Extract touch points and their action details without plotting."""
    touch_points = extract_touches_from_track(track_sequence)
    touch_action_details = []  # Store detailed info for each touch point
    for touch in touch_points:
        action = retrieve_action_descriptions(data_narrations, video_id, touch["pick"], touch["drop"])
        touch_action_details.append({
            "pick": touch["pick"],
            "drop": touch["drop"],
            "actions": action
        })
    return touch_action_details


def get_actions_between_timestamps(data_narrations, video_id, start_timestamp, end_timestamp):
    """Get all actions that overlap with the time period between start and end timestamps."""
    data_narrations_person = data_narrations[
        data_narrations.unique_narration_id.str.startswith(video_id) 
        & data_narrations.start_timestamp.ge(start_timestamp) ## action starts after start_timestamp
        & data_narrations.start_timestamp.le(end_timestamp) ## action starts before end_timestamp
    ]
    actions = []
    for _, row in data_narrations_person.iterrows():
        label_raw = "|".join("-".join(wrd.replace(" ", "-") for wrd in pair) for pair in row["main_actions"])
        actions.append({
            "start": row["start_timestamp"],
            "end": row["end_timestamp"],
            "description": label_raw,
            "narration": row["narration"]
        })
    return sorted(actions, key=lambda x: x["start"])


def interactive_labeling(video_id, object_name, association_id, touches, data_narrations, existing_label=None):
    """Interactive tool to label the last action where the object was used before the final touch.
    
    Args:
        existing_label: Existing label data to resume from (if any)
    """
    if len(touches) < 2:
        print(f"  Skipping {object_name} (ID: {association_id}) - needs at least 2 touches, has {len(touches)}")
        return {"object_name": object_name, "association_id": association_id, "skip": True}
    
    # If all the touches are identical, return skip
    if all(touch["pick"] == touches[0]["pick"] and touch["drop"] == touches[0]["drop"] for touch in touches):
        print(f"  Skipping {object_name} (ID: {association_id}) - all touches are identical")
        return {"object_name": object_name, "association_id": association_id, "skip": True}
    
    # Check if we're resuming
    is_resume = existing_label is not None and not existing_label.get("skip", False)
    if is_resume:
        print(f"\n  Resuming labeling for {object_name} (ID: {association_id})...")
        print(f"  Existing labels:")
        if existing_label.get("pre_lastTrace_label"):
            print(f"    - pre_lastTrace: {existing_label.get('pre_lastTrace_label', None)}")
        if existing_label.get("lastTrace_label"):
            print(f"    - last_trace: {existing_label.get('lastTrace_label', None)}")
        if existing_label.get("after_lastTrace_label"):
            print(f"    - after_last_trace: {existing_label.get('after_lastTrace_label', None)}")
    
    # Get the last three touches
    second_last = touches[-2]
    last = touches[-1]
    
    # Get actions between second-to-last drop and last pick
    pre_LastTrace_start = second_last["drop"]
    pre_LastTrace_end = last["pick"]
    pre_LastTrace_actions = get_actions_between_timestamps(data_narrations, video_id, pre_LastTrace_start, pre_LastTrace_end)
    
    ## Get actions between last pick and last drop
    lastTrace_start = last["pick"]
    lastTrace_end = last["drop"]
    lastTrace_actions = get_actions_between_timestamps(data_narrations, video_id, lastTrace_start, lastTrace_end)

    # Display information
    print("\n" + "=" * 80)
    print(f"Video ID: {video_id}")
    print(f"Object: {object_name} (Association ID: {association_id})")
    print(f"Total touches: {len(touches)}")
    print("=" * 80)

    # Print the pick and drop times of the second-to-last and last trace
    def _format_time(ts):
        mins = int(ts // 60)
        secs = ts % 60
        return f"{mins:02d}:{secs:05.2f}"

    print(f"Second-to-last trace:")
    print(f"  Pick time: {_format_time(second_last['pick'])}")
    print(f"  Drop time: {_format_time(second_last['drop'])}")
    print(f"Last trace:")
    print(f"  Pick time: {_format_time(last['pick'])}")
    print(f"  Drop time: {_format_time(last['drop'])}")
    
    ## Offer the user a chance to skip labeling this object
    while True:
        skip = input("Skip labeling this object? Enter 'y' to skip, 'n' to continue: ").strip().lower()
        if skip == 'y':
            print("  Skipping labeling for this object.")
            return {"object_name": object_name, "association_id": association_id, "skip": True}
        elif skip == 'n':
            break
        else:
            print("Please enter 'y' or 'n'.")

    print(f"\nPeriod between second-to-last and last trace")

    print(f"  Time range: {pre_LastTrace_start} - {pre_LastTrace_end} "
          f"({ _format_time(pre_LastTrace_start) } - { _format_time(pre_LastTrace_end) })")
    print(f"  Number of actions: {len(pre_LastTrace_actions)}")
    if pre_LastTrace_actions:
        print("  Actions (sorted by start time):")
        for idx, action in enumerate(pre_LastTrace_actions, 1):
            print(f"    {idx}. [{action['start']} - {action['end']}]: {action['narration']}")
    else:
        print("  (No actions found)")

    # Label the time between second-to-last and last trace as idle or use
    print("\n" + "-" * 80)
    pre_lastTrace_label = None
    if is_resume and existing_label.get("pre_lastTrace_label"):
        pre_lastTrace_label = existing_label.get("pre_lastTrace_label")

    if pre_lastTrace_label is None:
        while True:
            choice = input(
                f"Enter any of the following labels: {LABELS}: "
            ).strip().lower()
            if choice in LABELS:
                pre_lastTrace_label = choice
                break
            else:
                print(f"Please enter any of the following labels: {LABELS}")

    ## Get actions between last pick and last drop
    lastTrace_start = last["pick"]
    lastTrace_end = last["drop"]
    lastTrace_actions = get_actions_between_timestamps(data_narrations, video_id, lastTrace_start, lastTrace_end)

    print(f"\nPeriod between last pick and last drop")
    print(f"  Time range: {lastTrace_start} - {lastTrace_end} "
          f"({ _format_time(lastTrace_start) } - { _format_time(lastTrace_end) })")
    print(f"  Number of actions: {len(lastTrace_actions)}")
    if lastTrace_actions:
        print("  Actions (sorted by start time):")
        for idx, action in enumerate(lastTrace_actions, 1):
            print(f"    {idx}. [{action['start']} - {action['end']}]: {action['narration']}")
    else:
        print("  (No actions found)")

    # Label the last trace as a return touch or use touch
    lastTrace_label = None
    if is_resume and existing_label.get("lastTrace_label"):
        lastTrace_label = existing_label.get("lastTrace_label")
    
    if lastTrace_label is None:
        while True:
            choice = input(
                f"Enter any of the following labels: {LABELS}: "
            ).strip().lower()
            if choice in LABELS:
                lastTrace_label = choice
                break
            else:
                print(f"Please enter any of the following labels: {LABELS}")

    # Ask user to label the period after the last trace
    print(f"\nPeriod after last drop (end of data for this object): {_format_time(lastTrace_end)} to END OF VIDEO")
    after_lastTrace_label = None
    if is_resume and existing_label.get("after_lastTrace_label"):
        after_lastTrace_label = existing_label.get("after_lastTrace_label")

    if after_lastTrace_label is None:
        while True:
            choice = input(
                f"Enter a label for the period after the last trace (any of the following labels: {LABELS}): "
            ).strip().lower()
            if choice in LABELS:
                after_lastTrace_label = choice
                break
            else:
                print(f"Please enter any of the following labels: {LABELS}")

    # Build return dictionary, preserving existing data when resuming
    result = {
        "object_name": object_name,
        "association_id": association_id,
        ## Time between second-to-last drop and last pick
        "pre_lastTrace_start": pre_LastTrace_start,
        "pre_lastTrace_end": pre_LastTrace_end,
        "pre_lastTrace_label": pre_lastTrace_label,
        ## Time between last pick and last drop
        "lastTrace_start": lastTrace_start,
        "lastTrace_end": lastTrace_end,
        "lastTrace_label": lastTrace_label,
        ## Time after last drop
        "after_lastTrace_start": last["drop"],
        "after_lastTrace_label": after_lastTrace_label,
    }
    
    # If resuming, preserve any other fields from existing_label
    if is_resume and existing_label:
        for key, value in existing_label.items():
            if key not in result or result[key] is None:
                result[key] = value
    
    return result

def main():
    ## Load association info (object movements)
    with open("scene-and-object-movements/assoc_info.json") as f:
        data_assoc = json.load(f)

    video_ids = [line.strip() for line in open("video_ids_viz.txt")]

    with open("narrations-and-action-segments/HD_EPIC_Narrations.pkl", "rb") as f:
        data_narrations = pickle.load(f)

    # Dictionary to store all labels
    all_labels = {}
    os.makedirs("plots", exist_ok=True)
    labels_file = "plots/object_usage_labels.json"
    
    # Load existing labels if file exists
    if os.path.exists(labels_file):
        with open(labels_file, "r") as f:
            all_labels = json.load(f)
        print(f"Loaded existing labels from {labels_file}")
    
    def save_labels():
        """Helper function to save labels to file."""
        with open(labels_file, "w") as f:
            json.dump(all_labels, f, indent=2)

    for video_id in video_ids:
        if video_id not in data_assoc:
            print(f"\nSkipping video {video_id} - not found in association data")
            continue
        
        print(f"\n\nProcessing video: {video_id}")
        data_assoc_video = data_assoc[video_id]
        
        # Collect all action descriptions for text file
        all_object_actions = []
        # Load existing labels for this video if any
        video_labels = all_labels.get(video_id, [])
        
        for object_id, data_object in data_assoc_video.items():
            if data_object['name'].startswith("Track"):
                continue
            print(f"Object name: {data_object['name']}")
            print(f"Number of tracks: {len(data_object['tracks'])}")
            touch_action_details = get_touch_action_details(
                data_object['tracks'], data_narrations, video_id
            )
            
            # Store object and touch details for text file
            all_object_actions.append({
                "object_name": data_object['name'],
                "object_id": object_id,
                "touches": touch_action_details
            })
            
            # Check if this object has already been labeled with all three labels
            existing_label = None
            for label in video_labels:
                if label.get("association_id") == object_id:
                    existing_label = label
                    break
            
            # Only skip if all three labels are present
            if existing_label and existing_label.get("skip", False):
                print(f"  Object {data_object['name']} (ID: {object_id}) already skipped, skipping...")
                continue

            if existing_label and not existing_label.get("skip", False):
                has_all_labels = (
                    existing_label.get("pre_lastTrace_label") is not None and
                    existing_label.get("lastTrace_label") is not None and
                    existing_label.get("after_lastTrace_label") is not None
                )
                if has_all_labels:
                    print(f"  Object {data_object['name']} (ID: {object_id}) already fully labeled, skipping...")
                    continue
            
            # Interactive labeling for objects with at least 2 touches
            label_data = interactive_labeling(
                video_id, 
                data_object['name'], 
                object_id, 
                touch_action_details, 
                data_narrations,
                existing_label  # Pass existing label for resume
            )
            if label_data:
                # Skip if user explicitly skipped
                if label_data.get("skip", False):
                    # Keep the skip marker but don't process further
                    if existing_label is None:
                        video_labels.append(label_data)
                        all_labels[video_id] = video_labels
                        save_labels()
                    continue
                
                # Update existing label or append new one
                if existing_label is not None:
                    # Update existing label in place
                    for idx, label in enumerate(video_labels):
                        if label.get("association_id") == object_id:
                            video_labels[idx] = label_data
                            break
                else:
                    # Append new label
                    video_labels.append(label_data)
                
                # Update labels for this video and save immediately
                all_labels[video_id] = video_labels
                save_labels()
                print(f"Labels saved to {labels_file}")
        
        # Write all action descriptions to text file
        output_file = f"plots/object_actions_{video_id}.txt"
        with open(output_file, "w") as f:
            f.write(f"Video ID: {video_id}\n")
            f.write("=" * 80 + "\n\n")
            
            for obj_data in all_object_actions:
                f.write(f"Object: {obj_data['object_name']} (ID: {obj_data['object_id']})\n")
                f.write("-" * 80 + "\n")
                
                total_touches = len(obj_data['touches'])
                for idx, touch in enumerate(obj_data['touches'], 1):
                    # Label touches based on position
                    if idx == total_touches:
                        touch_label = "User return touch (blue)"
                    elif idx == total_touches - 1:
                        touch_label = "Time between last use and return (red)"
                    else:
                        touch_label = f"Touch {idx}"
                    
                    f.write(f"\n  {touch_label}:\n")
                    f.write(f"    Pick time: {touch['pick']}\n")
                    f.write(f"    Drop time: {touch['drop']}\n")
                    f.write(f"    Action descriptions:\n")
                    
                    if touch['actions']:
                        for action in touch['actions']:
                            start_ts, end_ts, action_desc = action
                            f.write(f"      - [{start_ts} - {end_ts}]: {action_desc.replace('\n', '')}\n")
                    else:
                        f.write(f"      (No action descriptions found)\n")
                    f.write("\n")
                
                f.write("\n")
        
        print(f"Action descriptions saved to {output_file}")
    
    # Final save (redundancy check)
    save_labels()
    
    # Print summary
    total_objects_labeled = sum(len(labels) for labels in all_labels.values())
    print(f"\n\n{'=' * 80}")
    print(f"Labeling Summary:")
    print(f"  Total videos processed: {len([v for v in video_ids if v in data_assoc])}")
    print(f"  Total objects labeled: {total_objects_labeled}")
    print(f"  Videos with labels: {len(all_labels)}")
    print(f"All labels saved to {labels_file}")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()
