# JSON to Anthropic Claude Messages Format Converter

This directory contains Python utilities to convert JSON prompt structures into the Anthropic Claude Messages Format, which is required for using the Anthropic Claude API.

## Files

- `json_to_anthropic_prompt.py` - Comprehensive converter with detailed functions
- `anthropic_converter.py` - Simplified utility with easy-to-use functions
- `example_usage.py` - Example script showing how to use the converters
- `generated_prompt.json` - Sample JSON prompt structure to convert

## Quick Start

### Using the Simplified Converter

```python
from anthropic_converter import json_to_anthropic_messages

# Convert from file
messages = json_to_anthropic_messages("generated_prompt.json")

# Convert from dictionary
with open("generated_prompt.json", "r") as f:
    data = json.load(f)
messages = json_to_anthropic_messages(data)
```

### Command Line Usage

```bash
# Convert and save to file
python3 anthropic_converter.py generated_prompt.json output_messages.json

# Convert without saving (just display)
python3 anthropic_converter.py generated_prompt.json
```

## JSON Structure

The converter expects JSON files with the following structure:

```json
{
    "system_prompt": {
        "role": "Agent Role",
        "objective": "Main objective",
        "model_instructions": [
            {"point": "Instruction 1"},
            {"point": "Instruction 2"}
        ],
        "response_instructions": [
            {"point": "Response instruction 1"},
            {"point": "Response instruction 2"}
        ]
    },
    "user_prompt": {
        "positive_scenarios": [
            {
                "domain": "Domain Name",
                "categories": [
                    {
                        "type": "Category Type",
                        "info": [
                            {"point": "Info point 1"},
                            {"point": "Info point 2"}
                        ]
                    }
                ]
            }
        ],
        "analysis_instructions": {
            "instructions": [
                {"point": "Analysis step 1"},
                {"point": "Analysis step 2"}
            ],
            "confidence_score_assignment": {
                "positve_classication_score_guidelines": [
                    {"point": "Guideline 1"},
                    {"point": "Guideline 2"}
                ],
                "negative_classication_score_guidelines": [
                    {"point": "Guideline 1"},
                    {"point": "Guideline 2"}
                ]
            }
        },
        "output_instructions": [
            {"point": "Output instruction 1"},
            {"point": "Output instruction 2"}
        ],
        "examples": [
            {
                "prompt_input": {
                    "subject": "Email subject",
                    "body": "Email body content"
                },
                "prompt_output": {
                    "confidence_score": 0.85,
                    "classification_rationale": "Explanation"
                }
            }
        ]
    }
}
```

## Output Format

The converter produces a list of message objects in Anthropic Claude Messages Format:

```json
[
    {
        "role": "system",
        "content": "System message content..."
    },
    {
        "role": "user", 
        "content": "User message content..."
    }
]
```

## Usage with Anthropic Client

```python
import anthropic
from anthropic_converter import json_to_anthropic_messages

# Convert your JSON prompt
messages = json_to_anthropic_messages("generated_prompt.json")

# Use with Anthropic client
client = anthropic.Anthropic(api_key="your-api-key")

response = client.messages.create(
    model="claude-3-sonnet-20240229",
    max_tokens=1000,
    messages=messages
)

print(response.content[0].text)
```

## Functions Reference

### `json_to_anthropic_messages(json_data)`

Converts JSON prompt data to Anthropic Messages Format.

**Parameters:**
- `json_data`: Either a dictionary or file path string

**Returns:**
- List of message objects with `role` and `content` fields

### `convert_file(input_file, output_file=None)`

Converts a JSON file and optionally saves the result.

**Parameters:**
- `input_file`: Path to input JSON file
- `output_file`: Optional path to save converted messages

**Returns:**
- List of message objects

## Example Output

The converter transforms the structured JSON into a readable prompt format:

**System Message:**
```
Role: Email Classification Agent
Objective: Analyze and classify business emails as IN_SCOPE or OUT_OF_SCOPE...

Model Instructions:
• Examine the email's metadata including From, To fields, and subject line...
• Analyze the email body for content related to core business operations...

Response Instructions:
• Generate a confidence score between 0.0 and 1.0...
• Provide a clear, concise rationale explaining key factors...
```

**User Message:**
```
POSITIVE SCENARIOS (IN_SCOPE):

Internal Operations:
  Crew Management:
    • Crew scheduling, assignments, and rotation communications
    • Onboarding processes and documentation for new crew members...

ANALYSIS INSTRUCTIONS:
• First identify the sender domain and determine if it's internal...

EXAMPLES:

Example 1:
Subject: RE: SBN Pursuit | Broome crew change | May 21
Body: From: PST Captain (PST-Captain@Seabourn.com)...
Confidence Score: 0.8878365329568256
Classification Rationale: This email should be classified as IN_SCOPE...
```

## Error Handling

The converters include comprehensive error handling for:
- File not found errors
- Invalid JSON format
- Missing required fields
- Encoding issues

## Dependencies

- Python 3.6+
- Standard library modules: `json`, `typing`

No external dependencies required.

## Testing

Run the example script to test the conversion:

```bash
python3 example_usage.py
```

This will convert the `generated_prompt.json` file and display the results. 