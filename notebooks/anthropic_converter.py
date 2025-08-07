#!/usr/bin/env python3
"""
Simple utility for converting JSON prompt structures to Anthropic Claude Messages Format.
This module provides easy-to-use functions for converting prompt JSON files to the format
required by the Anthropic Claude API.
"""

import json
from typing import Dict, List, Any, Union

def json_to_anthropic_messages(json_data: Union[Dict, str]) -> List[Dict[str, str]]:
    """
    Convert JSON prompt data to Anthropic Claude Messages Format.
    
    Args:
        json_data: Either a dictionary containing the prompt data or a file path to a JSON file
        
    Returns:
        List of message objects in Anthropic Messages Format
        
    Example:
        # From dictionary
        messages = json_to_anthropic_messages(prompt_dict)
        
        # From file path
        messages = json_to_anthropic_messages("prompt.json")
    """
    if isinstance(json_data, str):
        # Assume it's a file path
        with open(json_data, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
    
    return _convert_to_messages(json_data)

def _convert_to_messages(data: Dict[str, Any]) -> List[Dict[str, str]]:
    """Internal function to convert data structure to messages."""
    messages = []
    
    # System message
    if "system_prompt" in data:
        system_content = _build_system_content(data["system_prompt"])
        messages.append({
            "role": "system",
            "content": system_content
        })
    
    # User message
    if "user_prompt" in data:
        user_content = _build_user_content(data["user_prompt"])
        messages.append({
            "role": "user",
            "content": user_content
        })
    
    return messages

def _build_system_content(system_prompt: Dict[str, Any]) -> str:
    """Build system message content."""
    parts = []
    
    if "role" in system_prompt:
        parts.append(f"Role: {system_prompt['role']}")
    
    if "objective" in system_prompt:
        parts.append(f"Objective: {system_prompt['objective']}")
    
    if "model_instructions" in system_prompt:
        parts.append("\n## Model Instructions:")
        for instruction in system_prompt["model_instructions"]:
            if "point" in instruction:
                parts.append(f"• {instruction['point']}")
    
    if "response_instructions" in system_prompt:
        parts.append("\n## Response Instructions:")
        for instruction in system_prompt["response_instructions"]:
            if "point" in instruction:
                parts.append(f"• {instruction['point']}")
    
    return "\n".join(parts)

def _build_user_content(user_prompt: Dict[str, Any]) -> str:
    """Build user message content."""
    parts = []
    
    # Positive scenarios
    if "positive_scenarios" in user_prompt:
        parts.append("\n## POSITIVE SCENARIOS (OUT_OF_SCOPE):")
        for scenario in user_prompt["positive_scenarios"]:
            if "domain" in scenario:
                parts.append(f"\n{scenario['domain']}:")
            
            if "categories" in scenario:
                for category in scenario["categories"]:
                    if "type" in category:
                        parts.append(f"  {category['type']}:")
                    
                    if "info" in category:
                        for info in category["info"]:
                            if "point" in info:
                                parts.append(f"    • {info['point']}")
    
    # Analysis instructions
    if "analysis_instructions" in user_prompt:
        analysis = user_prompt["analysis_instructions"]
        
        if "instructions" in analysis:
            parts.append("\n## ANALYSIS INSTRUCTIONS:")
            for instruction in analysis["instructions"]:
                if "point" in instruction:
                    parts.append(f"• {instruction['point']}")
        
        # Confidence score guidelines
        if "confidence_score_assignment" in analysis:
            confidence = analysis["confidence_score_assignment"]
            
            if "positve_classication_score_guidelines" in confidence:
                parts.append("\n###  POSITIVE CLASSIFICATION SCORE GUIDELINES:")
                for guideline in confidence["positve_classication_score_guidelines"]:
                    if "point" in guideline:
                        parts.append(f"• {guideline['point']}")
            
            if "negative_classication_score_guidelines" in confidence:
                parts.append("\n###  NEGATIVE CLASSIFICATION SCORE GUIDELINES:")
                for guideline in confidence["negative_classication_score_guidelines"]:
                    if "point" in guideline:
                        parts.append(f"• {guideline['point']}")
    
    # Output instructions
    if "output_instructions" in user_prompt:
        parts.append("\n## OUTPUT INSTRUCTIONS:")
        for instruction in user_prompt["output_instructions"]:
            if "point" in instruction:
                parts.append(f"• {instruction['point']}")
    
    # Examples
    if "examples" in user_prompt:
        parts.append("\n## EXAMPLES:")
        for i, example in enumerate(user_prompt["examples"], 1):
            parts.append(f"\nExample {i}:")
            parts.append("\n Input: \n")
            if "prompt_input" in example:
                input_data = example["prompt_input"]
                if "subject" in input_data:
                    parts.append(f"Subject: {input_data['subject']}")
                if "body" in input_data:
                    body_lines = input_data['body'].split('\n')
                    body_lines = [line.strip() for line in body_lines if len(line.strip()) > 0]
                    parts.append(f"Body: {'\n'.join(body_lines)}")
            parts.append("\n Output: \n")
            if "prompt_output" in example:
                output_data = example["prompt_output"]
                if "confidence_score" in output_data:
                    parts.append(f"Confidence Score: {output_data['confidence_score']}")
                if "classification_rationale" in output_data:
                    parts.append(f"Classification Rationale: {output_data['classification_rationale']}")
                if "classification_label" in output_data:
                    parts.append(f"Classification Label: {output_data['classification_label']}")
            
            parts.append("\n\n"+'-'*100 +"\n")
    
    return "\n".join(parts)

# Convenience function for direct file conversion
def convert_file(input_file: str, output_file: str = None) -> List[Dict[str, str]]:
    """
    Convert a JSON file to Anthropic Messages Format and optionally save the result.
    
    Args:
        input_file: Path to the input JSON file
        output_file: Optional path to save the converted messages (as JSON)
        
    Returns:
        List of message objects in Anthropic Messages Format
    """
    messages = json_to_anthropic_messages(input_file)
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(messages, f, indent=2, ensure_ascii=False)
        print(f"✅ Converted messages saved to: {output_file}")
    
    return messages

if __name__ == "__main__":
    # Simple command-line usage
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python anthropic_converter.py <input_file> [output_file]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        messages = convert_file(input_file, output_file)
        print(f"✅ Successfully converted {len(messages)} messages")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1) 