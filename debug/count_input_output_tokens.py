#!/usr/bin/env python3
"""Simple script to count tokens for system prompt, input prompt, and output response in JSONL files."""

import json
import glob

try:
    import tiktoken
    encoding = tiktoken.get_encoding("cl100k_base")
    def count_tokens(text):
        if not text:
            return 0
        if not isinstance(text, str):
            text = str(text)
        return len(encoding.encode(text))
except ImportError:
    def count_tokens(text):
        if not text:
            return 0
        if not isinstance(text, str):
            text = str(text)
        return len(text) // 4  # Rough estimate


# Process all JSONL files
jsonl_files = sorted(glob.glob("../outputs/object_usage_labels_temp1_gptoss_noOutputLimit/*.jsonl"))

print(f"Processing {len(jsonl_files)} file(s)...\n")

system_token_counts = []
input_token_counts = []
output_token_counts = []
total_token_counts = []

for filepath in jsonl_files:
    print(f"{filepath}:")
    
    with open(filepath, 'r') as f:
        for line in f:
            entry = json.loads(line)
            
            # Count system prompt tokens
            system_prompt = entry.get('system_prompt', '')
            system_tokens = count_tokens(system_prompt)
            
            # Count input/user prompt tokens
            user_prompt = entry.get('user_prompt', '')
            input_tokens = count_tokens(user_prompt) + sum(count_tokens(example["prompt"] + example["response"]["explanation"] + str(example["response"]["is_used"])) for example in entry.get('examples', []))
            
            # Count output response tokens
            response_text = entry.get('llm_response_text', '')
            if not response_text:
                response_text = json.dumps(entry.get('llm_response_json', {}))
            output_tokens = count_tokens(response_text)
            
            # Total tokens (system + input + output)
            total_tokens = system_tokens + input_tokens + output_tokens
            
            system_token_counts.append(system_tokens)
            input_token_counts.append(input_tokens)
            output_token_counts.append(output_tokens)
            total_token_counts.append(total_tokens)
            
            object_name = entry.get('object_name', 'unknown')
            print(f"  {object_name}:")
            print(f"    System prompt: {system_tokens} tokens")
            print(f"    Input prompt: {input_tokens} tokens")
            print(f"    Output response: {output_tokens} tokens")
            print(f"    Total: {total_tokens} tokens")
            
            # if output_tokens > 300:
            #     print(f"    WARNING: Large output response ({output_tokens} tokens)")
            #     print(response_text)
            #     input("Look at this response, so big?")
    
if system_token_counts:
    print(f"\nSummary for {filepath}:")
    print(f"  System prompt tokens - Total: {sum(system_token_counts)}, Avg: {sum(system_token_counts)/len(system_token_counts):.1f}, Min: {min(system_token_counts)}, Max: {max(system_token_counts)}")
    print(f"  Input prompt tokens - Total: {sum(input_token_counts)}, Avg: {sum(input_token_counts)/len(input_token_counts):.1f}, Min: {min(input_token_counts)}, Max: {max(input_token_counts)}")
    print(f"  Output response tokens - Total: {sum(output_token_counts)}, Avg: {sum(output_token_counts)/len(output_token_counts):.1f}, Min: {min(output_token_counts)}, Max: {max(output_token_counts)}")
    print(f"  Total tokens (system+input+output) - Total: {sum(total_token_counts)}, Avg: {sum(total_token_counts)/len(total_token_counts):.1f}, Min: {min(total_token_counts)}, Max: {max(total_token_counts)}")
print()
