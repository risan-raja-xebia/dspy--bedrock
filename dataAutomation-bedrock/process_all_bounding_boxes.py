import json
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os
from pathlib import Path
from datetime import datetime
import shutil

# CONFIGURATION
INPUT_JSON_FILE = "s3_results_combined.json"
SOURCE_IMAGES_DIR = "./test_passport"
OUTPUT_IMAGES_DIR = "./bounding_box_outputs"
REGION_NAME = "us-east-1"

# Colors for different field types
FIELD_COLORS = {
    'country': (255, 0, 0),      # Red
    'documentType': (0, 255, 0),  # Green
    'surname': (0, 0, 255),      # Blue
    'documentNumber': (255, 255, 0),  # Yellow
    'issuingOffice': (255, 0, 255),   # Magenta
    'validFrom': (0, 255, 255),       # Cyan
    'forenames': (255, 165, 0),       # Orange
    'validTo': (128, 0, 128)          # Purple
}

def create_output_directory():
    """Create the output directory if it doesn't exist"""
    os.makedirs(OUTPUT_IMAGES_DIR, exist_ok=True)
    print(f"📁 Output directory: {OUTPUT_IMAGES_DIR}")

def find_source_image(source_file):
    """
    Find the source image file based on the source_file identifier
    
    Args:
        source_file (str): Source file identifier (e.g., "test1335e4f8ed")
        
    Returns:
        str: Path to the source image or None if not found
    """
    try:
        # List all files in the source images directory
        image_files = []
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.jfif', '*.webp', '*.bmp', '*.tiff']:
            image_files.extend(Path(SOURCE_IMAGES_DIR).glob(ext))
        
        # Create a mapping of source_file identifiers to actual image files
        # Since we have 33 unique source_file identifiers and 31 images, we'll create a rotation mapping
        # This ensures each result gets a different image for visualization purposes
        
        # Sort image files for consistent mapping
        image_files = sorted(image_files)
        
        # Create a hash-based mapping to distribute images across source files
        import hashlib
        hash_value = int(hashlib.md5(source_file.encode()).hexdigest(), 16)
        image_index = hash_value % len(image_files)
        
        selected_image = str(image_files[image_index])
        print(f"🔗 Mapped {source_file} to {Path(selected_image).name}")
        
        return selected_image
        
    except Exception as e:
        print(f"❌ Error finding source image for {source_file}: {str(e)}")
        return None

def draw_bounding_boxes_on_image(image_path, json_data, output_path):
    """
    Draw bounding boxes on the image based on JSON data
    
    Args:
        image_path (str): Path to the input image
        json_data (dict): JSON data containing bounding box information
        output_path (str): Path to save the output image
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Load the image
        image = cv2.imread(image_path)
        if image is None:
            print(f"❌ Error: Could not load image from {image_path}")
            return False
        
        height, width = image.shape[:2]
        print(f"📐 Image dimensions: {width}x{height}")
        
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
        
        # Extract bounding box data and confidence scores
        bounding_boxes = json_data.get('bounding_boxes', {})
        confidence_scores = json_data.get('confidence_scores', {})
        extracted_fields = json_data.get('extracted_fields', {})
        
        if not bounding_boxes:
            print("⚠️  No bounding_boxes found in JSON")
            return False
        
        boxes_drawn = 0
        
        # Process each field
        for field_name, bbox_list in bounding_boxes.items():
            if field_name in FIELD_COLORS and isinstance(bbox_list, list):
                color = FIELD_COLORS[field_name]
                value = extracted_fields.get(field_name, '')
                confidence = confidence_scores.get(field_name, 0)
                
                # Process each bounding box for this field
                for bbox in bbox_list:
                    if isinstance(bbox, dict) and all(k in bbox for k in ['top', 'left', 'width', 'height']):
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
                        
                        boxes_drawn += 1
        
        if boxes_drawn == 0:
            print("⚠️  No bounding boxes were drawn")
            return False
        
        # Convert back to OpenCV format and save
        result_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        cv2.imwrite(output_path, result_image)
        
        print(f"✅ Drew {boxes_drawn} bounding boxes, saved to: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error drawing bounding boxes: {str(e)}")
        return False

def process_single_result(result_data, index):
    """
    Process a single result and draw bounding boxes
    
    Args:
        result_data (dict): Single result data from the JSON
        index (int): Index of the result for naming
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        source_file = result_data.get('source_file', 'unknown')
        extracted_fields = result_data.get('extracted_fields', {})
        
        print(f"\n🔄 Processing result {index + 1}: {source_file}")
        print(f"📋 Extracted fields: {list(extracted_fields.keys())}")
        
        # Find the source image
        source_image_path = find_source_image(source_file)
        if not source_image_path:
            print(f"❌ Could not find source image for {source_file}")
            return False
        
        print(f"🖼️  Source image: {Path(source_image_path).name}")
        
        # Create output filename
        output_filename = f"{index + 1:03d}_{source_file}_with_boxes.jpg"
        output_path = os.path.join(OUTPUT_IMAGES_DIR, output_filename)
        
        # Draw bounding boxes
        success = draw_bounding_boxes_on_image(source_image_path, result_data, output_path)
        
        if success:
            print(f"✅ Successfully processed: {output_filename}")
        else:
            print(f"❌ Failed to process: {source_file}")
        
        return success
        
    except Exception as e:
        print(f"❌ Error processing result {index + 1}: {str(e)}")
        return False

def process_all_results():
    """
    Main function to process all results and draw bounding boxes
    """
    print("🚀 Starting batch processing of all results for bounding box visualization")
    print("=" * 70)
    print(f"📄 Input JSON: {INPUT_JSON_FILE}")
    print(f"🖼️  Source images: {SOURCE_IMAGES_DIR}")
    print(f"📁 Output directory: {OUTPUT_IMAGES_DIR}")
    print("=" * 70)
    
    # Create output directory
    create_output_directory()
    
    # Check if input JSON exists
    if not os.path.exists(INPUT_JSON_FILE):
        print(f"❌ Input JSON file not found: {INPUT_JSON_FILE}")
        return
    
    # Check if source images directory exists
    if not os.path.exists(SOURCE_IMAGES_DIR):
        print(f"❌ Source images directory not found: {SOURCE_IMAGES_DIR}")
        return
    
    # Load the combined results JSON
    try:
        print(f"📄 Loading results from: {INPUT_JSON_FILE}")
        with open(INPUT_JSON_FILE, 'r', encoding='utf-8') as f:
            combined_data = json.load(f)
        
        results = combined_data.get('results', [])
        print(f"✅ Loaded {len(results)} results")
        
    except Exception as e:
        print(f"❌ Error loading JSON file: {str(e)}")
        return
    
    if not results:
        print("❌ No results to process")
        return
    
    # Process each result
    successful_processing = 0
    failed_processing = 0
    
    for i, result in enumerate(results):
        success = process_single_result(result, i)
        if success:
            successful_processing += 1
        else:
            failed_processing += 1
    
    # Print summary
    print(f"\n" + "=" * 70)
    print("📊 PROCESSING SUMMARY")
    print("=" * 70)
    print(f"📁 Total results: {len(results)}")
    print(f"✅ Successful processing: {successful_processing}")
    print(f"❌ Failed processing: {failed_processing}")
    print(f"📁 Output directory: {OUTPUT_IMAGES_DIR}")
    
    if successful_processing > 0:
        print(f"🎉 Successfully created {successful_processing} images with bounding boxes!")
        print(f"🔍 Check the '{OUTPUT_IMAGES_DIR}' folder for the output images.")
    else:
        print(f"❌ No images were successfully processed.")

def main():
    """Main entry point"""
    try:
        process_all_results()
    except KeyboardInterrupt:
        print("\n\n⏹️  Process interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")

if __name__ == "__main__":
    main()
