import boto3
import json
import os
from datetime import datetime
from pathlib import Path

# CONFIGURATION
S3_BUCKET = "test-passport-data"
S3_RESULTS_PREFIX = "results/"
S3_IMAGES_PREFIX = "test_passport/"
REGION_NAME = "us-east-1"
OUTPUT_JSON_FILE = "s3_results_combined.json"
OUTPUT_IMAGES_INFO_FILE = "s3_images_info.json"

# Initialize AWS S3 client
s3_client = boto3.client('s3', region_name=REGION_NAME)

def list_s3_results():
    """
    List all files in the S3 results folder
    
    Returns:
        list: List of S3 objects in the results folder
    """
    try:
        print(f"🔍 Listing files in s3://{S3_BUCKET}/{S3_RESULTS_PREFIX}")
        
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=S3_RESULTS_PREFIX
        )
        
        if 'Contents' in response:
            files = response['Contents']
            print(f"✅ Found {len(files)} files in results folder")
            return files
        else:
            print("❌ No files found in results folder")
            return []
            
    except Exception as e:
        print(f"❌ Error listing S3 objects: {str(e)}")
        return []

def download_and_parse_json(s3_key):
    """
    Download and parse a JSON file from S3
    
    Args:
        s3_key (str): S3 key of the JSON file
    
    Returns:
        dict: Parsed JSON content or None if failed
    """
    try:
        print(f"📥 Downloading: {s3_key}")
        
        # Download the file
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        json_content = response['Body'].read().decode('utf-8')
        
        # Parse JSON
        parsed_data = json.loads(json_content)
        
        print(f"✅ Successfully parsed: {s3_key}")
        return parsed_data
        
    except Exception as e:
        print(f"❌ Error processing {s3_key}: {str(e)}")
        return None

def extract_source_filename(s3_key):
    """
    Extract the source file name from the S3 key
    
    Args:
        s3_key (str): S3 key path
        
    Returns:
        str: Source file name or 'unknown' if cannot be determined
    """
    try:
        # Parse the S3 key to extract source file information
        # Example key: results/test1335e4f8ed//d114bef3-4a2e-4b97-9fa6-93adb3b1b278/0/custom_output/0/result.json
        # We want to extract the test name (e.g., "test1335e4f8ed")
        
        parts = s3_key.split('/')
        if len(parts) >= 2 and parts[1].startswith('test'):
            # Extract the test name (e.g., "test1335e4f8ed")
            return parts[1]
        elif len(parts) >= 3 and parts[2].startswith('test'):
            # Alternative pattern
            return parts[2]
        else:
            # If we can't determine, use a portion of the path
            return f"source_{Path(s3_key).parent.name}"
    except Exception as e:
        print(f"⚠️  Warning: Could not extract source filename from {s3_key}: {str(e)}")
        return "unknown_source"

def list_s3_images():
    """
    List all images in the S3 test_passport folder
    
    Returns:
        list: List of S3 objects in the test_passport folder
    """
    try:
        print(f"🔍 Listing images in s3://{S3_BUCKET}/{S3_IMAGES_PREFIX}")
        
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=S3_IMAGES_PREFIX
        )
        
        if 'Contents' in response:
            files = response['Contents']
            print(f"✅ Found {len(files)} images in test_passport folder")
            return files
        else:
            print("❌ No images found in test_passport folder")
            return []
            
    except Exception as e:
        print(f"❌ Error listing S3 images: {str(e)}")
        return []

def extract_image_info(s3_object):
    """
    Extract information about an image from S3 object metadata
    
    Args:
        s3_object (dict): S3 object information
        
    Returns:
        dict: Image information including metadata
    """
    try:
        s3_key = s3_object['Key']
        file_name = Path(s3_key).name
        file_extension = Path(s3_key).suffix.lower()
        
        image_info = {
            's3_key': s3_key,
            'file_name': file_name,
            'file_extension': file_extension,
            'file_size_bytes': s3_object.get('Size', 0),
            'file_size_mb': round(s3_object.get('Size', 0) / (1024 * 1024), 2),
            'last_modified': s3_object.get('LastModified', '').isoformat() if s3_object.get('LastModified') else None,
            's3_last_modified': s3_object.get('LastModified', '').isoformat() if s3_object.get('LastModified') else None,
            'etag': s3_object.get('ETag', '').strip('"'),
            'storage_class': s3_object.get('StorageClass', 'STANDARD')
        }
        
        # Add file type classification
        if file_extension in ['.jpg', '.jpeg']:
            image_info['file_type'] = 'JPEG'
        elif file_extension == '.png':
            image_info['file_type'] = 'PNG'
        elif file_extension == '.jfif':
            image_info['file_type'] = 'JFIF'
        elif file_extension == '.webp':
            image_info['file_type'] = 'WEBP'
        elif file_extension in ['.bmp', '.tiff', '.tif']:
            image_info['file_type'] = file_extension.upper().strip('.')
        else:
            image_info['file_type'] = 'UNKNOWN'
        
        return image_info
        
    except Exception as e:
        print(f"❌ Error extracting image info: {str(e)}")
        return None

def extract_passport_data(json_data, s3_key):
    """
    Extract relevant passport data from the JSON result
    
    Args:
        json_data (dict): Raw JSON data from S3
        s3_key (str): S3 key to extract source file information
    
    Returns:
        dict: Cleaned passport data
    """
    try:
        # Extract source file name from S3 key
        source_file = extract_source_filename(s3_key)
        
        # Extract key information
        passport_data = {
            'extraction_timestamp': datetime.now().isoformat(),
            'source_file': source_file,
            'blueprint_info': {},
            'document_info': {},
            'extracted_fields': {},
            'confidence_scores': {},
            'bounding_boxes': {}
        }
        
        # Extract blueprint information
        if 'matched_blueprint' in json_data:
            passport_data['blueprint_info'] = {
                'arn': json_data['matched_blueprint'].get('arn'),
                'name': json_data['matched_blueprint'].get('name'),
                'version': json_data['matched_blueprint'].get('version'),
                'confidence': json_data['matched_blueprint'].get('confidence')
            }
        
        # Extract document information
        if 'document_class' in json_data:
            passport_data['document_info'] = {
                'type': json_data['document_class'].get('type')
            }
        
        # Extract inference results
        if 'inference_result' in json_data:
            passport_data['extracted_fields'] = json_data['inference_result']
        
        # Extract explainability info with confidence scores and bounding boxes
        if 'explainability_info' in json_data:
            for field_info in json_data['explainability_info']:
                for field_name, field_data in field_info.items():
                    if 'confidence' in field_data:
                        passport_data['confidence_scores'][field_name] = field_data['confidence']
                    
                    if 'geometry' in field_data and field_data['geometry']:
                        # Store bounding box information
                        passport_data['bounding_boxes'][field_name] = []
                        for geometry in field_data['geometry']:
                            if 'boundingBox' in geometry:
                                bbox = geometry['boundingBox']
                                passport_data['bounding_boxes'][field_name].append({
                                    'top': bbox.get('top'),
                                    'left': bbox.get('left'),
                                    'width': bbox.get('width'),
                                    'height': bbox.get('height')
                                })
        
        return passport_data
        
    except Exception as e:
        print(f"❌ Error extracting passport data: {str(e)}")
        return None

def process_images():
    """
    Process all images in the S3 test_passport folder and extract metadata
    """
    try:
        print("\n🖼️  Processing S3 images...")
        
        # List all images
        image_files = list_s3_images()
        if not image_files:
            print("❌ No images found. Skipping image processing.")
            return []
        
        # Process each image
        successful_image_info = 0
        all_image_info = []
        
        for s3_object in image_files:
            s3_key = s3_object['Key']
            
            # Skip non-image files
            if not any(s3_key.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.jfif', '.webp', '.bmp', '.tiff', '.tif']):
                continue
            
            # Extract image information
            image_info = extract_image_info(s3_object)
            if image_info:
                successful_image_info += 1
                all_image_info.append(image_info)
        
        print(f"✅ Successfully processed {successful_image_info} images")
        return all_image_info
        
    except Exception as e:
        print(f"❌ Error processing images: {str(e)}")
        return []

def process_all_results():
    """
    Main function to process all results from S3 and combine them
    """
    print("🚀 Starting S3 results and images retrieval and processing")
    print("=" * 60)
    print(f"☁️  S3 bucket: {S3_BUCKET}")
    print(f"📁 Results folder: {S3_RESULTS_PREFIX}")
    print(f"🖼️  Images folder: {S3_IMAGES_PREFIX}")
    print(f"🌍 Region: {REGION_NAME}")
    print("=" * 60)
    
    # List all files in results folder
    s3_files = list_s3_results()
    
    if not s3_files:
        print("❌ No files to process")
        return
    
    # Process each file
    all_results = []
    successful_downloads = 0
    successful_parses = 0
    
    for i, s3_obj in enumerate(s3_files, 1):
        s3_key = s3_obj['Key']
        
        # Skip if it's a directory marker
        if s3_key.endswith('/'):
            continue
            
        print(f"\n🔄 Processing {i}/{len(s3_files)}: {Path(s3_key).name}")
        
        # Download and parse JSON
        json_data = download_and_parse_json(s3_key)
        
        if json_data:
            successful_downloads += 1
            
            # Extract passport data
            passport_data = extract_passport_data(json_data, s3_key)
            
            if passport_data:
                successful_parses += 1
                
                # Add S3 metadata
                passport_data['s3_metadata'] = {
                    's3_key': s3_key,
                    's3_size': s3_obj.get('Size'),
                    's3_last_modified': s3_obj.get('LastModified').isoformat() if s3_obj.get('LastModified') else None
                }
                
                all_results.append(passport_data)
                
                print(f"✅ Successfully processed: {Path(s3_key).name}")
            else:
                print(f"❌ Failed to extract passport data from: {Path(s3_key).name}")
        else:
            print(f"❌ Failed to download/parse: {Path(s3_key).name}")
    
    # Process images
    all_image_info = process_images()
    
    # Save combined results to JSON file
    if all_results:
        try:
            combined_data = {
                'summary': {
                    'total_files_found': len(s3_files),
                    'successful_downloads': successful_downloads,
                    'successful_parses': successful_parses,
                    'processing_timestamp': datetime.now().isoformat()
                },
                'results': all_results
            }
            
            with open(OUTPUT_JSON_FILE, 'w', encoding='utf-8') as f:
                json.dump(combined_data, f, indent=2, ensure_ascii=False, default=str)
            
            print(f"✅ Successfully saved combined results to: {OUTPUT_JSON_FILE}")
            
        except Exception as e:
            print(f"❌ Error saving combined results: {str(e)}")
    else:
        print(f"\n❌ No results were successfully processed")
    
    # Save images info to JSON file
    if all_image_info:
        try:
            images_data = {
                'summary': {
                    'total_images_found': len(all_image_info),
                    'successful_image_info': len(all_image_info),
                    'processing_timestamp': datetime.now().isoformat()
                },
                'images': all_image_info
            }
            
            with open(OUTPUT_IMAGES_INFO_FILE, 'w', encoding='utf-8') as f:
                json.dump(images_data, f, indent=2, ensure_ascii=False, default=str)
            
            print(f"✅ Successfully saved images info to: {OUTPUT_IMAGES_INFO_FILE}")
            
        except Exception as e:
            print(f"❌ Error saving images info: {str(e)}")
    
    # Print final summary
    print(f"\n" + "=" * 60)
    print("📊 PROCESSING SUMMARY")
    print("=" * 60)
    print(f"📁 Total S3 files found: {len(s3_files)}")
    print(f"✅ Successful downloads: {successful_downloads}")
    print(f"✅ Successful parses: {successful_parses}")
    print(f"🖼️  Total images processed: {len(all_image_info)}")
    print(f"📄 Results saved to: {OUTPUT_JSON_FILE}")
    print(f"🖼️  Images info saved to: {OUTPUT_IMAGES_INFO_FILE}")
    print(f"🎉 Successfully processed {len(all_results)} passport extractions!")

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
