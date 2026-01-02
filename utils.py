import textwrap
import pandas as pd
import pdb

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
            try:
                pick_mask_id = "unknown"
                if len(track["masks"]) > 0:
                    pick_mask_id = track["masks"][0]
                else:
                    print(f"Track {track['track_id']} has no pick mask: {track['masks']}")
                pick_time = track["time_segment"][0]
                event_history.append(
                    {
                        "time": pick_time,
                        "object_name": assoc_data["name"],
                        "action": "PICK",
                        "mask_id": pick_mask_id,
                    }
                )
                drop_time = track["time_segment"][1]
                drop_mask_id = "unknown"
                if len(track["masks"]) > 1:
                    drop_mask_id = track["masks"][1]
                else:
                    print(f"Track {track['track_id']} has no drop mask: {track['masks']}")
                event_history.append(
                    {
                        "time": drop_time,
                        "object_name": assoc_data["name"],
                        "action": "DROP",
                        "mask_id": drop_mask_id
                    }
                )
            except Exception as e:
                print(f"Error processing track {track['track_id']}: {e}")
    event_history = pd.DataFrame(event_history).sort_values(by="time").reset_index(drop=True)
    return event_history


def generate_time_wise_scene_graphs(object_movements: dict, mask_fixtures: dict) -> list:
    """
    Generate time-wise scene graphs from object movements.
    
    Args:
        object_movements: Dictionary from assoc_info.json for a video_id
        mask_fixtures: Dictionary from mask_info.json for a video_id
    
    Returns:
        List of dictionaries, each containing:
            - "time": timestamp of the scene graph
            - "action": action type ("PICK" or "DROP")
            - "object_name": name of the object involved in the action
            - "scene_graph": dictionary mapping node names (fixtures/"Human"/"Free Space") to lists of object names
    """
    # Get sorted event history
    event_history = return_event_history_sorted(object_movements)
    
    # Initialize scene graph: use first pick action of each object to determine initial state
    scene_graph = {}  # Maps node name -> list of object names
    object_initial_locations = {}  # Track where each object starts
    
    # Find first pick for each object to determine initial location
    for _, assoc_data in object_movements.items():
        object_name = assoc_data["name"]
        # Skip objects whose name starts with "Track"
        if object_name.startswith("Track"):
            continue
        if len(assoc_data["tracks"]) > 0:
            first_track = assoc_data["tracks"][0]
            first_pick_mask_id = first_track["masks"][0]
            
            # Get fixture from mask_info
            if first_pick_mask_id in mask_fixtures:
                fixture = mask_fixtures[first_pick_mask_id]["fixture"]
                # Handle Null fixture
                if fixture is None or fixture == "Null":
                    node_name = "Free Space"
                else:
                    node_name = fixture
            else:
                node_name = "Free Space"
            
            # Initialize object at this location
            if node_name not in scene_graph:
                scene_graph[node_name] = []
            scene_graph[node_name].append(object_name)
            object_initial_locations[object_name] = node_name
    
    # Track current location of each object
    object_current_location = object_initial_locations.copy()
    
    # List to store scene graphs at each time point
    time_wise_scene_graphs = []
    
    # Store initial state (before any events)
    if len(event_history) > 0:
        initial_time = max(0.0, event_history.iloc[0]["time"] - 0.01)  # Slightly before first event
        initial_scene_graph = {node: objects.copy() for node, objects in scene_graph.items()}
        time_wise_scene_graphs.append({
            "time": initial_time,
            "action": "INITIAL",
            "object_name": None,
            "mask_id": None,
            "scene_graph": initial_scene_graph
        })
    
    # Process events chronologically
    for _, row in event_history.iterrows():
        time = row["time"]
        object_name = row["object_name"]
        # Skip objects whose name starts with "Track"
        if object_name.startswith("Track"):
            continue
        action = row["action"]
        mask_id = row["mask_id"]
        
        if action == "PICK":
            # Remove object from current node and add to "Human"
            current_node = object_current_location.get(object_name)
            if current_node and current_node in scene_graph:
                if object_name in scene_graph[current_node]:
                    scene_graph[current_node].remove(object_name)
                # # Remove empty nodes (optional, for cleaner output)
                # if len(scene_graph[current_node]) == 0 and current_node != "Human" and current_node != "Free Space":
                #     del scene_graph[current_node]
            
            # Add to Human node
            if "Human" not in scene_graph:
                scene_graph["Human"] = []
            if object_name not in scene_graph["Human"]:
                scene_graph["Human"].append(object_name)
            object_current_location[object_name] = "Human"
            
        elif action == "DROP":
            # Remove object from "Human" and add to drop location
            if "Human" in scene_graph:
                if object_name in scene_graph["Human"]:
                    scene_graph["Human"].remove(object_name)
            
            # Determine drop location
            if mask_id == "unknown" or mask_id not in mask_fixtures:
                drop_node = "Free Space"
            else:
                fixture = mask_fixtures[mask_id]["fixture"]
                if fixture is None or fixture == "Null":
                    drop_node = "Free Space"
                else:
                    drop_node = fixture
            
            # Add to drop node
            if drop_node not in scene_graph:
                scene_graph[drop_node] = []
            if object_name not in scene_graph[drop_node]:
                scene_graph[drop_node].append(object_name)
            object_current_location[object_name] = drop_node
        
        # Store scene graph snapshot at this time
        # Create a deep copy to avoid reference issues
        scene_graph_snapshot = {node: objects.copy() for node, objects in scene_graph.items()}
        time_wise_scene_graphs.append({
            "time": time,
            "action": action,
            "object_name": object_name,
            "mask_id": mask_id,
            "scene_graph": scene_graph_snapshot
        })
    
    return time_wise_scene_graphs
