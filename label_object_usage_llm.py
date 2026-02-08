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
                    help='Video ID for output path (e.g., P01-20240202-171220); derived from --prompt_file if omitted')
parser.add_argument('--prompt_file', type=str, required=False, help='Path to prompt dict JSON')
parser.add_argument('--no_images', action='store_true',
                    help='Do not attach images to the prompt (text-only)')
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
args = parser.parse_args()

VERBOSE = False

# Default few-shot examples per segment_category (empty = no examples). Can be extended with prompt/response dicts.
LLM_EXAMPLE_PROMPTS = {
    "passive": [],
    "active": [],
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
    system_instruction = """
You are an expert Video Understanding Agent specialized in recognizing human-object interaction in kitchen environments. Your task is to annotate whether a specific object is **Functionally In Use** during a provided time window.

**Definition of 'Functionally In Use':**
An object is 'used' if it fulfills one of the following:
1. Active Functional Interaction: The user is manipulating the object to perform a meaningful action (e.g., cutting with a knife, flipping with a spatula, eating from a fork).
2. Passive Functional State: The object is currently fulfilling a function without human contact (e.g., a kettle boiling water, a bowl holding chopped ingredients, a pan searing meat on the stove).

**Exclusion Criteria (The object is NOT in use if):**
- Idle/Background: The object is visible but stationary and not serving any functional purpose.
- Aborted Interaction: The user touches or grabs the object but releases it without performing an action.
- Interim Holding: The user is holding the object briefly to perform a task with another object (e.g., grabbing an object from the front of the shelf to reach another object behind it).
- Maintenance/Inspecting: The user is holding the object to clean it or inspect its contents.



**Output Format:**
Provide your analysis using Chain of Thought reasoning, and respond with the following JSON structure:
{
  'is_used': boolean,
  'prediction_confidence': 'high/medium/low',
  'prediction_explanation': 'string'
}
"""
    return normalize_text(system_instruction)


def generate_user_prompt(entry, show_empty: bool = False):
    """
    Generate the user prompt for a specific entry.
    
    Args:
        entry: Dictionary containing object_name, time_start, time_end, and event_history
        
    Returns:
        User prompt string
    """
    target_object = entry['object_name']
    time_start = float(entry['time_start'])
    time_end = float(entry['time_end'])

    time_start_str = seconds_to_minutes_seconds(time_start)
    time_end_str = seconds_to_minutes_seconds(time_end)

    action_narrations = entry['action_narrations']
    ## Support both list-of-dicts (prompt_dict: {narration, start_timestamp, end_timestamp}) and list-of-strings
    narration_texts = [
        (n.get('narration', n) if isinstance(n, dict) else n) for n in action_narrations
    ]
    action_narrations_str = "\n".join([f"  - {t}" for t in narration_texts])
    
    prompt = f"""
Please analyze the following data:
**Target Object:** {target_object}
**Time Period:** {time_start_str} - {time_end_str}
**Action Narrations:** {action_narrations_str}
"""

    return normalize_text(prompt)


def call_ollama_object_usage(system_prompt, prompt, examples, model_args, image_paths=None):
    """
    Call Ollama to determine if an object is being used.

    Args:
        system_prompt: System prompt
        prompt: User prompt
        examples: Few-shot examples (list of dicts with 'prompt' and 'response')
        model_args: Dict with model_name, temperature, max_num_predict, num_tries
        image_paths: Optional list of image file paths to attach to the user message (for vision models)
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
                    "explanation": {"type": "string"},
                    "prediction_confidence": {"type": "string"}
                },
                "required": ["is_used", "explanation", "prediction_confidence"]
            }
            user_message = {'role': 'user', 'content': prompt}
            if image_paths:
                user_message['images'] = image_paths
            response = ollama.chat(
                model=model_args["model_name"],
                messages=[
                    {
                        'role': 'system',
                        'content': system_prompt
                    },
                    user_message
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


def _video_id_from_prompt_file(prompt_file):
    """Derive video_id from prompt_dict filename, e.g. prompt_dict_P07-20240529-131737_max_segment_length_30_long.json -> P07-20240529-131737"""
    basename = os.path.basename(prompt_file)
    if basename.startswith("prompt_dict_") and "_max_segment_length_" in basename:
        rest = basename[len("prompt_dict_"):]
        video_id = rest.split("_max_segment_length_")[0]
        return video_id
    return None


def main():
    # Resolve input file path: --prompt_file takes precedence; else build from --video_id
    if args.prompt_file:
        prompt_dict_path = os.path.abspath(args.prompt_file)
        if not os.path.isfile(prompt_dict_path):
            parser.error(f"Prompt file not found: {prompt_dict_path}")
        video_id = args.video_id or _video_id_from_prompt_file(prompt_dict_path)
        if not video_id:
            parser.error("Could not derive video_id from --prompt_file; provide --video_id")
    elif args.video_id:
        long_suffix = "_long"
        prompt_dict_path = f"outputs/prompts/prompt_dict_{args.video_id}_max_segment_length_{args.max_segment_length}{long_suffix}.json"
        if not os.path.isfile(prompt_dict_path):
            parser.error(f"Prompt file not found: {prompt_dict_path}. Use --prompt_file to specify path.")
        video_id = args.video_id
    else:
        parser.error("Provide either --prompt_file or --video_id")

    ## Print args
    print(f"Args: {args}")
    print(f"Prompt file: {prompt_dict_path}")
    print(f"Video ID: {video_id}")
    print(f"Model name: {args.model_name}")
    print(f"Temperature: {args.temperature}")
    print(f"Max number of predictions: {args.max_num_predict}")
    print(f"Number of tries: {args.num_tries}")
    print(f"Max segment length: {args.max_segment_length}")
    print(f"Include images: {not args.no_images}")

    model_args = {
        "model_name": args.model_name,
        "temperature": float(args.temperature),
        "max_num_predict": int(args.max_num_predict),
        "num_tries": int(args.num_tries),
    }

    with open(prompt_dict_path, "r", encoding="utf-8") as f:
        prompt_info = json.load(f)

    if not isinstance(prompt_info, list):
        parser.error("Prompt file must contain a JSON array of entries")

    # Ensure the model is loaded
    ensure_ollama_model_loaded(args.model_name)

    # Determine output file path
    datetime_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    long_suffix = "_long"
    output_dir = f"outputs/object_usage_labels_model-{args.model_name}_max-segment-length-{args.max_segment_length}{long_suffix}_temp-{int(100*args.temperature)}_numPredict-{args.max_num_predict}_tries-{args.num_tries}"
    os.makedirs(output_dir, exist_ok=True)
    output_filename = os.path.join(output_dir, f"object_usage_labels_{video_id}.jsonl")

    # Resume logic: load already processed entries (optional, currently disabled)
    processed_entries = set()

    system_prompt = generate_system_prompt()
    verbose_print(f"System prompt:\n<{system_prompt}>")

    show_empty = True

    # Process each entry
    skipped_count = 0
    for idx, entry in enumerate(prompt_info):
        object_name = entry["object_name"]
        time_start = entry["time_start"]
        time_end = entry["time_end"]

        # Examples for few-shot (by segment_category)
        segment_category = entry.get("segment_category", "passive")
        examples = LLM_EXAMPLE_PROMPTS.get(segment_category, LLM_EXAMPLE_PROMPTS["passive"])

        # Check if this entry has already been processed
        entry_key = (object_name, time_start, time_end)
        if entry_key in processed_entries:
            skipped_count += 1
            print(f"Skipping entry {idx + 1}/{len(prompt_info)}: {object_name} ({time_start:.2f}s - {time_end:.2f}s) - already processed")
            continue

        print(f"Processing entry {idx + 1}/{len(prompt_info)}: {object_name} ({time_start:.2f}s - {time_end:.2f}s)")

        # Resolve image paths for this entry (prompt_dict may have image_filepaths)
        image_paths = []
        if not args.no_images and entry.get("image_filepaths"):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            for p in entry["image_filepaths"]:
                if os.path.isabs(p) and os.path.isfile(p):
                    image_paths.append(p)
                elif os.path.isfile(p):
                    image_paths.append(os.path.abspath(p))
                else:
                    candidate = os.path.join(script_dir, p)
                    if os.path.isfile(candidate):
                        image_paths.append(candidate)
            if image_paths:
                verbose_print(f"Attaching {len(image_paths)} images to prompt")

        # Generate prompts
        user_prompt = generate_user_prompt(entry, show_empty=show_empty)
        verbose_print(f"User prompt:\n<{user_prompt}>\n\n--------------------------------")

        # Call ollama (with optional images for vision models)
        llm_response_json, llm_response_raw = call_ollama_object_usage(
            system_prompt, user_prompt, examples, model_args=model_args,
            image_paths=image_paths if image_paths else None,
        )
        llm_response_text = json.dumps(llm_response_json, ensure_ascii=False)
        verbose_print(f"LLM response text:\n<{llm_response_text}>")
        
        # Prepare output entry
        output_entry = {
            "object_name": object_name,
            "time_start": time_start,
            "segment_category": segment_category,
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
