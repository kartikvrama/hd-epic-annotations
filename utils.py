import textwrap
import pandas as pd

def seconds_to_minutes_seconds(seconds):
    minutes = int(seconds) // 60
    seconds_rem = int(seconds) % 60
    return f"{minutes:02d}:{seconds_rem:02d}"


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


def return_event_history_sorted(object_movements: dict) -> pd.DataFrame:
    """
    Return a sorted event history dataframe from the object movements.
    """

    event_history = []
    for _, assoc_data in object_movements.items():
        for track in assoc_data["tracks"]:
            pick_time = track["time_segment"][0]
            event_history.append(
                {
                    "time": pick_time,
                    "object_name": assoc_data["name"],
                    "action": "PICK",
                    "mask_id": track["masks"][0],
                }
            )
            drop_time = track["time_segment"][1]
            drop_mask_id = "unknown"
            if len(track["masks"]) > 1:
                drop_mask_id = track["masks"][1]
            event_history.append(
                {
                    "time": drop_time,
                    "object_name": assoc_data["name"],
                    "action": "DROP",
                    "mask_id": drop_mask_id
                }
            )
    event_history = pd.DataFrame(event_history).sort_values(by="time").reset_index(drop=True)
    return event_history
