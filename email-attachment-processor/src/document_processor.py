"""
Core Document Processor Class
Implements the robust workflow from the flowchart:
Bytes -> Format Check -> Conversion -> Document -> S3 Upload -> DocumentObject
"""

import os
import uuid
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from config.config import Config

class DocumentProcessor:
    """
    Robust Document Processor
    
    Flow:
    1. Bytes -> Check format -> Convert if needed -> Document
    2. Document -> Upload to S3 -> Convert to DocumentObject
    3. Store results with UUID-based paths
    """
    
    def __init__(self, config: Config = None):
        """Initialize the document processor"""
        self.config = config or Config()
        self.logger = self._setup_logging()
        self.s3_client = self._setup_s3_client()
        self.bedrock_client = self._setup_bedrock_client()
        
        # Processing statistics
        self.stats = {
            'processed': 0,
            'converted': 0,
            'uploaded': 0,
            'errors': 0,
            'start_time': datetime.now()
        }
    
    def _setup_logging(self) -> logging.Logger:
        
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        
        # Only console handler - no file logging
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        
        # Add only console handler
        logger.addHandler(console_handler)
        
        return logger
    
    def _setup_s3_client(self) -> boto3.client:
        """Setup S3 client"""
        try:
            return boto3.client('s3', region_name=self.config.AWS_REGION)
        except NoCredentialsError:
            self.logger.error("AWS credentials not found")
            raise
        except Exception as e:
            self.logger.error(f"Failed to setup S3 client: {e}")
            raise
    
    def _setup_bedrock_client(self) -> boto3.client:
        """Setup Bedrock client"""
        try:
            return boto3.client('bedrock-runtime', region_name=self.config.AWS_REGION)
        except Exception as e:
            self.logger.error(f"Failed to setup Bedrock client: {e}")
            raise
    
    def process_bytes(self, bytes_data: bytes, filename: str) -> Dict[str, Any]:
        """
        Main processing method implementing the flowchart workflow
        
        Args:
            bytes_data: Raw bytes of the document
            filename: Original filename
            
        Returns:
            DocumentObject with processing results
        """
        try:
            self.logger.info(f"Starting processing for file: {filename}")
            
            # Step 1: Check if bytes is in supported formats and convert if needed
            original_format = Path(filename).suffix.lower()
            converted_format = None
            
            # Always convert JFIF images to JPG format
            if original_format == '.jfif':
                self.logger.info(f"Converting JFIF format to JPG: {filename}")
                bytes_data = self._convert_to_supported_format(bytes_data, filename)
                converted_format = '.jpg'
                self.stats['converted'] += 1
                self.logger.info(f"JFIF conversion completed: {original_format} -> {converted_format}")
            elif not self._is_supported_format(filename):
                self.logger.info(f"Converting unsupported format: {filename}")
                bytes_data = self._convert_to_supported_format(bytes_data, filename)
                converted_format = '.jpg'  # All conversions result in JPEG
                self.stats['converted'] += 1
                self.logger.info(f"Format conversion completed: {original_format} -> {converted_format}")
            else:
                # Even for supported formats, ensure they're optimized
                self.logger.info(f"Optimizing supported format: {filename}")
                bytes_data = self._convert_to_supported_format(bytes_data, filename)
                if original_format in {'.jpg', '.jpeg'}:
                    converted_format = '.jpg'  # Mark as optimized
                    self.stats['converted'] += 1
            
            # Step 2: Create Document object with conversion info
            document = self._create_document(bytes_data, filename, converted_format)
            
            # Step 3: Validate S3 and Bedrock compatibility
            if not self._is_s3_bedrock_compatible(bytes_data, document['filename']):
                self.logger.error(f"Document {filename} is not compatible with S3/Bedrock processing")
                raise ValueError(f"Document {filename} failed S3/Bedrock compatibility check")
            
            self.logger.info(f"Document {filename} validated for S3/Bedrock processing")
            
            # Step 4: Upload to S3 if not already done
            s3_key = self._upload_to_s3(document, document['filename'])
            
            # Step 5: Convert to DocumentObject
            document_object = self._convert_to_document_object(document, s3_key)
            
            # Step 6: Store results with UUID-based path
            result_uuid = str(uuid.uuid4())
            self._store_results(document_object, result_uuid, filename)
            
            # Expose result UUID on the returned object for downstream cleanup
            document_object['result_uuid'] = result_uuid
            
            self.stats['processed'] += 1
            self.logger.info(f"Successfully processed: {filename}")
            
            return document_object
            
        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"Error processing {filename}: {e}")
            raise
    
    def _is_supported_format(self, filename: str) -> bool:
        """Check if the file format is supported for S3 and Bedrock processing"""
        file_ext = Path(filename).suffix.lower()
        
        # S3 and Bedrock fully supported formats (including PDFs)
        fully_supported = {'.pdf', '.jpg', '.jpeg'}
        
        # Formats that can be converted to supported formats
        convertible_formats = {'.png', '.webp', '.bmp', '.tiff', '.jfif'}
        
        return file_ext in fully_supported or file_ext in convertible_formats
    
    def _is_s3_bedrock_compatible(self, bytes_data: bytes, filename: str) -> bool:
        """
        Validate if document is compatible with S3 and Bedrock processing
        
        Args:
            bytes_data: Document bytes
            filename: Original filename
            
        Returns:
            True if compatible, False otherwise
        """
        try:
            file_ext = Path(filename).suffix.lower()
            
            # For PDFs, skip image validation - they're compatible by default
            if file_ext == '.pdf':
                self.logger.info(f"PDF format detected for {filename} - skipping image validation")
                return True
            
            # For images, validate using PIL
            from PIL import Image
            import io
            
            # Try to open as image to validate
            image = Image.open(io.BytesIO(bytes_data))
            image.verify()  # Verify the image is valid
            
            self.logger.info(f"Successfully validated {filename} for S3/Bedrock compatibility")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to validate {filename} for S3/Bedrock compatibility: {e}")
            return False
    
    def _convert_to_supported_format(self, bytes_data: bytes, filename: str) -> bytes:
        """
        Convert document to S3 and Bedrock-supported format
        
        Args:
            bytes_data: Original bytes
            filename: Original filename
            
        Returns:
            Converted bytes in supported format (no conversion for PDFs)
        """
        try:
            # Get file extension
            file_ext = Path(filename).suffix.lower()
            
            # For PDFs, no conversion needed - return as-is
            if file_ext == '.pdf':
                self.logger.info(f"PDF format detected for {filename} - no conversion needed")
                return bytes_data
            
            # For images, perform conversion to JPEG if needed
            from PIL import Image
            import io
            
            # Define formats that need conversion to JPEG
            formats_to_convert = {'.jfif', '.webp', '.bmp', '.tiff', '.png'}
            
            # Check if conversion is needed
            if file_ext in formats_to_convert:
                self.logger.info(f"Converting {filename} from {file_ext} to JPEG format")
                
                # Open image
                image = Image.open(io.BytesIO(bytes_data))
                
                # Convert to RGB if needed (for PNG with transparency, RGBA, etc.)
                if image.mode in ('RGBA', 'LA', 'P', 'CMYK', 'YCbCr'):
                    self.logger.info(f"Converting {filename} from {image.mode} mode to RGB")
                    image = image.convert('RGB')
                
                # Optimize image for processing
                # Ensure reasonable dimensions for Bedrock processing
                max_dimension = 4000  # Maximum dimension for optimal processing
                if max(image.size) > max_dimension:
                    ratio = max_dimension / max(image.size)
                    new_size = tuple(int(dim * ratio) for dim in image.size)
                    image = image.resize(new_size, Image.Resampling.LANCZOS)
                    self.logger.info(f"Resized {filename} to {new_size} for optimal processing")
                
                # Save as high-quality JPEG
                output_buffer = io.BytesIO()
                image.save(output_buffer, format='JPEG', quality=95, optimize=True)
                converted_bytes = output_buffer.getvalue()
                
                self.logger.info(f"Successfully converted {filename} to JPEG ({len(converted_bytes)} bytes)")
                return converted_bytes
            
            # For already supported formats (JPG, JPEG), ensure they're optimized
            elif file_ext in {'.jpg', '.jpeg'}:
                self.logger.info(f"Optimizing {filename} (already JPEG format)")
                
                # Open and re-save to ensure consistency and optimization
                image = Image.open(io.BytesIO(bytes_data))
                
                # Convert to RGB if needed
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                
                # Optimize
                output_buffer = io.BytesIO()
                image.save(output_buffer, format='JPEG', quality=95, optimize=True)
                optimized_bytes = output_buffer.getvalue()
                
                self.logger.info(f"Optimized {filename} ({len(optimized_bytes)} bytes)")
                return optimized_bytes
            
            # For other formats, attempt conversion to JPEG
            else:
                self.logger.info(f"Attempting to convert {filename} from {file_ext} to JPEG")
                try:
                    image = Image.open(io.BytesIO(bytes_data))
                    
                    # Convert to RGB
                    if image.mode != 'RGB':
                        image = image.convert('RGB')
                    
                    # Save as JPEG
                    output_buffer = io.BytesIO()
                    image.save(output_buffer, format='JPEG', quality=95, optimize=True)
                    converted_bytes = output_buffer.getvalue()
                    
                    self.logger.info(f"Successfully converted {filename} to JPEG")
                    return converted_bytes
                    
                except Exception as e:
                    self.logger.warning(f"Failed to convert {filename} from {file_ext}: {e}")
                    return bytes_data
            
        except Exception as e:
            self.logger.error(f"Format conversion failed for {filename}: {e}")
            # Return original data if conversion fails
            return bytes_data
    
    def _create_document(self, bytes_data: bytes, filename: str, converted_format: str = None) -> Dict[str, Any]:
        """
        Create a Document object from bytes
        
        Args:
            bytes_data: Document bytes
            filename: Original filename
            converted_format: New format if conversion occurred
            
        Returns:
            Document object
        """
        # Determine the final format
        if converted_format:
            final_format = converted_format
            final_filename = str(Path(filename).with_suffix(converted_format))
        else:
            final_format = Path(filename).suffix.lower()
            final_filename = filename
        
        document = {
            'id': str(uuid.uuid4()),
            'filename': final_filename,
            'original_filename': filename,
            'size_bytes': len(bytes_data),
            'format': final_format,
            'created_at': datetime.now().isoformat(),
            'bytes_data': bytes_data,
            'metadata': {
                'original_filename': filename,
                'converted_format': converted_format,
                'processing_timestamp': datetime.now().isoformat(),
                'conversion_applied': converted_format is not None
            }
        }
        
        self.logger.debug(f"Created document: {document['id']} (format: {final_format})")
        return document
    
    def _upload_to_s3(self, document: Dict[str, Any], filename: str) -> str:
        """
        Upload document to S3 if not already done
        
        Args:
            document: Document object
            filename: Original filename
            
        Returns:
            S3 key where document was uploaded
        """
        try:
            # Generate S3 key using the final filename (converted if applicable)
            s3_key = self.config.get_s3_key_for_image(document['filename'])
            
            # Check if already exists
            try:
                self.s3_client.head_object(Bucket=self.config.AWS_S3_BUCKET, Key=s3_key)
                self.logger.info(f"Document already exists in S3: {s3_key}")
                return s3_key
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    # Object doesn't exist, proceed with upload
                    pass
                else:
                    raise
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.config.AWS_S3_BUCKET,
                Key=s3_key,
                Body=document['bytes_data'],
                ContentType=self._get_content_type(filename),
                Metadata={
                    'original_filename': filename,
                    'document_id': document['id'],
                    'upload_timestamp': datetime.now().isoformat()
                }
            )
            
            self.stats['uploaded'] += 1
            self.logger.info(f"Uploaded to S3: {s3_key}")
            return s3_key
            
        except Exception as e:
            self.logger.error(f"Failed to upload to S3: {e}")
            raise
    
    def _get_content_type(self, filename: str) -> str:
        """Get appropriate content type for file"""
        file_ext = Path(filename).suffix.lower()
        
        content_types = {
            '.pdf': 'application/pdf',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.jfif': 'image/jpeg',
            '.webp': 'image/webp',
            '.bmp': 'image/bmp',
            '.tiff': 'image/tiff'
        }
        
        return content_types.get(file_ext, 'application/octet-stream')
    
    def _convert_to_document_object(self, document: Dict[str, Any], s3_key: str) -> Dict[str, Any]:
        """
        Convert document to DocumentObject
        
        Args:
            document: Document object
            s3_key: S3 key where document is stored
            
        Returns:
            DocumentObject
        """
        document_object = {
            'document_id': document['id'],
            'filename': document['filename'],
            's3_key': s3_key,
            's3_bucket': self.config.AWS_S3_BUCKET,
            'size_bytes': document['size_bytes'],
            'format': document['format'],
            'created_at': document['created_at'],
            'status': 'uploaded',
            'processing_metadata': {
                'processor_version': '1.0.0',
                'processing_timestamp': datetime.now().isoformat(),
                'config_used': {
                    'bucket': self.config.AWS_S3_BUCKET,
                    'region': self.config.AWS_REGION
                }
            }
        }
        
        self.logger.debug(f"Created DocumentObject: {document_object['document_id']}")
        return document_object
    
    def _store_results(self, document_object: Dict[str, Any], result_uuid: str, filename: str):
        """
        Store results with UUID-based path
        
        Args:
            document_object: DocumentObject to store
            result_uuid: UUID for result path
            filename: Original filename
        """
        try:
            # Create result metadata
            result_metadata = {
                'result_id': result_uuid,
                'document_object': document_object,
                'stored_at': datetime.now().isoformat(),
                'workflow_version': '1.0.0'
            }
            
            # Store in S3 with UUID-based path
            result_key = self.config.get_s3_key_for_result(result_uuid, 'result.json')
            
            import json
            self.s3_client.put_object(
                Bucket=self.config.AWS_S3_BUCKET,
                Key=result_key,
                Body=json.dumps(result_metadata, indent=2, default=str),
                ContentType='application/json',
                Metadata={
                    'result_uuid': result_uuid,
                    'original_filename': filename,
                    'stored_timestamp': datetime.now().isoformat()
                }
            )
            
            self.logger.info(f"Stored results with UUID path: {result_key}")
            
        except Exception as e:
            self.logger.error(f"Failed to store results: {e}")
            raise
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get current processing statistics"""
        stats = self.stats.copy()
        stats['end_time'] = datetime.now()
        stats['duration'] = (stats['end_time'] - stats['start_time']).total_seconds()
        return stats
    
    def process_batch(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process multiple files in batch
        
        Args:
            files: List of file dictionaries with 'bytes' and 'filename' keys
            
        Returns:
            List of DocumentObjects
        """
        results = []
        
        for file_info in files:
            try:
                result = self.process_bytes(file_info['bytes'], file_info['filename'])
                results.append(result)
            except Exception as e:
                self.logger.error(f"Failed to process {file_info['filename']}: {e}")
                continue
        
        return results
