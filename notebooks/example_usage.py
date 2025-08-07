#!/usr/bin/env python3
"""
Example usage of the JSON to Anthropic Messages Format converter.
This script demonstrates how to convert the generated_prompt.json file
into a format suitable for use with the Anthropic Claude API.
"""

import json
import sys
import os

# Add the current directory to the path so we can import our converter
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from json_to_anthropic_prompt import load_and_convert_json_file, convert_json_to_anthropic_messages

def main():
    """Main function to demonstrate the conversion."""
    
    # Path to the JSON file
    json_file_path = "generated_prompt.json"
    
    print("Converting JSON to Anthropic Claude Messages Format...")
    print("=" * 60)
    
    try:
        # Convert the JSON file to Anthropic Messages Format
        messages = load_and_convert_json_file(json_file_path)
        
        # Display the converted messages
        print("CONVERTED MESSAGES:")
        print("=" * 60)
        
        for i, message in enumerate(messages, 1):
            print(f"\nMessage {i}:")
            print(f"Role: {message['role']}")
            print(f"Content Length: {len(message['content'])} characters")
            print(f"Content Preview: {message['content'][:200]}...")
            print("-" * 40)
        
        # Save the converted messages to a new JSON file
        output_file = "anthropic_messages.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(messages, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Conversion completed successfully!")
        print(f"📁 Output saved to: {output_file}")
        
        # Show how to use with Anthropic client
        print("\n" + "=" * 60)
        print("USAGE WITH ANTHROPIC CLIENT:")
        print("=" * 60)
        print("""
# Example usage with Anthropic client:
import anthropic

client = anthropic.Anthropic(api_key="your-api-key")

messages = load_and_convert_json_file("generated_prompt.json")

response = client.messages.create(
    model="claude-3-sonnet-20240229",
    max_tokens=1000,
    messages=messages
)

print(response.content[0].text)
        """)
        
    except FileNotFoundError:
        print(f"❌ Error: File '{json_file_path}' not found.")
        print("Make sure the JSON file is in the same directory as this script.")
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON format - {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main() 