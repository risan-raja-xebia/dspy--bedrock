"""
Prompt to Markdown Converter
"""

import json
import logging
from typing import Dict, List, Any, Union, Optional
from pathlib import Path
from functools import lru_cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PromptConversionError(Exception):
    """Custom exception for prompt conversion errors."""
    pass


def json_to_markdown(json_data: Union[Dict, str]) -> Dict[str, str]:
    """
    Convert JSON prompt data to markdown format based on Pydantic models.
    """
    try:
        if isinstance(json_data, str):
            # Assume it's a file path
            json_data = _load_json_file(json_data)
        
        if not isinstance(json_data, dict):
            raise PromptConversionError("Input must be a dictionary or valid JSON file path")
        
        return _convert_to_markdown(json_data)
    except Exception as e:
        logger.error(f"Failed to convert JSON to markdown: {e}")
        raise PromptConversionError(f"Conversion failed: {e}")


def _load_json_file(file_path: str) -> Dict[str, Any]:
    """Load JSON data from file with error handling."""
    try:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise PromptConversionError(f"Invalid JSON in file {file_path}: {e}")
    except Exception as e:
        raise PromptConversionError(f"Error reading file {file_path}: {e}")


def _convert_to_markdown(data: Dict[str, Any]) -> Dict[str, str]:
    """Internal function to convert data structure to markdown."""
    result = {}
    
    # System Prompt Section
    if "system_prompt" in data:
        result["system_prompt"] = _build_system_prompt_markdown(data["system_prompt"])
    
    # User Prompt Section
    if "user_prompt" in data:
        user_prompt_markdown = _build_user_prompt_markdown(data["user_prompt"])
        # Add input placeholders at the end
        user_prompt_markdown += _get_email_content_placeholders()
        result["user_prompt"] = user_prompt_markdown
    
    return result


@lru_cache(maxsize=1)
def _get_email_content_placeholders() -> str:
    """Get email content placeholders (cached for performance)."""
    return "\n\n## Email Content\n\n**Subject:** {{subject}}\n\n**Body:** {{body}}"


def _build_system_prompt_markdown(system_prompt: Dict[str, Any]) -> str:
    """Build system prompt markdown section."""
    if not isinstance(system_prompt, dict):
        raise PromptConversionError("System prompt must be a dictionary")
    
    parts = ["## System Prompt"]
    
    # Define the structure for system prompt sections
    sections = [
        ("role", "### Role"),
        ("objective", "### Objective"),
        ("model_instructions", "### Model Instructions"),
        ("response_instructions", "### Response Instructions")
    ]
    
    for key, header in sections:
        if key in system_prompt:
            parts.append(header)
            content = system_prompt[key]
            
            if key in ["model_instructions", "response_instructions"]:
                # Handle list of instructions
                if isinstance(content, list):
                    for instruction in content:
                        if isinstance(instruction, dict) and "point" in instruction:
                            parts.append(f"• {instruction['point']}")
                else:
                    parts.append(str(content))
            else:
                # Handle simple string content
                parts.append(str(content))
            
            parts.append("")  # Add empty line for spacing
    
    return "\n".join(parts)


def _build_user_prompt_markdown(user_prompt: Dict[str, Any]) -> str:
    """Build user prompt markdown section."""
    if not isinstance(user_prompt, dict):
        raise PromptConversionError("User prompt must be a dictionary")
    
    parts = ["## User Prompt"]
    
    # Build each section
    sections = [
        ("positive_scenarios", _build_positive_scenarios),
        ("analysis_instructions", _build_analysis_instructions),
        ("output_instructions", _build_output_instructions),
        ("examples", _build_examples)
    ]
    
    for key, builder_func in sections:
        if key in user_prompt:
            section_content = builder_func(user_prompt[key])
            if section_content:
                parts.append(section_content)
    
    return "\n".join(parts)


def _build_positive_scenarios(scenarios: List[Dict[str, Any]]) -> str:
    """Build positive scenarios section."""
    if not isinstance(scenarios, list):
        return ""
    
    parts = ["### Positive Scenarios"]
    
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            continue
            
        if "domain" in scenario:
            parts.append(f"#### {scenario['domain']}")
        
        if "categories" in scenario and isinstance(scenario["categories"], list):
            for category in scenario["categories"]:
                if isinstance(category, dict):
                    if "type" in category:
                        parts.append(f"**{category['type']}:**")
                    
                    if "info" in category and isinstance(category["info"], list):
                        for info in category["info"]:
                            if isinstance(info, dict) and "point" in info:
                                parts.append(f"• {info['point']}")
                    parts.append("")
    
    return "\n".join(parts)


def _build_analysis_instructions(analysis: Dict[str, Any]) -> str:
    """Build analysis instructions section."""
    if not isinstance(analysis, dict):
        return ""
    
    parts = ["### Analysis Instructions"]
    
    # Instructions
    if "instructions" in analysis and isinstance(analysis["instructions"], list):
        parts.append("#### Instructions")
        for instruction in analysis["instructions"]:
            if isinstance(instruction, dict) and "point" in instruction:
                parts.append(f"• {instruction['point']}")
        parts.append("")
    
    # Confidence Score Guidelines
    if "confidence_score_assignment" in analysis:
        confidence = analysis["confidence_score_assignment"]
        if isinstance(confidence, dict):
            guidelines = [
                ("positve_classication_score_guidelines", "#### Positive Classification Score Guidelines"),
                ("negative_classication_score_guidelines", "#### Negative Classification Score Guidelines")
            ]
            
            for key, header in guidelines:
                if key in confidence and isinstance(confidence[key], list):
                    parts.append(header)
                    for guideline in confidence[key]:
                        if isinstance(guideline, dict) and "point" in guideline:
                            parts.append(f"• {guideline['point']}")
                    parts.append("")
    
    return "\n".join(parts)


def _build_output_instructions(instructions: List[Dict[str, Any]]) -> str:
    """Build output instructions section."""
    if not isinstance(instructions, list):
        return ""
    
    parts = ["### Output Instructions"]
    
    for instruction in instructions:
        if isinstance(instruction, dict) and "point" in instruction:
            parts.append(f"• {instruction['point']}")
    
    parts.append("")
    return "\n".join(parts)


def _build_examples(examples: List[Dict[str, Any]]) -> str:
    """Build examples section."""
    if not isinstance(examples, list):
        return ""
    
    parts = ["### Examples"]
    
    for i, example in enumerate(examples, 1):
        if not isinstance(example, dict):
            continue
            
        parts.append(f"#### Example {i}")
        
        # Input
        if "prompt_input" in example:
            input_data = example["prompt_input"]
            if isinstance(input_data, dict):
                parts.append("**Input:**")
                if "subject" in input_data:
                    parts.append(f"**Subject:** {input_data['subject']}")
                if "body" in input_data:
                    parts.append("**Body:**")
                    body_lines = _clean_body_text(input_data['body'])
                    parts.append(f"```\n{body_lines}\n```")
        
        # Output
        if "prompt_output" in example:
            output_data = example["prompt_output"]
            if isinstance(output_data, dict):
                parts.append("**Output:**")
                output_fields = [
                    ("classification_label", "**Classification Label:**"),
                    ("confidence_score", "**Confidence Score:**"),
                    ("classification_rationale", "**Classification Rationale:**")
                ]
                
                for key, label in output_fields:
                    if key in output_data:
                        parts.append(f"{label} {output_data[key]}")
        
        parts.append("")
        parts.append("---")
        parts.append("")
    
    return "\n".join(parts)


def _clean_body_text(body: str) -> str:
    """Clean and format email body text."""
    if not isinstance(body, str):
        return str(body)
    
    lines = body.split('\n')
    cleaned_lines = [line.strip() for line in lines if line.strip()]
    return '\n'.join(cleaned_lines)


def convert_file(input_file: str, output_file: Optional[str] = None) -> Dict[str, str]:
    """
    Convert a JSON file to markdown format and optionally save the result.
    
    Args:
        input_file: Path to the input JSON file
        output_file: Optional path to save the converted markdown as JSON
        
    Returns:
        Dictionary with 'system_prompt' and 'user_prompt' markdown strings
        
    Raises:
        PromptConversionError: If conversion fails
    """
    try:
        markdown_dict = json_to_markdown(input_file)
        
        if output_file:
            _save_markdown_to_file(markdown_dict, output_file)
        
        return markdown_dict
    except Exception as e:
        logger.error(f"Failed to convert file {input_file}: {e}")
        raise PromptConversionError(f"File conversion failed: {e}")


def _save_markdown_to_file(markdown_dict: Dict[str, str], output_file: str) -> None:
    """Save markdown dictionary to JSON file."""
    try:
        path = Path(output_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(markdown_dict, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Converted markdown saved to: {output_file}")
    except Exception as e:
        raise PromptConversionError(f"Failed to save output file {output_file}: {e}")


def convert_pydantic_model_to_markdown(prompt_model) -> Dict[str, str]:
    """
    Convert a Pydantic model instance to markdown format.
    
    Args:
        prompt_model: Instance of the Prompt Pydantic model
        
    Returns:
        Dictionary with 'system_prompt' and 'user_prompt' markdown strings
        
    Raises:
        PromptConversionError: If conversion fails
    """
    try:
        if not hasattr(prompt_model, 'model_dump'):
            raise PromptConversionError("Input must be a Pydantic model instance")
        
        # Convert Pydantic model to dict
        model_dict = prompt_model.model_dump()
        return _convert_to_markdown(model_dict)
    except Exception as e:
        logger.error(f"Failed to convert Pydantic model to markdown: {e}")
        raise PromptConversionError(f"Pydantic model conversion failed: {e}")


def validate_prompt_structure(data: Dict[str, Any]) -> bool:
    """
    Validate that the prompt data has the expected structure.
    
    Args:
        data: Dictionary containing prompt data
        
    Returns:
        True if valid, False otherwise
    """
    required_sections = ["system_prompt", "user_prompt"]
    
    if not isinstance(data, dict):
        return False
    
    for section in required_sections:
        if section not in data:
            return False
    
    return True


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python prompt_to_markdown_converter.py <input_file> [output_file]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        markdown_dict = convert_file(input_file, output_file)
        print(f"✅ Successfully converted to markdown format")
        
        if not output_file:
            print("\n" + "="*50)
            print("MARKDOWN OUTPUT:")
            print("="*50)
            print(json.dumps(markdown_dict, indent=2, ensure_ascii=False))
    except PromptConversionError as e:
        print(f"❌ Conversion Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        sys.exit(1) 