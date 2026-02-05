#! /usr/bin/env python3

## Start ollama server: ./ollama/bin/ollama serve&
## Check ollama: ./ollama/bin/ollama ps

import os
import argparse
import json
import ollama
from datetime import datetime
import pdb
from utils import seconds_to_minutes_seconds
import unicodedata
import re
from prompt_utils import (
    generate_prompts_for_video,
    generate_system_prompt,
    format_event_history,
    normalize_text,
)


MODEL_NAME = "gpt-oss:20b"
NUM_TRIES = 3
MAX_NUM_PREDICT = 400
TEMPERATURE = 0.8
MAX_SEGMENT_LENGTH = 120

parser = argparse.ArgumentParser(description='Label object usage during time periods.')
parser.add_argument('--video_id', type=str, required=False,
                    help='Video ID to construct prompt_info file path (e.g., P01-20240202-171220)')
parser.add_argument('--model_name', type=str, required=False, default=MODEL_NAME,
                    help='Model name to use (e.g., gpt-oss:20b)')
parser.add_argument('--temperature', type=float, required=False, default=TEMPERATURE,
                    help='Temperature to use (e.g., 0.8)')
parser.add_argument('--max_num_predict', type=int, required=False, default=MAX_NUM_PREDICT,
                    help='Maximum number of predictions to use (e.g., 400)')
parser.add_argument('--num_tries', type=int, required=False, default=NUM_TRIES,
                    help='Number of tries to use (e.g., 3)')
parser.add_argument('--max_segment_length', type=int, required=False, default=MAX_SEGMENT_LENGTH,
                    help='Maximum segment length in seconds for prompt generation (default: 120)')
parser.add_argument('--long', action='store_true',
                    help='Include full scene graph in prompts instead of just objects at specific fixture')
args = parser.parse_args()

VERBOSE = False

if args.long:
    from incontext_examples.examples_objectUsage_long import PASSIVE_KETTLE_LONG, PASSIVE_FORK_LONG, ACTIVE_RIGHTGLOVE_LONG, ACTIVE_PLATE_LONG
    LLM_EXAMPLE_PROMPTS = {
        "passive": [PASSIVE_KETTLE_LONG, PASSIVE_FORK_LONG],
        "active": [ACTIVE_RIGHTGLOVE_LONG, ACTIVE_PLATE_LONG],
    }
else:
    from incontext_examples.examples_objectUsage_short import PASSIVE_KETTLE_SHORT, PASSIVE_FORK_SHORT, ACTIVE_RIGHTGLOVE_SHORT, ACTIVE_PLATE_SHORT
    LLM_EXAMPLE_PROMPTS = {
        "passive": [PASSIVE_KETTLE_SHORT, PASSIVE_FORK_SHORT],
        "active": [ACTIVE_RIGHTGLOVE_SHORT, ACTIVE_PLATE_SHORT],
    }


def count_tokens(s):
    """Calculate number of tokens in system_prompt and prompt"""
    # Basic whitespace tokenizer as a fallback
    if not isinstance(s, str):
        s = str(s)
    return len(s.split())


def ensure_ollama_model_loaded(model_name):
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


def generate_system_prompt():
    """
    Generate the system prompt for object usage labeling.
    
    Returns:
        System prompt string
    """
    system_prompt = """You are an expert in analyzing kitchen activities to determine if an object is being used during a specific time period. Your task is to determine whether a given object is being used during a specified time period, along with a clear explanation of your reasoning.
    
You will be given a history of events that occurred during the time period. The events include:
    - High-level activity
    - Low-level action narrations
    - Current object locations (e.g., in the person's hand, on the countertop, etc.)
    - Atomic actions such as picking up and placing down

An object is considered 'being used' if it is contributing to the high-level activity, either by actively being held by the person or passively performing a function as part of the high-level activity.
Analyze the evidence step-by-step before providing your final answer, and provide a clear explanation of your reasoning. Think through the following questions:
    1. If the object is in the person's hand during this period, is the person using this object to perform the high-level activity? Otherwise, it is not being used.
    2. If the object is not in the person's hand during this period, is the object meaningfully contributing to the task being performed? Otherwise, it is not being used.

Provide your analysis using Chain of Thought reasoning, and respond with the following JSON structure:""" + """
{
  'is_used': true/false,
  'explanation': 'Step-by-step Chain of Thought reasoning explaining your decision...'
}"""
    
    return normalize_text(system_prompt)


def generate_user_prompt(entry, show_empty: bool = False):
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
    
    formatted_history = format_event_history(event_history, show_empty=show_empty)

    prompt = f"""Determine if the object '{object_name}' is being used during the time period between {time_start_str} ({time_start:.2f}s) and {time_end_str} ({time_end:.2f}s).

Analyze the event history before providing your final answer using step-by-step Chain of Thought reasoning.

Event History:
{formatted_history}

Respond with the following JSON structure:""" + """
{
  'is_used': true/false,
  'explanation': 'Step-by-step Chain of Thought reasoning explaining your decision...'
}"""
    
    return normalize_text(prompt)


def call_ollama_object_usage(system_prompt, prompt, examples, model_args):
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
    response_raw = None
    num_attempts = 0
    while not success and num_attempts < model_args["num_tries"]:
        num_attempts += 1
        # Call Ollama
        try:

            system_tokens = count_tokens(system_prompt)
            prompt_tokens = count_tokens(prompt)
            verbose_print(f"System prompt tokens: {system_tokens}")
            verbose_print(f"User prompt tokens: {prompt_tokens}")
            # pdb.set_trace()

            json_schema = {
                "type": "object",
                "properties": {
                    "is_used": {"type": "boolean"},
                    "explanation": {"type": "string"}
                },
                "required": ["is_used", "explanation"]
            }
            response = ollama.chat(
                model=model_args["model_name"],
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
                format=json_schema,
                options={"temperature": model_args["temperature"], "num_predict": model_args["max_num_predict"], "num_ctx": 150000},
            )
            # Extract the response content
            response_raw = normalize_text(response['message']['content'])
            verbose_print(f"--------------------------------\nResponse:\n<{response_raw}>")
            
            # Parse JSON
            response_json = json.loads(response_raw)
            if "explanation" in response_json and "is_used" in response_json:
                success = True
                return response_json, response_raw
            else:
                print(f"Warning: Missing explanation or is_used in LLM response (attempt {num_attempts}/{args.num_tries}): <{response_raw}>")
                if num_attempts >= args.num_tries:
                    break
                continue

        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response (attempt {num_attempts}/{args.num_tries}): {e}")
            # if response_raw is not None:
            #     print(f"Response was: <{response_raw}>")
            if num_attempts >= args.num_tries:
                break
            continue  # Retry instead of returning

        except Exception as e:
            print(f"Error calling Ollama (attempt {num_attempts}/{args.num_tries}): {e}")
            if num_attempts >= args.num_tries:
                break
            continue  # Retry instead of returning
    
    # If we exhausted all tries without success, return empty values
    print(f"Failed to get valid response after {args.num_tries} attempts. Returning empty response.")
    return {}, response_raw


def main():
    # Determine input file path
    if args.video_id:
        long_suffix = "_long" if args.long else ""
        prompt_info_path = f"outputs/prompts/prompt_info_{args.video_id}_max_segment_length_{args.max_segment_length}{long_suffix}.json"
    else:
        parser.error("Arg --video_id must be provided")
    
    ## Print args
    print(f"Args: {args}")
    print(f"Video ID: {args.video_id}")
    print(f"Model name: {args.model_name}")
    print(f"Temperature: {args.temperature}")
    print(f"Max number of predictions: {args.max_num_predict}")
    print(f"Number of tries: {args.num_tries}")
    print(f"Max segment length: {args.max_segment_length}")
    print(f"Long mode (full scene graph): {args.long}")

    model_args = {
        "model_name": args.model_name,
        "temperature": float(args.temperature),
        "max_num_predict": int(args.max_num_predict),
        "num_tries": int(args.num_tries),
    }
    
    # Always generate prompts (will delete old file if it exists)
    print(f"Generating prompts for video_id: {args.video_id} with max_segment_length: {args.max_segment_length}, long: {args.long}")
    generate_prompts_for_video(args.video_id, args.max_segment_length, long=args.long)
    print(f"Generated prompts saved to: {prompt_info_path}")
    
    print(f"Processing prompt info file: {prompt_info_path}")
    
    # Ensure the model is loaded
    ensure_ollama_model_loaded(args.model_name)
    
    # Load prompt info
    with open(prompt_info_path, 'r', encoding='utf-8') as f:
        prompt_info = json.load(f)
    
    print(f"Found {len(prompt_info)} entries to process")
    
    # Determine output file path
    datetime_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    long_suffix = "_long" if args.long else ""
    output_dir = f"outputs/object_usage_labels_model-{args.model_name}_max-segment-length-{args.max_segment_length}{long_suffix}_temp-{int(100*args.temperature)}_numPredict-{args.max_num_predict}_tries-{args.num_tries}"
    os.makedirs(output_dir, exist_ok=True)
    output_filename = os.path.join(output_dir, f"object_usage_labels_{args.video_id}.jsonl")
    
    # Load already processed entries to avoid reprocessing
    ## Entry is processed if it has an LLM response JSON with explanation and is_used, and is_used is a boolean.
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
                    if "llm_response_json" in existing_entry:
                        llm_response_json = existing_entry['llm_response_json']
                        if "explanation" in llm_response_json and "is_used" in llm_response_json:
                            if isinstance(llm_response_json['is_used'], bool):
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
    

    show_empty = True if args.long else False

    # Process each entry
    skipped_count = 0
    for idx, entry in enumerate(prompt_info):
        object_name = entry['object_name']
        time_start = entry['time_start']
        time_end = entry['time_end']
        
        # Generate system prompt
        examples = LLM_EXAMPLE_PROMPTS[entry['segment_category']]

        # Check if this entry has already been processed
        entry_key = (object_name, time_start, time_end)
        if entry_key in processed_entries:
            skipped_count += 1
            print(f"Skipping entry {idx + 1}/{len(prompt_info)}: {object_name} ({time_start:.2f}s - {time_end:.2f}s) - already processed")
            continue
        
        print(f"Processing entry {idx + 1}/{len(prompt_info)}: {object_name} ({time_start:.2f}s - {time_end:.2f}s)")
        
        # Generate prompts
        user_prompt = generate_user_prompt(entry, show_empty=show_empty)
        verbose_print(f"User prompt:\n<{user_prompt}>\n\n--------------------------------")
        
        # Call ollama
        llm_response_json, llm_response_raw = call_ollama_object_usage(
            system_prompt, user_prompt, examples, model_args=model_args,
        )
        llm_response_text = json.dumps(llm_response_json, ensure_ascii=False)
        verbose_print(f"LLM response text:\n<{llm_response_text}>")
        
        # Prepare output entry
        output_entry = {
            "object_name": object_name,
            "time_start": time_start,
            "segment_category": entry['segment_category'],
            "llm_response_raw": llm_response_raw,
            "llm_response_json": llm_response_json,
            "llm_response_text": llm_response_text,
            "time_end": time_end,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "examples": examples,
            "datetime_str": datetime_str,
        }
        
        # Write to JSONL file
        with open(output_filename, "a", encoding='utf-8') as outfile:
            outfile.write(json.dumps(output_entry, ensure_ascii=False) + "\n")
    
    processed_count = len(prompt_info) - skipped_count
    print(f"\nCompleted! Processed {processed_count} entries, skipped {skipped_count} already processed entries.")
    print(f"Results written to {output_filename}")


if __name__ == "__main__":
    main()
