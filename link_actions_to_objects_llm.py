#! /usr/bin/env python3

## Start ollama server: ./ollama/bin/ollama serve&
## Check ollama: ./ollama/bin/ollama ps

import argparse
import json
import pickle
import ollama


parser = argparse.ArgumentParser(description='Process a video by its ID.')
parser.add_argument('--video_id', required=True, type=str, help='ID of the video')
args = parser.parse_args()

VERBOSE = True

# Check if "qwen3:8b" is already loaded in Ollama; if not, load it.
def ensure_ollama_model_loaded(model_name="qwen3:8b"):
    try:
        models = ollama.list().get("models", [])
        loaded_model_names = set()
        for m in models:
            # Some entries may not have a "name" key, so use get with fallback
            name = m.get("name") or m.get("model") or ""
            if not name:
                continue
            loaded_model_names.add(name.split(":")[0])
        verbose_print(f"Loaded model names: {loaded_model_names}")
        if model_name.split(":")[0] not in loaded_model_names:
            print(f"Pulling model {model_name} since it is not loaded...")
            ollama.pull(model_name)
        else:
            verbose_print(f"Model {model_name} is already loaded.")
    except Exception as e:
        print(f"Error while checking/loading model '{model_name}': {e}")


def verbose_print(*args, **kwargs):
    if VERBOSE:
        print(*args, **kwargs)


def link_objects_to_action(narration, nouns, available_objects, system_prompt, examples):
    """
    Use Ollama with Qwen3 8B to link objects to actions based on narration and nouns.
    
    Args:
        narration: Text description of the action
        nouns: List of nouns mentioned in the narration
        available_objects: List of available object names to choose from
        system_prompt: Optional system-level prompt (uses default if None)
        examples: Optional list of 2-3 examples in format [{"narration": "...", "nouns": [...], "objects": [...]}, ...]
    
    Returns:
        List of object names that are linked to the action
    """
    response_format = {
        "objects_used": ["<list of object names as strings>"],
        "explanation": "<concise explanation>"
    }
    system_prompt += f"\n\nRespond ONLY in the following JSON format: {json.dumps(response_format, ensure_ascii=False)}"

    # Build the prompt with examples
    prompt = f"""Examples:
"""
    
    for i, example in enumerate(examples, 1):
        prompt += f"""
Example {i}:
Narration: {example['narration']}
Nouns: {json.dumps(example['nouns'])}
Available objects: {json.dumps(example['objects_available'])}
Response:
{{
  "objects_used": {json.dumps(example['objects_used'])},
  "explanation": "{example['explanation']}"
}}
"""
    
    # Add the current task
    prompt += f"""
Task:
Narration: {narration}
Nouns: {json.dumps(nouns)}
Available objects: {json.dumps(available_objects)}
Response: """
    
    ## Create debug print statement
    verbose_print(f"System prompt:\n<{system_prompt}>")
    verbose_print(f"Prompt:\n<{prompt}>")
    
    # Call Ollama
    try:
        # Construct the expected JSON response format for Ollama
        response = ollama.chat(
            model='qwen3:8b',
            messages=[
                {
                    'role': 'system',
                    'content': system_prompt
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            format="json"
        )
        # Extract the response content
        response_text = response['message']['content'].strip()
        verbose_print(f"Response:\n<{response_text}>")
        
        # Try to parse as JSON
        # Sometimes the response might have markdown code blocks
        if response_text.startswith('```'):
            # Remove markdown code blocks
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
            response_text = response_text.strip()
        
        # Parse JSON
        objects = json.loads(response_text)
        
        # Ensure it's a list
        if isinstance(objects, list):
            return objects
        else:
            return [objects] if objects else []
            
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        print(f"Response was: {response_text}")
        return []
    except Exception as e:
        print(f"Error calling Ollama: {e}")
        return []

# Example usage:
# video_id = open("video_ids_long.txt").read().splitlines()[0]
# narrations_person = data_narrations[
#     data_narrations.unique_narration_id.str.startswith(video_id) 
# ]
# row = narrations_person.iloc[0]
# 
# # Get available objects for this video
# available_objects = [obj_data['name'] for obj_data in data_assoc[video_id].values()]
# 
# # Link objects to action
# linked_objects = link_objects_to_action(
#     narration=row['narration'],
#     nouns=row['nouns'],
#     available_objects=available_objects
# )
# print(f"Linked objects: {linked_objects}")


def main():
    print(f"Processing video: {args.video_id}")

    # Ensure the Qwen3 8B model is loaded before using it.
    ensure_ollama_model_loaded("qwen3:8b")

    with open("scene-and-object-movements/assoc_info.json") as f:
        data_assoc = json.load(f)

    with open("narrations-and-action-segments/HD_EPIC_Narrations.pkl", "rb") as f:
        data_narrations = pickle.load(f)

    object_trace_data = data_assoc[args.video_id]
    objects_available = [elem['name'] for elem in object_trace_data.values()]

    narrations_person = data_narrations[
        data_narrations.unique_narration_id.str.startswith(args.video_id)
    ]
    ## Sort by start timestamp
    narrations_person = narrations_person.sort_values(by="start_timestamp")

    system_prompt = """You are an expert at analyzing cooking actions and identifying which objects are used in each action.
    Given a narration describing an action and a list of nouns mentioned, you need to identify which objects from the available object list are actually used in this action.
    Return a JSON array of object names that are relevant to the action and an explanation of why these objects are relevant to the action. Consider all possible interpretations of the nouns."""
        
    examples = [
        {
            "narration": "put the box of foil paper inside the second drawer.",
            "nouns": ['box of foil paper', 'second drawer'],
            "objects_available": ['foil2', 'unrolled foil', 'foil wrap', 'box of foil wrap', 'pie2', 'plate2', 'plate', 'fork', 'pie', 'plastic spoon', 'tray', 'oven glove'],
            "objects_used": ["box of foil paper"],
            "explanation": "The `box of foil paper` noun is present in the `objects_available` list verbatim."
        },
        {
            "narration": "Push the pies already on the plate slightly to the left emptying space. The pies are pushed using the spoon which has the new pie.",
            "nouns": ['pies', 'plate', 'left emptying space', 'spoon', 'new pie'],
            "objects_available": ['foil2', 'unrolled foil', 'foil wrap', 'box of foil wrap', 'pie2', 'plate2', 'plate', 'fork', 'pie', 'plastic spoon', 'tray', 'oven glove'],
            "objects_used": ["plate", "plate2", "plastic spoon", "pie", "pie2"],
            "explanation": "The `plate` noun corresponds with the `plate` and `plate2` objects in the `objects_available` list. The `spoon` noun corresponds with the `plastic spoon` object in the `objects_available` list. The `new pie` and `pies` nouns correspond with the `pie` and `pie2` objects in the `objects_available` list."
        }
    ]
        
    output_filename = f"linked_objects_{args.video_id}.jsonl"
    with open(output_filename, "r") as infile:
        previous_entries = [json.loads(line) for line in infile]
    previous_trace_ids = [entry['trace_id'] for entry in previous_entries]

    for iter_idx, row in narrations_person.iterrows():
        trace_id = row['unique_narration_id']
        if trace_id in previous_trace_ids:
            print(f"Skipping {trace_id} since it already exists in {output_filename}")
            continue

        llm_response = link_objects_to_action(
            narration=row['narration'],
            nouns=row['nouns'],
            available_objects=objects_available,
            system_prompt=system_prompt,
            examples=examples
        )[0]
        # print(type(llm_response))
        # print(llm_response)
        # import pdb; pdb.set_trace()
        output_entry = {
            "trace_id": trace_id,
            "action_narration": row["narration"],
            "nouns": row["nouns"],
            "objects_used": llm_response.get("objects_used", ["ERROR"]),
            "explanation": llm_response.get("explanation", "ERROR"),
        }
        with open(output_filename, "a") as outfile:
            outfile.write(json.dumps(output_entry) + "\n")

    print(f"Linked objects written to {output_filename}")


if __name__ == "__main__":
    main()
