import json
import argparse
from utils import seconds_to_minutes_seconds


def format_scene_graph(scene_graph: dict) -> str:
    """Format a scene graph dictionary into a human-readable string."""
    lines = []
    # Sort nodes for consistent output
    sorted_nodes = sorted(scene_graph.keys())
    for node in sorted_nodes:
        objects = scene_graph[node]
        if objects:  # Only show nodes with objects
            objects_str = ", ".join(sorted(objects))
            lines.append(f"  {node}: [{objects_str}]")
    return "\n".join(lines)


def _visualize_scene_graph(scene_graph, video_id, mask_info_dict):
    print(f"Time: {scene_graph['time_str']}")
    print(f"High-level activity: {scene_graph['high_level_activity']['high_level_activity_label']}")
    print("Action narrations:")
    for narration in scene_graph['narrations']:
        print(f"  * {narration['narration']}")
    verb = scene_graph['action'].lower()
    fixture_name = mask_info_dict[video_id].get(scene_graph['mask_id'], {}).get('fixture', 'unknown')
    if verb == "drop":
        print(f"Atomic action: {verb} `{scene_graph['object_name']}` to `{fixture_name}`\n")
    elif verb == "pick":
        print(f"Atomic action: {verb} `{scene_graph['object_name']}` from `{fixture_name}`\n")
    elif verb == "initial":
        pass
    else:
        raise ValueError(f"Invalid verb: {verb}")
    print(f"Scene graph:\n{format_scene_graph(scene_graph['scene_graph'])}\n")


def _extract_event_history(scene_graphs, mask_info_dict, query_object_name):
    result = {
        "object_name": query_object_name,
        "event_history": [],
    }

    for scene_graph in scene_graphs:
        if scene_graph["action"] == "INITIAL":
            continue
        fixture_name = mask_info_dict[scene_graph['mask_id']]['fixture'] if scene_graph['mask_id'] in mask_info_dict else "unknown"
        event = {
            "time": scene_graph['time'],
            "time_str": seconds_to_minutes_seconds(scene_graph['time']),
            "high_level_activity": scene_graph['high_level_activity']['high_level_activity_label'],
            "action_narrations": [narration['narration'] for narration in scene_graph['narrations']],
            "action": scene_graph['action'],
            "object": scene_graph['object_name'],
            "fixture": fixture_name.split("_")[1] if "_" in fixture_name else fixture_name,
        }
        ## Get state before the action
        event['objects_in_hand'] = set(scene_graph['scene_graph'].get("Human"))
        if scene_graph['action'] == "PICK":
            event['objects_in_hand'] = event['objects_in_hand'].difference(set([scene_graph['object_name']]))
            event['nearby_objects_fixture'] = set(scene_graph['scene_graph'].get(fixture_name)).difference(set([scene_graph['object_name']])) if fixture_name in scene_graph["scene_graph"] else set()
        elif scene_graph['action'] == "DROP":
            event['objects_in_hand'] = event['objects_in_hand'].union(set([scene_graph['object_name']]))
            event['nearby_objects_fixture'] = set(scene_graph['scene_graph'].get(fixture_name)).union(set([scene_graph['object_name']])) if fixture_name in scene_graph["scene_graph"] else set()
        else:
            raise ValueError(f"Invalid action: {scene_graph['action']}")
        event['nearby_objects_fixture'] = list(event['nearby_objects_fixture'])
        event['objects_in_hand'] = list(event['objects_in_hand'])
        result['event_history'].append(event)
    return result


def main():
    parser = argparse.ArgumentParser(description='Label usage active interventions')
    parser.add_argument('--video_id', type=str, required=True,
                        help='Video ID to process (e.g., P01-20240202-171220)')
    args = parser.parse_args()
    
    video_id = args.video_id

    with open("scene-and-object-movements/assoc_info.json", encoding='utf-8') as f:
        object_movement_dict = json.load(f)

    with open("scene-and-object-movements/mask_info.json", encoding='utf-8') as f:
        mask_info_dict = json.load(f)

    with open(f"outputs/scene_graphs/scene_graphs_{video_id}.jsonl", "r") as f:
        scene_graphs = [json.loads(line) for line in f]

    prompt_info = []
    for assoc_id, assoc_data in object_movement_dict[video_id].items():

        object_name = assoc_data['name']
        timesteps = [0] + [scene_graph['time'] for scene_graph in scene_graphs if scene_graph["object_name"] == object_name] + [scene_graphs[-1]["time"]]

        ## Print event history for consecutive timesteps
        for i in range(len(timesteps) - 1):
            timestep_1 = timesteps[i]
            timestep_2 = timesteps[i + 1]
            scene_graphs_between_timesteps = [scene_graph for scene_graph in scene_graphs if scene_graph['time'] >= timestep_1 and scene_graph['time'] <= timestep_2]
            result = _extract_event_history(scene_graphs_between_timesteps, mask_info_dict[video_id], object_name)
            result["time_start"] = timestep_1
            result["time_end"] = timestep_2
            prompt_info.append(result)

    with open(f"outputs/prompt_info_{video_id}.json", "w") as f:
        json.dump(prompt_info, f, indent=1)


if __name__ == "__main__":
    main()