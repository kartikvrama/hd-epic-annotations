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
    action_descriptions = []
    for touch in touch_points:
        action = retrieve_action_descriptions(data_narrations, video_id, touch["pick"], touch["drop"])
        plot_x.append(touch["pick"])
        plot_o.append(touch["drop"])
        plot_points.extend([touch["pick"], touch["drop"]])
        action_descriptions.extend(action)
    ## Plot a flat line plot with the points
    if plot_points:
        ax.plot(plot_points, [object_id] * len(plot_points), "-", color="black")
        ax.plot(plot_x, [object_id] * len(plot_x), "x", color="red")
        ax.plot(plot_o, [object_id] * len(plot_o), "o", color="red")
    ## Plot last leg of the track as blue dashed line
    penultimate_touch = touch_points[-2] if len(touch_points) > 1 else touch_points[-1]
    ax.plot([penultimate_touch["drop"], touch_points[-1]["pick"], touch_points[-1]["drop"]], 3*[object_id], "--", color="blue")
    return action_descriptions


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

    random_videos = random.sample(list(data_assoc.keys()), 10)
    os.makedirs("plots", exist_ok=True)

    with open("narrations-and-action-segments/HD_EPIC_Narrations.pkl", "rb") as f:
        data_narrations = pickle.load(f)

    for video_id in random_videos:
        data_assoc_video = data_assoc[video_id]
        fig = plt.figure(figsize=(25, 20))
        ax = fig.add_subplot(111)
        ax_bottom = fig.add_subplot(212)
        for object_id, data_object in data_assoc_video.items():
            print(f"Object name: {data_object['name']}")
            print(f"Number of tracks: {len(data_object['tracks'])}")
            action_descriptions = plot_object_movement(data_object['tracks'], data_object['name'], data_narrations, video_id, ax)
            # import pdb; pdb.set_trace()
            for (start_timestamp, end_timestamp, action_name) in action_descriptions:
                print(start_timestamp, end_timestamp, action_name)
                if not action_name:
                    continue
                ax_bottom.plot([start_timestamp, end_timestamp], [0, 0], "-", color="black")
                ax_bottom.text((start_timestamp + end_timestamp) / 2, 0, action_name, rotation=90, ha="center", va="center")

        ## TODO: Add action descriptions to the plot at the bottom of the plot
        fig.savefig(f"plots/object_actions_{video_id}.png")

if __name__ == "__main__":
    main()
