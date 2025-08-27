import json
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os

def load_json_data(json_file):
    """Load bounding box data from JSON file"""
    with open(json_file, 'r') as f:
        data = json.load(f)
    return data

def draw_bounding_boxes(image_path, json_data, output_path="china_with_boxes.jpg"):
    """
    Draw bounding boxes on the image based on JSON data
    
    Args:
        image_path (str): Path to the input image
        json_data (dict): JSON data containing bounding box information
        output_path (str): Path to save the output image
    """
    
    # Load the image
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Could not load image from {image_path}")
        return
    
    height, width = image.shape[:2]
    print(f"Image dimensions: {width}x{height}")
    
    # Convert to PIL Image for better text rendering
    pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_image)
    
    # Try to load a font, fall back to default if not available
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 16)  # macOS
        except:
            font = ImageFont.load_default()
    
    # Colors for different field types
    colors = {
        'country': (255, 0, 0),      # Red
        'documentType': (0, 255, 0),  # Green
        'surname': (0, 0, 255),      # Blue
        'documentNumber': (255, 255, 0),  # Yellow
        'issuingOffice': (255, 0, 255),   # Magenta
        'validFrom': (0, 255, 255),       # Cyan
        'forenames': (255, 165, 0),       # Orange
        'validTo': (128, 0, 128)          # Purple
    }
    
    # Extract explainability info
    explainability_info = json_data.get('explainability_info', [])
    
    if not explainability_info:
        print("No explainability_info found in JSON")
        return
    
    # Process each field
    for field_info in explainability_info:
        for field_name, field_data in field_info.items():
            if field_name in colors and 'geometry' in field_data:
                color = colors[field_name]
                value = field_data.get('value', '')
                confidence = field_data.get('confidence', 0)
                
                # Process each geometry entry
                for geometry in field_data['geometry']:
                    if 'boundingBox' in geometry:
                        bbox = geometry['boundingBox']
                        
                        # Convert normalized coordinates to pixel coordinates
                        left = int(bbox['left'] * width)
                        top = int(bbox['top'] * height)
                        right = int((bbox['left'] + bbox['width']) * width)
                        bottom = int((bbox['top'] + bbox['height']) * height)
                        
                        # Draw bounding box
                        draw.rectangle([left, top, right, bottom], outline=color, width=3)
                        
                        # Draw label with field name, value, and confidence
                        label = f"{field_name}: {value} ({confidence:.2f})"
                        
                        # Calculate text position (above the box)
                        text_y = max(0, top - 25)
                        
                        # Draw text background
                        text_bbox = draw.textbbox((left, text_y), label, font=font)
                        draw.rectangle(text_bbox, fill=color)
                        
                        # Draw text
                        draw.text((left, text_y), label, fill=(255, 255, 255), font=font)
                        
                        print(f"Drew box for {field_name}: {value} at ({left}, {top}) to ({right}, {bottom})")
    
    # Convert back to OpenCV format and save
    result_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    cv2.imwrite(output_path, result_image)
    print(f"✅ Image with bounding boxes saved to: {output_path}")
    
    return output_path

def main():
    """Main function to process the image and JSON"""
    
    # File paths
    image_file = "china.jpg"
    json_file = "result.json"
    
    # Check if files exist
    if not os.path.exists(image_file):
        print(f"Error: Image file '{image_file}' not found")
        return
    
    if not os.path.exists(json_file):
        print(f"Error: JSON file '{json_file}' not found")
        return
    
    # Load JSON data
    print("📄 Loading JSON data...")
    json_data = load_json_data(json_file)
    
    # Draw bounding boxes
    print("🎨 Drawing bounding boxes...")
    output_file = draw_bounding_boxes(image_file, json_data)
    
    if output_file:
        print(f"\n🎉 Success! Bounding boxes drawn on the image.")
        print(f"📁 Output file: {output_file}")
        print(f"🔍 Open the image to see the extracted passport fields highlighted!")

if __name__ == "__main__":
    main()
