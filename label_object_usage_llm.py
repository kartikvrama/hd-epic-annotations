#! /usr/bin/env python3

## Start ollama server: ./ollama/bin/ollama serve&
## Check ollama: ./ollama/bin/ollama ps

import os
import argparse
import json
import ollama
from utils import seconds_to_minutes_seconds
import unicodedata
import re
import pdb


parser = argparse.ArgumentParser(description='Label object usage during time periods.')
parser.add_argument('--video_id', type=str, required=False,
                    help='Video ID to construct prompt_info file path (e.g., P01-20240202-171220)')
args = parser.parse_args()

VERBOSE = False
MODEL_NAME = "gpt-oss:20b"


def ensure_ollama_model_loaded(model_name=MODEL_NAME):
    """Ensure the specified ollama model is loaded."""
    try:
        models = ollama.list().get("models", [])
        loaded_model_names = set()
        for m in models:
            # Some entries may not have a "name" key, so use get with fallback
            name = m.get("name") or m.get("model") or ""
            if not name:
                continue
            loaded_model_names.add(name.split(":")[0])
        print(f"Loaded model names: {loaded_model_names}")
        if model_name.split(":")[0] not in loaded_model_names:
            print(f"Pulling model {model_name} since it is not loaded...")
            ollama.pull(model_name)
        else:
            print(f"Model {model_name} is already loaded.")
    except Exception as e:
        print(f"Error while checking/loading model '{model_name}': {e}")


def verbose_print(*args, **kwargs):
    """Print only if VERBOSE is True."""
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


def format_event_history(event_history):
    """
    Format event history into a readable string for the prompt.
    
    Args:
        event_history: List of event dictionaries
        
    Returns:
        Formatted string representation of event history
    """
    lines = []
    for event in event_history:
        event_lines = []
        event_lines.append(f"Time: {event['time_str']} ({event['time']:.2f}s)")
        event_lines.append(f"High-level task being performed: {event['high_level_activity']}")
        
        if event.get('action_narrations'):
            narrations = event['action_narrations']
            if narrations:
                event_lines.append("Current scene narration:")
                for narration in narrations:
                    event_lines.append(f"  - {narration}")
        
        if event.get('objects_in_hand'):
            event_lines.append(f"Objects currently in hand: {', '.join(event['objects_in_hand'])}")
        else:
            event_lines.append("Objects currently in hand: []")
        
        if event.get('nearby_objects_fixture'):
            event_lines.append(f"Objects currently at `{event['fixture']}`: {', '.join(event['nearby_objects_fixture'])}")
        else:
            event_lines.append(f"Objects currently at `{event['fixture']}`: []")

        action = "pick up" if event['action'] == "PICK" else "put down" if event['action'] == "DROP" else event['action']
        action_event = f"{action} `{event['object']}` from `{event['fixture']}`" if event['action'] == "PICK" else f"{action} `{event['object']}` to `{event['fixture']}`"
        event_lines.append(f"Human atomic action: {action_event}")
        
        lines.append("\n".join(event_lines))
        lines.append("")  # Empty line between events
    
    return "\n".join(lines)


def generate_system_prompt():
    """
    Generate the system prompt for object usage labeling.
    
    Returns:
        System prompt string
    """
    system_prompt = """You are an expert in analyzing kitchen activities to determine if an object is being used during a specific time period. Your task is to determine whether a given object is being used during a specified time period.
    
You will be given a history of events that occurred during the time period. The events include:
    - High-level activity
    - Low-level action narrations
    - Current object locations (e.g., in the person's hand, on the countertop, etc.)
    - Atomic actions such as picking up and placing down

An object is considered 'being used' if it is contributing to the high-level activity, either by actively being held by the person or passively performing a function as part of the high-level activity.
You must use Chain of Thought (CoT) reasoning to analyze the evidence step-by-step before providing your final answer. Think through the following questions:
    1. If the object is in the person's hand during this period, is the person using this object to perform the high-level activity? Otherwise, it is not being used.
    2. If the object is not in the person's hand during this period, is the object meaningfully contributing to the task being performed? Otherwise, it is not being used.

Respond in JSON format with the following structure:
{
  'is_used': true/false,
  'explanation': 'Step-by-step Chain of Thought reasoning explaining your decision...'
}

Be thorough in your reasoning and provide clear evidence from the event history."""
    
    return normalize_text(system_prompt)


def generate_user_prompt_example_active():
    example_a1 = {
        "prompt": """Determine if the object "right glove" is being used during the time period between 02:57 (177.84s) and 02:58 (178.20s).

Use Chain of Thought reasoning to analyze the event history below step-by-step before providing your final answer.

Event History:
Time: 02:57 (177.84s)
High-level task being performed: Prepare candy floss
Objects currently in hand: []
Objects currently at `sink.001`: left glove, empty pot, bowl
Human atomic action: pick up `right glove` from `sink.001`

Time: 02:58 (178.20s)
High-level task being performed: Drink some water
Current scene narration:
  -  Touch the glove then release it.
Objects currently in hand: right glove
Objects currently at `sink.001`: left glove, right glove, empty pot, bowl
Human atomic action: put down `right glove` to `sink.001`
""",
    "response": {
        "is_used": False,
        "explanation": "The object `right glove` is briefly touched by the person during the time period, but is not being used to perform the high-level activity of preparing candy floss. Hence, it is not being used."
    }
    }

    example_a2 = {
        "prompt": """Determine if the object "plate" is being used during the time period between 00:54 (54.69s) and 00:59 (59.63s).

Use Chain of Thought reasoning to analyze the event history below step-by-step before providing your final answer.

Event History:
Time: 00:54 (54.69s)
High-level task being performed: Pick up the second tray from the oven, pile the meat pies on two plate and cover one of them using foil paper
Current scene narration:
  - pick up a plate, that's the top of the pile of plates, on the lower shelf of the cupboard.
Objects currently in hand: []
Objects currently at `cupboard.008`: []
Human atomic action: pick up `plate` from `cupboard.008`

Time: 00:56 (56.40s)
High-level task being performed: Pick up the second tray from the oven, pile the meat pies on two plate and cover one of them using foil paper
Current scene narration:
  - pick up the plastic spoon from the countertop.
Objects currently in hand: plate
Objects currently at `counter.002`: plate2, fork, oven glove
Human atomic action: pick up `plastic spoon` from `counter.002`

Time: 00:57 (57.37s)
High-level task being performed: Pick up the second tray from the oven, pile the meat pies on two plate and cover one of them using foil paper
Current scene narration:
  - Move the plate filled with pies to the right of the countertop so that to empty space next to the hob to place the other plate.
Objects currently in hand: plate, plastic spoon
Objects currently at `counter.002`: oven glove, fork
Human atomic action: pick up `plate2` from `counter.002`

Time: 00:58 (58.36s)
High-level task being performed: Pick up the second tray from the oven, pile the meat pies on two plate and cover one of them using foil paper
Current scene narration:
  - Move the plate filled with pies to the right of the countertop so that to empty space next to the hob to place the other plate.
Objects currently in hand: plate2, plate, plastic spoon
Objects currently at `counter.002`: oven glove, plate2, fork
Human atomic action: put down `plate2` to `counter.002`

Time: 00:59 (59.63s)
High-level task being performed: Pick up the second tray from the oven, pile the meat pies on two plate and cover one of them using foil paper
Objects currently in hand: plate, plastic spoon
Objects currently at `counter.002`: plate2, fork, oven glove, plate
Human atomic action: put down `plate` to `counter.002`
""",
    "response": {
        "is_used": True,
        "explanation": "The object `plate` is in the person's hand while the person is piling meat pies. The plate is meaningfully contributing to the high-level activity of piling the meat pies. Hence, it is being used.",
    }
    }

    return [example_a2, example_a1]

def generate_user_prompt_example_passive():

    example_p1 = {
        "prompt": """Determine if the object "kettle" is being used during the time period from 03:38 (218.07s) to 04:28 (268.78s).

Use Chain of Thought reasoning to analyze the event history below step-by-step before providing your final answer.

Event History:
Time: 03:38 (218.07s)
High-level task being performed: Brew tea
Current scene narration:
  -  Put down the kettle back on its base.
Objects currently in hand: kettle
Objects currently at `counter.003`: kettle, water filter jug, glass
Human atomic action: put down `kettle` to `counter.003`

Time: 03:41 (221.71s)
High-level task being performed: Brew tea
Current scene narration:
  -  Move a mug at the bottom shelf of the cupboard without picking it up.
Objects currently in hand: []
Objects currently at `cupboard.009`: flask, glass2, mug2
Human atomic action: pick up `mug` from `cupboard.009`

Time: 03:42 (222.72s)
High-level task being performed: Brew tea
Current scene narration:
  -  Move a mug at the bottom shelf of the cupboard without picking it up.
Objects currently in hand: mug
Objects currently at `cupboard.009`: glass2, mug, mug2, flask
Human atomic action: put down `mug` to `cupboard.009`

Time: 03:43 (223.67s)
High-level task being performed: Brew tea
Current scene narration:
  -  Move a glass at the second shelf of the cupboard without picking it up, so as to access what's behind it.
Objects currently in hand: []
Objects currently at `cupboard.009`: flask, mug, mug2
Human atomic action: pick up `glass2` from `cupboard.009`

Time: 03:44 (224.22s)
High-level task being performed: Brew tea
Current scene narration:
  -  Move a glass at the second shelf of the cupboard without picking it up, so as to access what's behind it.
Objects currently in hand: glass2
Objects currently at `cupboard.009`: glass2, mug, mug2, flask
Human atomic action: put down `glass2` to `cupboard.009`

Time: 03:44 (224.66s)
High-level task being performed: Brew tea
Objects currently in hand: []
Objects currently at `cupboard.009`: glass2, mug, mug2
Human atomic action: pick up `flask` from `cupboard.009`

Time: 03:46 (226.77s)
High-level task being performed: Brew tea
Current scene narration:
  -  Open the cover of the flask by holding the flask using the left hand, holding the cover with the right hand, turning the cover counterclockwise to release it and then lifting it up.
Objects currently in hand: flask
Objects currently at `mid-air`: []
Human atomic action: pick up `cover of flask` from `mid-air`

Time: 03:47 (227.34s)
High-level task being performed: Brew tea
Current scene narration:
  -  Put the cover on the counter top.
Objects currently in hand: flask, cover of flask
Objects currently at `counter.002`: container's cover, cover of flask, second cover, bag of bagels
Human atomic action: put down `cover of flask` to `counter.002`

Time: 03:47 (227.79s)
High-level task being performed: Brew tea
Current scene narration:
  -  Pick up the second cover using the right hand.
Objects currently in hand: flask
Objects currently at `counter.002`: container's cover, cover of flask, bag of bagels
Human atomic action: pick up `second cover` from `counter.002`

Time: 03:48 (228.17s)
High-level task being performed: Brew tea
Current scene narration:
  -  Put the second cover on the counter top.
Objects currently in hand: flask, second cover
Objects currently at `counter.002`: container's cover, cover of flask, flask, bag of bagels
Human atomic action: put down `flask` to `counter.002`

Time: 03:48 (228.33s)
High-level task being performed: Brew tea
Current scene narration:
  -  Put the second cover on the counter top.
Objects currently in hand: second cover
Objects currently at `counter.002`: container's cover, cover of flask, flask, second cover, bag of bagels
Human atomic action: put down `second cover` to `counter.002`

Time: 03:50 (230.83s)
High-level task being performed: Brew tea
Objects currently in hand: []
Objects currently at `shelf.003`: []
Human atomic action: pick up `small gold color container` from `shelf.003`

Time: 03:55 (235.24s)
High-level task being performed: Brew tea
Current scene narration:
  -  Open the container by holding it with the left hand and then pulling its cover with the right hand.
Objects currently in hand: small gold color container
Objects currently at `counter.002`: flask, cover of flask, second cover, bag of bagels
Human atomic action: pick up `container's cover` from `counter.002`

Time: 04:04 (244.74s)
High-level task being performed: Brew tea
Current scene narration:
  -  Put down the empty container on the countertop.
Objects currently in hand: container's cover, small gold color container
Objects currently at `counter.009`: small gold color container
Human atomic action: put down `small gold color container` to `counter.009`

Time: 04:05 (245.26s)
High-level task being performed: Brew tea
Current scene narration:
  -  Open the trash bin's lid.
  -  Throw the container's cover in the trash, using the right hand.
Objects currently in hand: container's cover
Objects currently at `storage.001`: container's cover
Human atomic action: put down `container's cover` to `storage.001`

Time: 04:18 (258.82s)
High-level task being performed: Brew tea
Current scene narration:
  -  Pick up a mug from the bottom shelf by holding it with the left hand from its bottom. The mug is upside down.
Objects currently in hand: []
Objects currently at `cupboard.009`: glass2, mug
Human atomic action: pick up `mug2` from `cupboard.009`

Time: 04:21 (261.30s)
High-level task being performed: Brew tea
Current scene narration:
  -  Put down the mug on the counter top.
Objects currently in hand: mug2
Objects currently at `dishwasher.001`: knife, plate, mug2, container, plate2
Human atomic action: put down `mug2` to `dishwasher.001`

Time: 04:24 (264.20s)
High-level task being performed: Brew tea
Current scene narration:
  -  Pick up a small plastic strainer from the cutlery drawer using the right hand.
Objects currently in hand: []
Objects currently at `drawer.003`: []
Human atomic action: pick up `strainer2` from `drawer.003`

Time: 04:26 (266.79s)
High-level task being performed: Brew tea
Current scene narration:
  -  Place the strainer on top of the mug. The strainer will be used to separate the tea from the loose tea.
Objects currently in hand: strainer2
Objects currently at `counter.002`: cover of flask, flask, second cover, strainer2, bag of bagels
Human atomic action: put down `strainer2` to `counter.002`

Time: 04:28 (268.78s)
High-level task being performed: Brew tea
Current scene narration:
  -  pick up the kettle from its base.
Objects currently in hand: []
Objects currently at `counter.003`: water filter jug, glass
Human atomic action: pick up `kettle` from `counter.003`
""",
    "response": {
        "is_used": True,
        "explanation": "The object `kettle` is not in the person's hand between 218.07s and 268.78s. However, the user is currently preparing the mug to brew tea, and the kettle is likely boiling water for the tea. Hence, it is being used."
    }
    }

    example_p2 = {
        "prompt": """Determine if the object "fork" is being used during the time period between 00:00 (0.00s) and 00:33 (33.57s).

Use Chain of Thought reasoning to analyze the event history below step-by-step before providing your final answer.

Event History:
Time: 00:04 (4.61s)
High-level task being performed: Pick up the second tray from the oven, pile the meat pies on two plate and cover one of them using foil paper
Current scene narration:
  - Pick up the oven glove from the countertop using the right hand.
Objects currently in hand: []
Objects currently at `counter.002`: plastic spoon, fork, plate2
Human atomic action: pick up `oven glove` from `counter.002`

Time: 00:13 (13.05s)
High-level task being performed: Pick up the second tray from the oven, pile the meat pies on two plate and cover one of them using foil paper
Objects currently in hand: oven glove
Objects currently at `oven.001`: []
Human atomic action: pick up `tray` from `oven.001`

Time: 00:14 (14.70s)
High-level task being performed: Pick up the second tray from the oven, pile the meat pies on two plate and cover one of them using foil paper
Current scene narration:
  - Pick up the tray from the upper shelf of the oven using the right hand holding the oven glove by sliding it out.
Objects currently in hand: tray, oven glove
Objects currently at `oven.001`: tray
Human atomic action: put down `tray` to `oven.001`

Time: 00:15 (15.48s)
High-level task being performed: Pick up the second tray from the oven, pile the meat pies on two plate and cover one of them using foil paper
Current scene narration:
  - Pick up the tray from the upper shelf of the oven using the right hand holding the oven glove by sliding it out.
Objects currently in hand: oven glove
Objects currently at `oven.001`: []
Human atomic action: pick up `tray` from `oven.001`

Time: 00:19 (19.39s)
High-level task being performed: Pick up the second tray from the oven, pile the meat pies on two plate and cover one of them using foil paper
Current scene narration:
  - Put the tray on the hob.
Objects currently in hand: tray, oven glove
Objects currently at `hob.001`: pie2, pie, tray
Human atomic action: put down `tray` to `hob.001`

Time: 00:21 (21.39s)
High-level task being performed: Pick up the second tray from the oven, pile the meat pies on two plate and cover one of them using foil paper
Current scene narration:
  - Throw the oven's glove on the countertop using the right hand.
Objects currently in hand: oven glove
Objects currently at `counter.002`: oven glove, plastic spoon, fork, plate2
Human atomic action: put down `oven glove` to `counter.002`

Time: 00:21 (21.70s)
High-level task being performed: Pick up the second tray from the oven, pile the meat pies on two plate and cover one of them using foil paper
Current scene narration:
  - Throw the oven's glove on the countertop using the right hand.
Objects currently in hand: []
Objects currently at `counter.002`: oven glove, fork, plate2
Human atomic action: pick up `plastic spoon` from `counter.002`

Time: 00:27 (27.58s)
High-level task being performed: Pick up the second tray from the oven, pile the meat pies on two plate and cover one of them using foil paper
Current scene narration:
  - Pick up one meat pie from the tray using the plastic spoon by sliding the spoon under the pie and pulling it up, also using the left hand to break the pie from its neighboring pie.
Objects currently in hand: plastic spoon
Objects currently at `hob.001`: pie2, tray
Human atomic action: pick up `pie` from `hob.001`

Time: 00:28 (28.17s)
High-level task being performed: Pick up the second tray from the oven, pile the meat pies on two plate and cover one of them using foil paper
Objects currently in hand: plastic spoon, pie
Objects currently at `hob.001`: pie2, pie, tray
Human atomic action: put down `pie` to `hob.001`

Time: 00:33 (33.57s)
High-level task being performed: Pick up the second tray from the oven, pile the meat pies on two plate and cover one of them using foil paper
Current scene narration:
  - Pick up a fork from the countertop.
Objects currently in hand: plastic spoon
Objects currently at `counter.002`: oven glove, plate2
Human atomic action: pick up `fork` from `counter.002`
""",
    "response": {
        "is_used": False,
        "explanation": "The object `fork` is not in the person's hand between 4.61s and 33.57s. The activity until 33.57s is about piling meat pies, and none of the action narrations mention before 00:33s or after 00:04s mention using the fork. Hence, it is not being used."
    }
    }

    return [example_p1, example_p2]

def generate_user_prompt(entry):
    """
    Generate the user prompt for a specific entry.
    
    Args:
        entry: Dictionary containing object_name, time_start, time_end, and event_history
        
    Returns:
        User prompt string
    """
    object_name = entry['object_name']
    time_start = float(entry['time_start'])
    time_end = float(entry['time_end'])
    event_history = entry['event_history']
    
    time_start_str = seconds_to_minutes_seconds(time_start)
    time_end_str = seconds_to_minutes_seconds(time_end)
    
    formatted_history = format_event_history(event_history)

    prompt = f"""Determine if the object '{object_name}' is being used during the time period between {time_start_str} ({time_start:.2f}s) and {time_end_str} ({time_end:.2f}s).

Use Chain of Thought reasoning to analyze the event history below step-by-step before providing your final answer.

Event History:
{formatted_history}

Provide your analysis using Chain of Thought reasoning, and then respond in JSON format with the following structure:""" + """
{
  'is_used': true/false,
  'explanation': 'Step-by-step Chain of Thought reasoning explaining your decision...'
}"""
    
    return normalize_text(prompt)


def call_ollama_object_usage(system_prompt, prompt, examples, model_name=MODEL_NAME):
    """
    Call Ollama to determine if an object is being used.
    
    Args:
        system_prompt: System prompt
        prompt: User prompt
        model_name: Model name
        examples: Examples
    Returns:
        Response JSON dict, Response text
    """
    examples_prompt = "Examples:"
    for i, example in enumerate(examples, 1):
        examples_prompt += f"""
Example {i}:
{normalize_text(example['prompt'])}

Response: {{
    'is_used': {example['response']['is_used']},
    'explanation': '{normalize_text(str(example['response']['explanation']))}'
}}
"""
    prompt = f"""{normalize_text(examples_prompt)}\n\n{normalize_text(prompt)}"""
    success = False
    response_text = None
    while not success:
        # Call Ollama
        try:
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
                format="json",
                options={"temperature": 0.0},
            )
            # Extract the response content
            response_text = normalize_text(response['message']['content'].strip())
            verbose_print(f"--------------------------------\nResponse:\n<{response_text}>")
            
            # Parse JSON
            response_json = json.loads(response_text)
            if "explanation" in response_json and "is_used" in response_json:
                success = True
                return response_json, response_text
            else:
                print(f"Warning: Missing explanation or is_used in LLM response: <{response_text}>")
                continue

        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            if response_text is not None:
                print(f"Response was: {response_text}")
            continue  # Retry instead of returning

        except Exception as e:
            print(f"Error calling Ollama: {e}")
            continue  # Retry instead of returning


def main():
    # Determine input file path
    if args.video_id:
        prompt_info_path = f"outputs/prompts/prompt_info_{args.video_id}.json"
    else:
        parser.error("Arg --video_id must be provided")
    
    if not os.path.exists(prompt_info_path):
        print(f"Error: File not found: {prompt_info_path}")
        return
    
    print(f"Processing prompt info file: {prompt_info_path}")
    
    # Ensure the model is loaded
    ensure_ollama_model_loaded(MODEL_NAME)
    
    # Load prompt info
    with open(prompt_info_path, 'r', encoding='utf-8') as f:
        prompt_info = json.load(f)
    
    print(f"Found {len(prompt_info)} entries to process")
    
    # Determine output file path
    output_dir = "outputs/object_usage_labels"
    os.makedirs(output_dir, exist_ok=True)
    output_filename = os.path.join(output_dir, f"object_usage_labels_diffExamples_{args.video_id}.jsonl")
    
    # Load already processed entries to avoid reprocessing
    processed_entries = set()
    if os.path.exists(output_filename):
        print(f"Loading existing entries from {output_filename}")
        with open(output_filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    existing_entry = json.loads(line)
                    if not existing_entry.get('llm_response_text'):
                        verbose_print(f"Warning: Skipping entry {existing_entry.get('object_name')} ({existing_entry.get('time_start')}s - {existing_entry.get('time_end')}s) - no LLM response text")
                        continue
                    if "explanation" not in existing_entry.get('llm_response_json') or "is_used" not in existing_entry.get('llm_response_json'):
                        verbose_print(f"Warning: Skipping entry {existing_entry.get('object_name')} ({existing_entry.get('time_start')}s - {existing_entry.get('time_end')}s) - missing explanation or is_used in LLM response")
                        continue
                    # Create a unique key from object_name, time_start, and time_end
                    key = (existing_entry.get('object_name'), 
                           existing_entry.get('time_start'), 
                           existing_entry.get('time_end'))
                    processed_entries.add(key)
                except json.JSONDecodeError as e:
                    print(f"Warning: Skipping invalid JSON line in existing file: {e}")
        print(f"Found {len(processed_entries)} already processed entries")
    
    system_prompt = generate_system_prompt()
    verbose_print(f"System prompt:\n<{system_prompt}>")
    
    # Process each entry
    skipped_count = 0
    for idx, entry in enumerate(prompt_info):
        object_name = entry['object_name']
        time_start = entry['time_start']
        time_end = entry['time_end']
        
        # Generate system prompt
        if entry['segment_category'] == "active":
            examples = generate_user_prompt_example_active()
        elif entry['segment_category'] == "passive":
            examples = generate_user_prompt_example_passive()
        else:
            raise ValueError(f"Invalid segment category: {entry['segment_category']}")

        # Check if this entry has already been processed
        entry_key = (object_name, time_start, time_end)
        if entry_key in processed_entries:
            skipped_count += 1
            print(f"Skipping entry {idx + 1}/{len(prompt_info)}: {object_name} ({time_start:.2f}s - {time_end:.2f}s) - already processed")
            continue
        
        print(f"Processing entry {idx + 1}/{len(prompt_info)}: {object_name} ({time_start:.2f}s - {time_end:.2f}s)")
        
        # Generate prompts
        user_prompt = generate_user_prompt(entry)
        verbose_print(f"User prompt:\n<{user_prompt}>\n\n--------------------------------")
        
        # Call ollama
        llm_response_json, llm_response_text = call_ollama_object_usage(system_prompt, user_prompt, examples)
        llm_response_text = json.dumps(llm_response_json, ensure_ascii=False)
        verbose_print(f"LLM response text:\n<{llm_response_text}>")
        
        # Prepare output entry
        output_entry = {
            "object_name": object_name,
            "time_start": time_start,
            "segment_category": entry['segment_category'],
            "llm_response_json": llm_response_json,
            "llm_response_text": llm_response_text,
            "time_end": time_end,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "examples": examples,
        }
        
        # Write to JSONL file
        with open(output_filename, "a", encoding='utf-8') as outfile:
            outfile.write(json.dumps(output_entry, ensure_ascii=False) + "\n")
    
    processed_count = len(prompt_info) - skipped_count
    print(f"\nCompleted! Processed {processed_count} entries, skipped {skipped_count} already processed entries.")
    print(f"Results written to {output_filename}")


if __name__ == "__main__":
    main()
