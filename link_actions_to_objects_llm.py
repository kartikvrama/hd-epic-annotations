#! /usr/bin/env python3

## Start ollama server: ./ollama/bin/ollama serve&
## Check ollama: ./ollama/bin/ollama ps

import os
import argparse
import json
import pickle
import ollama
from utils import seconds_to_minutes_seconds
import pdb
import unicodedata
import re


parser = argparse.ArgumentParser(description='Process a video by its ID.')
parser.add_argument('--video_id', required=True, type=str, help='ID of the video')
args = parser.parse_args()

VERBOSE = False
MODEL_NAME = "gpt-oss:20b"


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


def normalize_text(text):
    """
    Normalize text to avoid encoding errors by replacing problematic Unicode characters.
    Handles em-dash, en-dash, and other common problematic characters.
    """
    if not isinstance(text, str):
        return text
    
    # Normalize Unicode characters (NFD normalization helps with composed characters)
    text = unicodedata.normalize('NFD', text)
    
    # Replace common problematic Unicode characters with ASCII equivalents
    replacements = {
        '\u2011': '-',  # non-breaking hyphen
        '\u2013': '-',  # en-dash
        '\u2014': '-',  # em-dash
        '\u2015': '-',  # horizontal bar
        '\u2018': "'",  # left single quotation mark
        '\u2019': "'",  # right single quotation mark
        '\u201C': '"',  # left double quotation mark
        '\u201D': '"',  # right double quotation mark
        '\u2026': '...',  # horizontal ellipsis
        '\u00A0': ' ',  # non-breaking space
        '\u200B': '',   # zero-width space
        '\u200C': '',   # zero-width non-joiner
        '\u200D': '',   # zero-width joiner
        '\uFEFF': '',   # zero-width no-break space (BOM)
    }
    
    for unicode_char, replacement in replacements.items():
        text = text.replace(unicode_char, replacement)
    
    # Remove any remaining non-printable control characters except newlines and tabs
    text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F-\x9F]', '', text)
    
    return text


def extract_event_history(object_movement_video, mask_fixture_video):

    def _format_fixture_name(fixture_name):
        if fixture_name is None:
            return "unknown"
        if not "_" in fixture_name:
            return fixture_name
        return fixture_name.split("_")[1]

    event_history = []
    for assoc_id, assoc_data in object_movement_video.items():
        for track in assoc_data["tracks"]:
            pick_time = track["time_segment"][0]
            pick_fixture = mask_fixture_video[track["masks"][0]]["fixture"]
            event_history.append(
                (
                    pick_time,
                    'PICK',
                    f"[{seconds_to_minutes_seconds(pick_time)}] `{assoc_data['name']}` picked from `{_format_fixture_name(pick_fixture)}`"
                )
            )
            drop_time = track["time_segment"][1]
            if len(track["masks"]) > 1:
                drop_fixture = mask_fixture_video[track["masks"][1]]["fixture"]
            else:
                drop_fixture = "unknown"
            event_history.append(
                (
                    drop_time,
                    'DROP',
                    f"[{seconds_to_minutes_seconds(drop_time)}] `{assoc_data['name']}` dropped to `{_format_fixture_name(drop_fixture)}`"
                )
            )
    event_history.sort(key=lambda x: x[0])
    return event_history


def generate_prompt_object_linking(action_description, available_objects, event_history, system_prompt, examples):
    """
    Generate a prompt for linking objects to actions based on narration and nouns.
    
    Args:
        action_description: Action description
        available_objects: List of available object names to choose from
        event_history: Event history
        system_prompt: System prompt
        examples: Examples
    
    Returns:
        Prompt
    """
    # Build the prompt with examples
    prompt = f"""Examples:
"""
    
    for i, example in enumerate(examples, 1):
        prompt += f"""
Example {i}:
Action Start Time: {example['action_start_time']}
Action End Time: {example['action_end_time']}
Narration: {normalize_text(str(example['narration']))}
Nouns: {json.dumps(example['nouns'], ensure_ascii=False)}
Available objects: {json.dumps(example['objects_available'], ensure_ascii=False)}
Event History: {normalize_text(str(example['event_history']))}
Response:
{{
  "objects_used": {json.dumps(example['objects_used'], ensure_ascii=False)},
  "explanation": "{normalize_text(str(example['explanation']))}"
}}
"""
    
    start_timestamp = action_description['start_timestamp']
    end_timestamp = action_description['end_timestamp']
    event_pos_before_action = [i for i, event in enumerate(event_history) if event[0] < start_timestamp]
    if not event_pos_before_action:
        event_pos_before_action = [0]
    event_pos_after_action = [i for i, event in enumerate(event_history) if event[0] > end_timestamp]
    if not event_pos_after_action:
        event_pos_after_action = [len(event_history)-1]
    event_history_filtered = [elem[-1] for elem in event_history[event_pos_before_action[-1]:event_pos_after_action[0]+1]]
    # Add the current task
    prompt += f"""
Task:
Action Start Time: {seconds_to_minutes_seconds(start_timestamp)}
Action End Time: {seconds_to_minutes_seconds(end_timestamp)}
Narration: {normalize_text(str(action_description['narration']))}
Nouns: {json.dumps(action_description['nouns'], ensure_ascii=False)}
Available objects: {json.dumps(available_objects, ensure_ascii=False)}
Event History:
{chr(10).join("  "+normalize_text(str(event)) for event in event_history_filtered)}
Response: """
    return normalize_text(system_prompt), normalize_text(prompt)
    
def call_ollama_object_linking(system_prompt, prompt, model_name=MODEL_NAME):
    """
    Call Ollama to link objects to actions based on narration and nouns.
    
    Args:
        system_prompt: System prompt
        prompt: Prompt
        model_name: Model name
    
    Returns:
        Response processed, Response text
    """
    verbose_print(f"System prompt:\n<{system_prompt}>")
    verbose_print(f"Prompt:\n<{prompt}>")

    # Call Ollama
    try:
        # Construct the expected JSON response format for Ollama
        response = ollama.chat(
            model=model_name,
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
        response_text = normalize_text(response['message']['content'].strip())
        verbose_print(f"--------------------------------\nResponse:\n<{response_text}>")
        
        # Parse JSON
        response_json = json.loads(response_text)
        return response_json, response_text

    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        print(f"Response was: {response_text}")
        return {}, response_text

    except Exception as e:
        print(f"Error calling Ollama: {e}")
        return {}, "ERROR"


def main():
    print(f"Processing video: {args.video_id}")

    # Ensure the Qwen3 8B model is loaded before using it.
    ensure_ollama_model_loaded(MODEL_NAME)

    with open("scene-and-object-movements/assoc_info.json", encoding='utf-8') as f:
        object_movement_dict = json.load(f)

    with open("scene-and-object-movements/mask_info.json", "r", encoding='utf-8') as f:
        mask_fixture_dict = json.load(f)

    with open("narrations-and-action-segments/HD_EPIC_Narrations.pkl", "rb") as f:
        data_narrations = pickle.load(f)

    object_movement_example = object_movement_dict[args.video_id]
    mask_fixture_example = mask_fixture_dict[args.video_id]
    objects_available_all = [elem['name'] for elem in object_movement_example.values()]
    event_history_example = extract_event_history(object_movement_example, mask_fixture_example)

    narrations_person = data_narrations[
        data_narrations.unique_narration_id.str.startswith(args.video_id)
    ]
    ## Sort by start timestamp
    narrations_person = narrations_person.sort_values(by="start_timestamp")

    system_prompt = """You are an expert in analyzing kitchen actions to determine which objects are involved in each action.
You will be given:
    * An action narration (a textual description of the action)
    * A list of nouns mentioned in the narration
    * A list of available objects in the scene
    * A timeline of pick and drop events that occur during the action

Your task is to identify which objects from the available list are actually used in the described action, considering both the narration/nouns and the pick/drop event overlaps. Also return an explanation justifying why these objects are deemed relevant, referencing the list of objects available, the narration, nouns, and event information.
Be clear and specific in your reasoning."""
    response_format = {
        "objects_used": ["<list of object names as strings>"],
        "explanation": "<concise explanation>"
    }
    system_prompt += f"\n\nRespond ONLY in the following JSON format: {json.dumps(response_format, ensure_ascii=False)}"
    system_prompt = normalize_text(system_prompt)
        
    examples = [
        # {
        #     "action_start_time": "00:20",
        #     "action_end_time": "00:21",
        #     "narration": "Take off the oven's glove.",
        #     "nouns": ["oven's glove"],
        #     "objects_available": ["foil2", "unrolled foil", "foil wrap", "box of foil wrap", "pie2", "plate2", "plate", "fork", "pie", "plastic spoon", "tray", "oven glove", "Track 19 (skipped)"],
        #     "event_history": """
        #     [00:19] `tray` dropped to `hob.001`
        #     [00:21] `oven glove` dropped to `counter.002`
        #     """,
        #     "objects_used": ["oven glove"],
        #     "explanation": "The `oven glove` noun is dropped to the counter in the event history during the action start and end times. The narration mentions taking off the glove, which is likely the `oven glove` object."
        # },
        {
            "action_start_time": "02:52",
            "action_end_time": "02:53",
            "narration": "Put down the plate on the countertop, now fully covered with foil with all edges tucked in.",
            "nouns": ["plate", "countertop", "foil", "edges"],
            "objects_available": ["foil2", "unrolled foil", "foil wrap", "box of foil wrap", "pie2", "plate2", "plate", "fork", "pie", "plastic spoon", "tray", "oven glove", "Track 19 (skipped)"],
            "event_history": """
    [02:44] `foil2` picked from `counter.009`
    [02:53] `foil2` dropped to `counter.009`
    [02:53] `foil2` picked from `counter.009`""",
            "objects_used": ["foil2"],
            "explanation": "The `foil2` object is picked up and dropped to the counter in the event history during the action start and end times. The narration mentions a plate covered with foil, which is likely the `foil2` object. The `plate` object is not mentioned in the event history."
        },
        {
            "action_start_time": "01:04",
            "action_end_time": "01:04",
            "narration": "Put the pan with the strainer to the right of the sink.",
            "nouns": ["pan", "strainer", "right of sink"],
            "objects_available": ["knife2", "plastic spoon", "strainer2", "mug2", "container's cover", "small gold color container", "second cover", "cover of flask", "flask", "glass2", "mug", "kettle", "bag of bagels", "notepad", "glass", "water filter jug", "plastic bag", "wooden stick", "food processing bin", "plug", "disk", "candy floss machine", "second sponge", "pot3", "strainer", "bottle of washing up liquid", "sponge", "left glove", "right glove", "pot", "knife", "container", "plate2", "empty pot", "plate", "ladle", "scale", "bowl", "tissue"],
            "event_history": """
    [01:01] `pot` picked from `hob.001`
    [01:04] `pot` dropped to `counter.006`
    [01:04] `right glove` picked from `sink.001`""",
            "objects_used": ["pot"],
            "explanation": "The `pot` object is dropped to the counter in the event history during the action start and end times. The narration mentions a pan with the strainer, which is likely the `pot` object. The `strainer` object is not mentioned in the event history."
        },
        {
            "action_start_time": "00:27",
            "action_end_time": "00:28",
            "narration": "Open the tap using the right handle.",
            "nouns": ["tap", "right handle"],
            "objects_available": ["knife2", "plastic spoon", "strainer2", "mug2", "container's cover", "small gold color container", "second cover", "cover of flask", "flask", "glass2", "mug", "kettle", "bag of bagels", "notepad", "glass", "water filter jug", "plastic bag", "wooden stick", "food processing bin", "plug", "disk", "candy floss machine", "second sponge", "pot3", "strainer", "bottle of washing up liquid", "sponge", "left glove", "right glove", "pot", "knife", "container", "plate2", "empty pot", "plate", "ladle", "scale", "bowl", "tissue"],
            "event_history": """
    [00:26] `plate` dropped to `counter.003`
    [00:30] `ladle` dropped to `counter.004`""",
            "objects_used": [],
            "explanation": "The `plate` and `ladle` objects are dropped to the counter in the event history, but they are moved outside the action start and end times and not mentioned in the narration. The `tap` and `right handle` nouns are not present in the `objects_available` list."
        },
    ]
        
    
    output_folder = f"outputs/linked_objects_llm_{MODEL_NAME}"
    os.makedirs(output_folder, exist_ok=True)
    output_filename_linked_objects = os.path.join(output_folder, f"linked_objects_{MODEL_NAME}_{args.video_id}.jsonl")
    output_filename_llm_input_response = os.path.join(output_folder, f"llm_input_response_{MODEL_NAME}_{args.video_id}.jsonl")
    if os.path.exists(output_filename_linked_objects):
        with open(output_filename_linked_objects, "r", encoding='utf-8') as infile:
            previous_entries = [json.loads(line) for line in infile]
        previous_trace_ids = [entry['trace_id'] for entry in previous_entries]
    else:
        previous_trace_ids = []
    for iter_idx, row in narrations_person.iterrows():
        trace_id = row['unique_narration_id']
        if trace_id in previous_trace_ids:
            verbose_print(f"Skipping {trace_id} since it already exists in {output_filename_linked_objects}")
            continue

        system_prompt, prompt = generate_prompt_object_linking(row, objects_available_all, event_history_example, system_prompt, examples)
        llm_response_json, llm_response_text = call_ollama_object_linking(system_prompt, prompt)
        output_llm_input_response = {
            "system_prompt": system_prompt,
            "prompt": prompt,
            "response": llm_response_text,
        }
        with open(output_filename_llm_input_response, "a", encoding='utf-8') as outfile:
            outfile.write(json.dumps(output_llm_input_response, ensure_ascii=False) + "\n")

        if not isinstance(llm_response_json, dict):
            llm_response_json = {
                "objects_used": ["ERROR"],
                "explanation": "ERROR",
            }
        llm_response = {
            "objects_used": llm_response_json.get("objects_used", ["ERROR"]),
            "explanation": llm_response_json.get("explanation", "ERROR"),
        }
        output_entry = {
            "trace_id": trace_id,
            "action_narration": normalize_text(str(row["narration"])),
            "nouns": row["nouns"],
            "objects_used": llm_response.get("objects_used", ["ERROR"]),
            "explanation": normalize_text(str(llm_response.get("explanation", "ERROR"))),
        }
        with open(output_filename_linked_objects, "a", encoding='utf-8') as outfile:
            outfile.write(json.dumps(output_entry, ensure_ascii=False) + "\n")

    verbose_print(f"Linked objects written to {output_filename_linked_objects}")
    verbose_print(f"LLM input and response written to {output_filename_llm_input_response}")


if __name__ == "__main__":
    main()
