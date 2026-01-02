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


parser = argparse.ArgumentParser(description='Label object usage during time periods.')
parser.add_argument('--video_id', type=str, required=False,
                    help='Video ID to construct prompt_info file path (e.g., P01-20240202-171220)')
args = parser.parse_args()

VERBOSE = True
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
        verbose_print(f"Loaded model names: {loaded_model_names}")
        if model_name.split(":")[0] not in loaded_model_names:
            print(f"Pulling model {model_name} since it is not loaded...")
            ollama.pull(model_name)
        else:
            verbose_print(f"Model {model_name} is already loaded.")
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
    system_prompt = """You are an expert in analyzing kitchen activities to determine if an object is being used during a specific time period.

Your task is to determine whether a given object is being used during a specified time period. An object is considered "being used" if it is 
contributing to the high-level activity, either by actively being held by the person or passively performing a function as part of the high-level activity.

You will be given a history of events that occurred during the time period. The events include:
    - High-level activity
    - Low-level action narrations
    - Objects in the person's hand
    - Objects near the person
    - Atomic actions such as picking up and placing down

You must use Chain of Thought (CoT) reasoning to analyze the evidence step-by-step before providing your final answer. Think through the following questions:
1. If the object is in the person's hand at any point during this period, is the person using this object to perform the high-level activity? Otherwise, it is not being used.
2. If the object is not in the person's hand at any point during this period, is the object meaningfully contributing to the task being performed? Otherwise, it is not being used.

Respond in JSON format with the following structure:
{
  "is_used": true/false,
  "explanation": "Step-by-step Chain of Thought reasoning explaining your decision..."
}

Be thorough in your reasoning and provide clear evidence from the event history."""
    
    return system_prompt


def generate_user_prompt_example():
    example_1 = {
        "prompt": """Determine if the object "pot" is being used during the time period from 01:01 to 01:04.

Use Chain of Thought reasoning to analyze the event history below step-by-step before providing your final answer.

Event History:
Time: 01:01 (61.93s)
High-level task being performed: Clear the dishes
Objects currently in hand: []
Objects currently at `hob.001`: []
Human atomic action: pick up `pot` from `hob.001`

Time: 01:04 (64.52s)
High-level task being performed: Clear the dishes
Current scene narration:
  -  Put the pan with the strainer to the right of the sink.
Objects currently in hand: pot
Objects currently at `counter.006`: pot, strainer
Human atomic action: put down `pot` to `counter.006`


Provide your analysis using Chain of Thought reasoning, then output your answer in the required JSON format.""",
    "response": {
        "is_used": True,
        "explanation": "The object `pot` is moved from the hob to the counter while the person is clearing the dishes. The pot is meaningfully contributing to the high-level activity of clearing the dishes. Hence, it is being used."
    }
    }
    example_2 = {
        "prompt": """Determine if the object "plate" is being used during the time period from 00:54 to 00:59.

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


Provide your analysis using Chain of Thought reasoning, then output your answer in the required JSON format.""",
    "response": {
        "is_used": True,
        "explanation": "The object `plate` is in the person's hand while the person is piling meat pies. The plate is meaningfully contributing to the high-level activity of piling the meat pies. Hence, it is being used.",
    }
    }
    return [example_1, example_2]


def generate_user_prompt(entry):
    """
    Generate the user prompt for a specific entry.
    
    Args:
        entry: Dictionary containing object_name, time_start, time_end, and event_history
        
    Returns:
        User prompt string
    """
    object_name = entry['object_name']
    time_start = entry['time_start']
    time_end = entry['time_end']
    event_history = entry['event_history']
    
    time_start_str = seconds_to_minutes_seconds(time_start)
    time_end_str = seconds_to_minutes_seconds(time_end)
    
    formatted_history = format_event_history(event_history)
    
    prompt = f"""Determine if the object "{object_name}" is being used during the time period from {time_start_str} to {time_end_str}.

Use Chain of Thought reasoning to analyze the event history below step-by-step before providing your final answer.

Event History:
{formatted_history}

Provide your analysis using Chain of Thought reasoning, then output your answer in the required JSON format."""
    
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
{example['prompt']}
Response: {{
    "is_used": {example['response']['is_used']},
    "explanation": "{normalize_text(str(example['response']['explanation']))}"
}}
"""
    prompt = f"""{examples_prompt}\n\n{prompt}"""
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
    output_filename = os.path.join(output_dir, f"object_usage_labels_{args.video_id}.jsonl")
    
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
                    # Create a unique key from object_name, time_start, and time_end
                    key = (existing_entry.get('object_name'), 
                           existing_entry.get('time_start'), 
                           existing_entry.get('time_end'))
                    processed_entries.add(key)
                except json.JSONDecodeError as e:
                    print(f"Warning: Skipping invalid JSON line in existing file: {e}")
        print(f"Found {len(processed_entries)} already processed entries")
    
    # Generate system prompt
    system_prompt = generate_system_prompt()
    examples = generate_user_prompt_example()
    verbose_print(f"System prompt:\n<{system_prompt}>")
    verbose_print(f"Examples:\n<{examples}>")

    
    # Process each entry
    skipped_count = 0
    for idx, entry in enumerate(prompt_info):
        object_name = entry['object_name']
        time_start = entry['time_start']
        time_end = entry['time_end']
        
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
        verbose_print(f"LLM response JSON:\n<{llm_response_json}>")
        
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
