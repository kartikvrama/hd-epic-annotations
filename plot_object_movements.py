import json
import os
import pickle
import random
import pandas as pd
import matplotlib.pyplot as plt
import textwrap

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


def extract_touches_from_track(track_list):
    touches = []
    for track in track_list:
        ## convert string to tuple
        time_seg_tuple = track["time_segment"]
        assert isinstance(time_seg_tuple, list), f"Time segment for track {track['track_id']} is not a list\n{track}"
        if not len(time_seg_tuple) == 2:
            raise ValueError(f"Time segment for track {track['track_id']} is not of length 2\n{track}")
        touches.append({
            "pick": time_seg_tuple[0],
            "drop": time_seg_tuple[1],
        })
    return touches


def plot_object_movement(track_sequence, object_id, data_narrations, video_id, ax):
    ## first track
    touch_points = extract_touches_from_track(track_sequence)
    plot_x = []
    plot_o = []
    plot_points = []
    touch_action_details = []  # Store detailed info for each touch point
    for touch in touch_points:
        action = retrieve_action_descriptions(data_narrations, video_id, touch["pick"], touch["drop"])
        plot_x.append(touch["pick"])
        plot_o.append(touch["drop"])
        plot_points.extend([touch["pick"], touch["drop"]])
        ## Store detailed information for text file
        touch_action_details.append({
            "pick": touch["pick"],
            "drop": touch["drop"],
            "actions": action
        })
    ## Plot a flat line plot with the points
    if plot_points:
        ax.plot(plot_points, [object_id] * len(plot_points), "-", color="black")
        ax.plot(plot_x, [object_id] * len(plot_x), "x", color="red")
        ax.plot(plot_o, [object_id] * len(plot_o), "o", color="red")
    ## Plot last leg of the track as blue dashed line
    if len(touch_points) > 1:
        ax.plot([touch_points[-2]["drop"], touch_points[-1]["pick"]], 2*[object_id], "-", color="blue", linewidth=2)
    ax.plot([touch_points[-1]["pick"], touch_points[-1]["drop"]], 2*[object_id], "-", color="red", linewidth=2)
    return touch_action_details


def retrieve_action_descriptions(data_narrations, video_id, start_timestamp, end_timestamp):
    data_narrations_person = data_narrations[
        data_narrations.unique_narration_id.str.startswith(video_id) 
        & data_narrations.start_timestamp.ge(start_timestamp)
        & data_narrations.end_timestamp.le(end_timestamp)   
    ]
    action_descriptions = []
    for _, row in data_narrations_person.iterrows():
        label_raw = "|".join("-".join(wrd.replace(" ", "-") for wrd in pair) for pair in row["pairs"])
        description_str = "\n".join(textwrap.wrap(label_raw, width=18))
        action_descriptions.append(
            (
                row["start_timestamp"], 
                row["end_timestamp"], 
                description_str,
            )
        )
        # import pdb; pdb.set_trace()
    return action_descriptions

def main():
    ## Load association info (object movements)
    with open("scene-and-object-movements/assoc_info.json") as f:
        data_assoc = json.load(f)

    random_videos = random.sample(list(data_assoc.keys()), 15)
    os.makedirs("plots", exist_ok=True)

    with open("narrations-and-action-segments/HD_EPIC_Narrations.pkl", "rb") as f:
        data_narrations = pickle.load(f)

    for video_id in random_videos:
        data_assoc_video = data_assoc[video_id]
        fig = plt.figure(figsize=(25, 20))
        ax = fig.add_subplot(111)
        
        # Collect all action descriptions for text file
        all_object_actions = []
        
        for object_id, data_object in data_assoc_video.items():
            print(f"Object name: {data_object['name']}")
            print(f"Number of tracks: {len(data_object['tracks'])}")
            touch_action_details = plot_object_movement(
                data_object['tracks'], data_object['name'], data_narrations, video_id, ax
            )
            
            # Store object and touch details for text file
            all_object_actions.append({
                "object_name": data_object['name'],
                "object_id": object_id,
                "touches": touch_action_details
            })
            
        fig.savefig(f"plots/object_actions_{video_id}.png")
        
        # Write all action descriptions to text file
        output_file = f"plots/object_actions_{video_id}.txt"
        with open(output_file, "w") as f:
            f.write(f"Video ID: {video_id}\n")
            f.write("=" * 80 + "\n\n")
            
            for obj_data in all_object_actions:
                f.write(f"Object: {obj_data['object_name']} (ID: {obj_data['object_id']})\n")
                f.write("-" * 80 + "\n")
                
                for idx, touch in enumerate(obj_data['touches'], 1):
                    f.write(f"\n  Touch {idx}:\n")
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


if __name__ == "__main__":
    main()
