#!/usr/bin/env python3
"""
Script to save all user prompts for a given video ID.
This is useful for generating new examples for the prompt system.
"""

import os
import sys
import json
import argparse
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prompt_utils import generate_prompts_for_video, normalize_text, format_event_history, seconds_to_minutes_seconds
import pdb


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



def main():
    parser = argparse.ArgumentParser(description='Save all user prompts for a video ID')
    parser.add_argument('--video_id', type=str, required=True,
                        help='Video ID to process (e.g., P01-20240202-171220)')
    parser.add_argument('--max_segment_length', type=int, default=120,
                        help='Maximum segment length in seconds (default: 120)')
    parser.add_argument('--long', action='store_true',
                        help='Use long mode prompts (with full scene graph)')
    parser.add_argument('--output_file', type=str, default=None,
                        help='Output file path (default: outputs/prompts/user_prompts_{video_id}.json)')
    args = parser.parse_args()
    
    if not args.video_id:
        parser.error("Arg --video_id must be provided")
    
    # Always generate prompts (will delete old file if it exists)
    print(f"Generating prompts for video_id: {args.video_id} with max_segment_length: {args.max_segment_length}, long: {args.long}")
    long_suffix = "_long" if args.long else ""
    prompt_info_path = f"outputs/prompts/prompt_info_{args.video_id}_max_segment_length_{args.max_segment_length}{long_suffix}.json"
    generate_prompts_for_video(args.video_id, args.max_segment_length, long=args.long)
    print(f"Generated prompts saved to: {prompt_info_path}")
    
    # Load prompt info
    with open(prompt_info_path, 'r', encoding='utf-8') as f:
        prompt_info = json.load(f)
    
    print(f"Found {len(prompt_info)} entries to process")
    
    show_empty = True if args.long else False

    # Generate all user prompts
    all_prompts = []
    for idx, entry in enumerate(prompt_info):
        object_name = entry['object_name']
        time_start = entry['time_start']
        time_end = entry['time_end']
        segment_category = entry['segment_category']
        
        print(f"Processing entry {idx + 1}/{len(prompt_info)}: {object_name} ({time_start:.2f}s - {time_end:.2f}s) [{segment_category}]")
        pdb.set_trace()

        user_prompt = generate_user_prompt(entry, show_empty=show_empty)
        
        prompt_entry = {
            "object_name": object_name,
            "time_start": time_start,
            "time_end": time_end,
            "segment_category": segment_category,
            "prompt": user_prompt
        }
        
        all_prompts.append(prompt_entry)
    
    # Determine output file path
    if args.output_file:
        output_file = args.output_file
    else:
        output_dir = "outputs/prompts"
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"user_prompts_{args.video_id}_max_segment_length_{args.max_segment_length}{long_suffix}.jsonl")

    # Write all the prompts in a text file
    text_output_file = output_file.rsplit('.', 1)[0] + ".txt"
    with open(text_output_file, 'w', encoding='utf-8') as text_f:
        for prompt in all_prompts:
            text_f.write(f"{prompt['object_name']} ({prompt['time_start']:.2f}s - {prompt['time_end']:.2f}s) [{prompt['segment_category']}]\n<{prompt['prompt']}>\n\n")
    print(f"Also saved plain text prompts to {text_output_file}")
    
    # Save all prompts
    print(f"\nSaving {len(all_prompts)} prompts to: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        for prompt in all_prompts:
            f.write(json.dumps(prompt, ensure_ascii=False) + "\n")
    
    print(f"Successfully saved all prompts to {output_file}")


if __name__ == "__main__":
    main()
