import json
import os
import pickle
import random
import pandas as pd
import textwrap
from utils import extract_touches_from_track, retrieve_action_descriptions
import pdb


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

'''
Noun: "oven's glove", objects: "oven glove"
Noun: 'top of other pies', objects: "pie" and "pie2"
Noun: 'one pie', objects: "pie" and "pie2"
Noun: 'two pies', objects: "pie" and "pie2"
Noun: 'another pie', objects: "pie" and "pie2"
Noun: 'spoon', objects: "plastic spoon"
Noun: 'another pie', objects: "pie" and "pie2"
Noun: 'spoon', objects: "plastic spoon"

'''
LABELS = ["idle", "inuse"]

# Common words to ignore when matching nouns to objects
STOPWORDS = {
    "a", "an", "the", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "some", "another", "other", "top", "of", "bottom", "side", "piece", "pieces", "bit", "bits",
    "first", "second", "third", "last", "next", "more", "few", "all", "both", "each", "every",
    "my", "your", "his", "her", "its", "their", "our", "top", "bottom", "left", "right", "center",
    "empty", "full"
}


def normalize_word(word):
    """Normalize a word by removing possessives and converting to singular."""
    word = word.lower().strip()
    # Remove possessive 's
    if word.endswith("'s"):
        word = word[:-2]
    elif word.endswith("s'"):
        word = word[:-2]
    # Simple plural handling (not perfect but covers common cases)
    if word.endswith("ies"):
        word = word[:-3] + "y"  # pies -> pie (actually py, need to handle)
    elif word.endswith("es") and len(word) > 3:
        # boxes -> box, but not "es" alone
        word = word[:-2]
    elif word.endswith("s") and len(word) > 2 and not word.endswith("ss"):
        word = word[:-1]
    return word


def extract_keywords(phrase):
    """Extract meaningful keywords from a phrase, removing stopwords."""
    words = phrase.lower().replace("'s", " ").replace("-", " ").split()
    keywords = []
    for word in words:
        normalized = normalize_word(word)
        if normalized and normalized not in STOPWORDS and len(normalized) > 1:
            keywords.append(normalized)
    return keywords


def match_noun_to_objects(noun, object_names):
    """
    Match a noun from narration to object names.
    
    Args:
        noun: A noun string from narration (e.g., "oven's glove", "two pies")
        object_names: List of object name strings (e.g., ["oven glove", "pie", "pie2", "plastic spoon"])
    
    Returns:
        List of matched object names
    """
    matched_objects = []
    noun_keywords = extract_keywords(noun)
    
    if not noun_keywords:
        return matched_objects
    

    ## Method 0: Check for an exact match first
    if noun.lower() in [obj_name.lower() for obj_name in object_names]:
        matched_objects.append(noun)
        return matched_objects
    
    for obj_name in object_names: ## For all other methods, we will extract keywords from the object name
        obj_keywords = extract_keywords(obj_name)
        
        # Check for any keyword match
        noun_set = set(noun_keywords)
        obj_set = set(obj_keywords)
        
        # # Method 1: Direct keyword overlap
        # if noun_set & obj_set:
        #     matched_objects.append(obj_name)
        #     continue
        
        # # Method 2: Check if any noun keyword is a substring of any object keyword or vice versa
        # for noun_kw in noun_keywords:
        #     for obj_kw in obj_keywords:
        #         # "spoon" matches "spoon" in "plastic spoon"
        #         if noun_kw in obj_kw or obj_kw in noun_kw:
        #             matched_objects.append(obj_name)
        #             break
        #     else:
        #         continue
        #     break
        
        # Method 3: Check if object name (with numbers stripped) matches noun
        # e.g., "pie2" -> "pie" matches "pie"
        obj_name_no_numbers = ''.join(c for c in obj_name if not c.isdigit()).strip()
        obj_no_num_keywords = extract_keywords(obj_name_no_numbers)
        if set(noun_keywords) & set(obj_no_num_keywords):
            if obj_name not in matched_objects:
                matched_objects.append(obj_name)
    
    return matched_objects


def match_nouns_to_objects(nouns, object_names):
    """
    Match multiple nouns to object names.
    
    Args:
        nouns: List of noun strings from narration
        object_names: List of object name strings
    
    Returns:
        List of unique matched object names
    """
    matched = set()
    for noun in nouns:
        matches = match_noun_to_objects(noun, object_names)
        matched.update(matches)
    return list(matched)


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
        actions.append(row)
    return sorted(actions, key=lambda x: x["start"])


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

    action_object_mapping = {}
    for video_id in video_ids:
        action_object_mapping[video_id] = []
        if video_id not in data_assoc:
            print(f"\nSkipping video {video_id} - not found in association data")
            continue
        
        print(f"\n\nProcessing video: {video_id}")
        data_assoc_video = data_assoc[video_id]

        object_assoc_ids = list(data_assoc_video.keys())
        object_names = [data_assoc_video[k]["name"] for k in object_assoc_ids]
        
        # --- Ask user to choose which objects to label ---
        print("\nObjects detected in this video scene:")
        for idx, name in enumerate(object_names):
            print(f"[{idx}] {name}")

        print("\nWhich objects do you want to label usage for?")
        print("Enter comma-separated numbers (e.g. 0,2,4) or 'all' for all objects.")
        selected = input("Selection: ").strip()
        
        if selected.lower() == "all":
            chosen_indices = list(range(len(object_names)))
        else:
            try:
                chosen_indices = [int(x) for x in selected.split(",") if x.strip().isdigit()]
            except Exception:
                print("Invalid input, defaulting to all objects.")
                chosen_indices = list(range(len(object_names)))

        # Filter object ids/names for those selected
        object_names_selected = [object_names[i] for i in chosen_indices]
        data_narrations_video = data_narrations[data_narrations.unique_narration_id.str.startswith(video_id)]
        data_narrations_video = data_narrations_video.sort_values(by="start_timestamp")  # sort by start timestamp

        # Collect all nouns that appeared in any narration for this video
        # and track which objects were matched
        objects_ever_matched = set()

        def _seconds_to_minsecs(seconds):
            minutes = int(seconds // 60)
            seconds = int(seconds % 60)
            return f"{minutes}:{seconds:02d}"
        
        for iterrow, row in data_narrations_video.iterrows():
            nouns = row["nouns"]
            
            # Use the new matching function
            objects_used = match_nouns_to_objects(nouns, object_names_selected)
            objects_ever_matched.update(objects_used)

            # ## DEBUG: Print the nouns, main action classes, narrations, and objects involved
            # print(f"Nouns: {nouns}")
            # ## Start and end timestamps
            # print(f"Time between action: {_seconds_to_minsecs(row['start_timestamp'])} - {_seconds_to_minsecs(row['end_timestamp'])}")
            # print(f"Main actions: {row['main_actions']}")
            # print(f"Narration: {row['narration']}")
            # ## list of all objects in the scene
            # print(f"All objects in the scene: {sorted(object_names)}")
            # print(f"Objects involved: {objects_used}\n--------------------------------\n")
            # pdb.set_trace()

            action_object_mapping[video_id].append({
                "unique_narration_id": row["unique_narration_id"],
                "start": row["start_timestamp"],
                "end": row["end_timestamp"],
                "objects_used": objects_used,
                "nouns": nouns,
            })
                
        # List all objects that were never matched to any noun in this video's narrations
        never_mentioned_objects = [
            obj_name for obj_name in object_names_selected
            if obj_name not in objects_ever_matched
        ]

        print("\nObjects in association data that were NEVER mentioned in any narration for this video:")
        if never_mentioned_objects:
            for obj_name in never_mentioned_objects:
                print(f" - {obj_name}")
        else:
            print("All objects were mentioned at least once in the narrations.")

    # Save the action-object mapping for this video to a file

    output_mapping_dir = "plots/action_object_mapping"
    os.makedirs(output_mapping_dir, exist_ok=True)
    output_file = os.path.join(output_mapping_dir, "all_action_object_mapping.json")
    with open(output_file, "w") as f:
        json.dump(action_object_mapping, f, indent=2)
    print(f"\nSaved action-object mapping for {video_id} to {output_file}\n")



if __name__ == "__main__":
    main()
