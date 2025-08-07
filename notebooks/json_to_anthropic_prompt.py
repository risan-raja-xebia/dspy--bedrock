import json
from typing import Dict, List, Any

def convert_json_to_anthropic_messages(json_data: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Convert the JSON prompt structure to Anthropic Claude Messages Format.
    
    Args:
        json_data: The JSON data containing system_prompt and user_prompt
        
    Returns:
        List of message objects in Anthropic Messages Format
    """
    messages = []
    
    # Build system message
    system_content = build_system_content(json_data.get("system_prompt", {}))
    messages.append({
        "role": "system",
        "content": system_content
    })
    
    # Build user message
    user_content = build_user_content(json_data.get("user_prompt", {}))
    messages.append({
        "role": "user", 
        "content": user_content
    })
    
    return messages

def build_system_content(system_prompt: Dict[str, Any]) -> str:
    """Build the system message content from the system_prompt section."""
    content_parts = []
    
    # Role and objective
    if "role" in system_prompt:
        content_parts.append(f"Role: {system_prompt['role']}")
    
    if "objective" in system_prompt:
        content_parts.append(f"Objective: {system_prompt['objective']}")
    
    # Model instructions
    if "model_instructions" in system_prompt:
        content_parts.append("\nModel Instructions:")
        for instruction in system_prompt["model_instructions"]:
            if "point" in instruction:
                content_parts.append(f"• {instruction['point']}")
    
    # Response instructions
    if "response_instructions" in system_prompt:
        content_parts.append("\nResponse Instructions:")
        for instruction in system_prompt["response_instructions"]:
            if "point" in instruction:
                content_parts.append(f"• {instruction['point']}")
    
    return "\n".join(content_parts)

def build_user_content(user_prompt: Dict[str, Any]) -> str:
    """Build the user message content from the user_prompt section."""
    content_parts = []
    
    # Positive scenarios
    if "positive_scenarios" in user_prompt:
        content_parts.append("POSITIVE SCENARIOS (IN_SCOPE):")
        for scenario in user_prompt["positive_scenarios"]:
            if "domain" in scenario:
                content_parts.append(f"\n{scenario['domain']}:")
            
            if "categories" in scenario:
                for category in scenario["categories"]:
                    if "type" in category:
                        content_parts.append(f"  {category['type']}:")
                    
                    if "info" in category:
                        for info in category["info"]:
                            if "point" in info:
                                content_parts.append(f"    • {info['point']}")
    
    # Analysis instructions
    if "analysis_instructions" in user_prompt:
        analysis = user_prompt["analysis_instructions"]
        
        if "instructions" in analysis:
            content_parts.append("\nANALYSIS INSTRUCTIONS:")
            for instruction in analysis["instructions"]:
                if "point" in instruction:
                    content_parts.append(f"• {instruction['point']}")
        
        # Confidence score guidelines
        if "confidence_score_assignment" in analysis:
            confidence = analysis["confidence_score_assignment"]
            
            if "positve_classication_score_guidelines" in confidence:
                content_parts.append("\nPOSITIVE CLASSIFICATION SCORE GUIDELINES:")
                for guideline in confidence["positve_classication_score_guidelines"]:
                    if "point" in guideline:
                        content_parts.append(f"• {guideline['point']}")
            
            if "negative_classication_score_guidelines" in confidence:
                content_parts.append("\nNEGATIVE CLASSIFICATION SCORE GUIDELINES:")
                for guideline in confidence["negative_classication_score_guidelines"]:
                    if "point" in guideline:
                        content_parts.append(f"• {guideline['point']}")
    
    # Output instructions
    if "output_instructions" in user_prompt:
        content_parts.append("\nOUTPUT INSTRUCTIONS:")
        for instruction in user_prompt["output_instructions"]:
            if "point" in instruction:
                content_parts.append(f"• {instruction['point']}")
    
    # Examples
    if "examples" in user_prompt:
        content_parts.append("\nEXAMPLES:")
        for i, example in enumerate(user_prompt["examples"], 1):
            content_parts.append(f"\nExample {i}:")
            
            if "prompt_input" in example:
                input_data = example["prompt_input"]
                if "subject" in input_data:
                    content_parts.append(f"Subject: {input_data['subject']}")
                if "body" in input_data:
                    content_parts.append(f"Body: {input_data['body']}")
            
            if "prompt_output" in example:
                output_data = example["prompt_output"]
                if "confidence_score" in output_data:
                    content_parts.append(f"Confidence Score: {output_data['confidence_score']}")
                if "classification_rationale" in output_data:
                    content_parts.append(f"Classification Rationale: {output_data['classification_rationale']}")
    
    return "\n".join(content_parts)

def load_and_convert_json_file(file_path: str) -> List[Dict[str, str]]:
    """
    Load JSON file and convert to Anthropic Messages Format.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        List of message objects in Anthropic Messages Format
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    
    return convert_json_to_anthropic_messages(json_data)

def create_anthropic_client_prompt(messages: List[Dict[str, str]]) -> str:
    """
    Create a formatted string representation of the Anthropic Messages Format
    that can be used with the Anthropic client.
    
    Args:
        messages: List of message objects in Anthropic Messages Format
        
    Returns:
        Formatted string representation
    """
    formatted_messages = []
    for message in messages:
        formatted_messages.append(f"Role: {message['role']}")
        formatted_messages.append(f"Content: {message['content']}")
        formatted_messages.append("-" * 50)
    
    return "\n".join(formatted_messages)

# Example usage
if __name__ == "__main__":
    # Load the JSON file
    json_file_path = "generated_prompt.json"
    
    try:
        # Convert to Anthropic Messages Format
        messages = load_and_convert_json_file(json_file_path)
        
        # Print the formatted messages
        print("ANTHROPIC CLAUDE MESSAGES FORMAT:")
        print("=" * 50)
        print(create_anthropic_client_prompt(messages))
        
        # Also print as JSON for direct use with Anthropic client
        print("\n" + "=" * 50)
        print("JSON FORMAT FOR ANTHROPIC CLIENT:")
        print(json.dumps(messages, indent=2))
        
    except FileNotFoundError:
        print(f"Error: File '{json_file_path}' not found.")
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format - {e}")
    except Exception as e:
        print(f"Error: {e}") 