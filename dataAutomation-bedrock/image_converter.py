import os
import boto3
from PIL import Image
import glob
from pathlib import Path
import uuid
from datetime import datetime

# CONFIGURATION
LOCAL_SOURCE_DIR = "./test_passport"
S3_BUCKET = "test-passport-data"
S3_PREFIX = "test_passport/"
REGION_NAME = "us-east-1"

# Supported image formats for conversion
SUPPORTED_FORMATS = ['.png', '.jpeg', '.bmp', '.tiff', '.tif', '.webp', '.gif', '.ico', '.jpg', '.jfif']

# Initialize AWS S3 client
s3_client = boto3.client('s3', region_name=REGION_NAME)

def get_image_files(directory):
    """
    Get all image files from the specified directory
    
    Args:
        directory (str): Path to the directory containing images
    
    Returns:
        list: List of image file paths
    """
    image_files = []
    
    # Check if directory exists
    if not os.path.exists(directory):
        print(f" Directory does not exist: {directory}")
        return image_files
    
    # Get all files in directory
    for file_path in glob.glob(os.path.join(directory, "*")):
        if os.path.isfile(file_path):
            file_ext = Path(file_path).suffix.lower()
            if file_ext in SUPPORTED_FORMATS:
                image_files.append(file_path)
    
    return sorted(image_files)

def convert_image_to_jpg(image_path, output_dir=None):
    """
    Convert an image to JPG format
    
    Args:
        image_path (str): Path to the input image
        output_dir (str): Directory to save the converted JPG (optional)
    
    Returns:
        str: Path to the converted JPG file
    """
    try:
        # Open the image
        with Image.open(image_path) as img:
            # Convert to RGB if necessary (JPG doesn't support transparency)
            if img.mode in ('RGBA', 'LA', 'P'):
                # Create white background for transparent images
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Generate output filename
            base_name = Path(image_path).stem
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, f"{base_name}.jpg")
            else:
                output_path = f"{base_name}.jpg"
            
            # Save as JPG with high quality
            img.save(output_path, 'JPEG', quality=95, optimize=True)
            
            print(f"✅ Converted: {Path(image_path).name} → {Path(output_path).name}")
            return output_path
            
    except Exception as e:
        print(f"❌ Error converting {Path(image_path).name}: {str(e)}")
        return None

def upload_to_s3(file_path, bucket, key):
    """
    Upload a file to S3
    
    Args:
        file_path (str): Local path to the file
        bucket (str): S3 bucket name
        key (str): S3 key (path in bucket)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        s3_client.upload_file(file_path, bucket, key)
        print(f"✅ Uploaded: {Path(file_path).name} → s3://{bucket}/{key}")
        return True
    except Exception as e:
        print(f"❌ Error uploading {Path(file_path).name}: {str(e)}")
        return False

def process_images():
    """
    Main function to process all images: convert to JPG and upload to S3
    """
    print("🚀 Starting image conversion and S3 upload process")
    print("=" * 60)
    print(f"📁 Source directory: {LOCAL_SOURCE_DIR}")
    print(f"☁️  S3 destination: s3://{S3_BUCKET}/{S3_PREFIX}")
    print(f"🌍 Region: {REGION_NAME}")
    print("=" * 60)
    
    # Get all image files
    image_files = get_image_files(LOCAL_SOURCE_DIR)
    
    if not image_files:
        print("❌ No supported image files found in the directory")
        return
    
    print(f"📋 Found {len(image_files)} image files to process:")
    for img_file in image_files:
        print(f"   - {Path(img_file).name}")
    
    print("\n" + "=" * 60)
    
    # Create temporary directory for converted images
    temp_dir = "temp_converted_images"
    os.makedirs(temp_dir, exist_ok=True)
    
    successful_conversions = 0
    successful_uploads = 0
    
    # Process each image
    for i, image_path in enumerate(image_files, 1):
        print(f"\n🔄 Processing {i}/{len(image_files)}: {Path(image_path).name}")
        
        file_ext = Path(image_path).suffix.lower()
        
        # If it's already JPG, use it directly
        if file_ext in ['.jpg', '.jpeg']:
            print(f"✅ Already JPG: {Path(image_path).name}")
            processed_file = image_path
            needs_cleanup = False
        else:
            # Convert to JPG (including JFIF, PNG, WebP, etc.)
            processed_file = convert_image_to_jpg(image_path, temp_dir)
            needs_cleanup = True
        
        if processed_file:
            successful_conversions += 1
            
            # Generate unique S3 key
            base_name = Path(image_path).stem
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            s3_key = f"{S3_PREFIX}{base_name}_{timestamp}_{unique_id}.jpg"
            
            # Upload to S3
            if upload_to_s3(processed_file, S3_BUCKET, s3_key):
                successful_uploads += 1
            
            # Clean up temporary JPG file if it was converted
            if needs_cleanup:
                try:
                    os.remove(processed_file)
                    print(f"🧹 Cleaned up temporary file: {Path(processed_file).name}")
                except:
                    pass
        else:
            print(f"❌ Failed to process: {Path(image_path).name}")
    
    # Clean up temporary directory
    try:
        os.rmdir(temp_dir)
        print(f"🧹 Cleaned up temporary directory: {temp_dir}")
    except:
        pass
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 PROCESSING SUMMARY")
    print("=" * 60)
    print(f"📁 Total files found: {len(image_files)}")
    print(f"✅ Successfully processed: {successful_conversions}")
    print(f"☁️  Successful S3 uploads: {successful_uploads}")
    print(f"❌ Failed processing: {len(image_files) - successful_conversions}")
    print(f"❌ Failed uploads: {successful_conversions - successful_uploads}")
    
    if successful_uploads > 0:
        print(f"\n🎉 Successfully processed and uploaded {successful_uploads} files to S3!")
        print(f"📍 S3 location: s3://{S3_BUCKET}/{S3_PREFIX}")
        print(f"📋 Files include: JPG, PNG, WebP, JFIF, and other image formats")
    else:
        print(f"\n❌ No files were successfully processed and uploaded.")

def main():
    """Main entry point"""
    try:
        process_images()
    except KeyboardInterrupt:
        print("\n\n⏹️  Process interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")

if __name__ == "__main__":
    main()
