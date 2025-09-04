"""
Bounding Box Visualizer
Handles drawing bounding boxes on passport images based on Bedrock extraction results
"""

import cv2
import numpy as np
import json
import logging
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path
import boto3
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO

from config.config import Config


class BoundingBoxVisualizer:
    """
    Visualizes extracted passport data by drawing bounding boxes on images
    """
    
    def __init__(self, config: Config = None):
        """Initialize the visualizer"""
        self.config = config or Config()
        self.logger = logging.getLogger(__name__)
        self.s3_client = boto3.client('s3', region_name=self.config.AWS_REGION)
        
        # Color scheme for different field types - High contrast, readable colors
        self.field_colors = {
            # Passport fields
            'country': (220, 20, 60),      # Crimson Red - High contrast
            'documentType': (34, 139, 34),  # Forest Green - Dark green
            'surname': (25, 25, 112),      # Midnight Blue - Dark blue
            'documentNumber': (255, 140, 0), # Dark Orange - High contrast
            'issuingOffice': (138, 43, 226), # Blue Violet - Purple
            'validFrom': (0, 100, 100),    # Dark Cyan - Dark teal
            'forenames': (75, 0, 130),     # Indigo - Dark purple
            'validTo': (178, 34, 34),      # Fire Brick - Dark red
            
            # Medical certificate fields
            'patientName': (220, 20, 60),      # Crimson Red
            'dateOfBirth': (34, 139, 34),      # Forest Green
            'medicalCondition': (25, 25, 112), # Midnight Blue
            'diagnosis': (255, 140, 0),        # Dark Orange
            'treatmentPlan': (138, 43, 226),    # Blue Violet
            'doctorName': (0, 100, 100),        # Dark Cyan
            'hospitalName': (75, 0, 130),      # Indigo
            'issueDate': (178, 34, 34),        # Fire Brick
            'validUntil': (128, 0, 128),       # Purple
            'certificateNumber': (0, 128, 128), # Teal
            'patientId': (255, 69, 0),         # Orange Red
            'department': (0, 100, 0)          # Dark Green
        }
        
        # Field display names
        self.field_display_names = {
            # Passport fields
            'country': 'Country',
            'documentType': 'Document Type',
            'surname': 'Surname',
            'documentNumber': 'Document Number',
            'issuingOffice': 'Issuing Office',
            'validFrom': 'Valid From',
            'forenames': 'Forenames',
            'validTo': 'Valid To',
            
            # Medical certificate fields
            'patientName': 'Patient Name',
            'dateOfBirth': 'Date of Birth',
            'medicalCondition': 'Medical Condition',
            'diagnosis': 'Diagnosis',
            'treatmentPlan': 'Treatment Plan',
            'doctorName': 'Doctor Name',
            'hospitalName': 'Hospital Name',
            'issueDate': 'Issue Date',
            'validUntil': 'Valid Until',
            'certificateNumber': 'Certificate Number',
            'patientId': 'Patient ID',
            'department': 'Department'
        }
    
    def download_passport_image(self, s3_key: str, local_path: Path) -> bool:
        """
        Download passport image from S3
        
        Args:
            s3_key: S3 key of the passport image
            local_path: Local path to save the image
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Downloading passport image: {s3_key}")
            
            # Create directory if it doesn't exist
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Download from S3
            self.s3_client.download_file(
                self.config.AWS_S3_BUCKET,
                s3_key,
                str(local_path)
            )
            
            self.logger.info(f"Successfully downloaded: {local_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to download {s3_key}: {e}")
            return False
    
    def parse_bedrock_geometry(self, explainability_info: List[Dict]) -> Dict[str, Dict]:
        """
        Parse Bedrock geometry data into usable format
        
        Args:
            explainability_info: Geometry data from Bedrock
            
        Returns:
            Parsed geometry data for each field
        """
        parsed_geometry = {}
        
        for field_info in explainability_info:
            for field_name, field_data in field_info.items():
                if field_name in self.field_colors and field_data.get('success'):
                    # Extract bounding box coordinates
                    geometry = field_data.get('geometry', [])
                    if geometry:
                        bbox = geometry[0].get('boundingBox', {})
                        confidence = field_data.get('confidence', 0.0)
                        value = field_data.get('value', '')
                        
                        parsed_geometry[field_name] = {
                            'bbox': bbox,
                            'confidence': confidence,
                            'value': value,
                            'vertices': geometry[0].get('vertices', [])
                        }
        
        return parsed_geometry
    
    def draw_bounding_boxes(self, image_path: Path, geometry_data: Dict[str, Dict], 
                           output_path: Path) -> bool:
        """
        Draw bounding boxes on passport image
        
        Args:
            image_path: Path to input passport image
            geometry_data: Parsed geometry data from Bedrock
            output_path: Path to save annotated image
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Drawing bounding boxes on: {image_path}")
            
            # Load image using PIL for better text rendering
            pil_image = Image.open(image_path)
            draw = ImageDraw.Draw(pil_image)
            
            # Try to load a font, fallback to default if not available
            try:
                font = ImageFont.truetype("arial.ttf", 16)
            except:
                font = ImageFont.load_default()
            
            # Get image dimensions
            img_width, img_height = pil_image.size
            
            # Draw bounding boxes for each field
            for field_name, field_data in geometry_data.items():
                bbox = field_data['bbox']
                confidence = field_data['confidence']
                value = field_data['value']
                
                # Convert normalized coordinates to pixel coordinates
                left = int(bbox['left'] * img_width)
                top = int(bbox['top'] * img_height)
                width = int(bbox['width'] * img_width)
                height = int(bbox['height'] * img_height)
                
                # Get color for this field
                color = self.field_colors.get(field_name, (255, 255, 255))
                
                # Draw rectangle with semi-transparent fill and thick outline
                # Create a semi-transparent overlay
                overlay = Image.new('RGBA', pil_image.size, (0, 0, 0, 0))
                overlay_draw = ImageDraw.Draw(overlay)
                
                # Draw filled rectangle with low opacity
                overlay_draw.rectangle(
                    [left, top, left + width, top + height],
                    fill=(*color, 30),  # 30/255 = ~12% opacity
                    outline=(*color, 200),  # 200/255 = ~78% opacity
                    width=4
                )
                
                # Composite the overlay onto the main image
                pil_image = Image.alpha_composite(pil_image.convert('RGBA'), overlay).convert('RGB')
                draw = ImageDraw.Draw(pil_image)
                
                # Draw label background
                label_text = f"{self.field_display_names.get(field_name, field_name)}: {value}"
                label_bbox = draw.textbbox((0, 0), label_text, font=font)
                label_width = label_bbox[2] - label_bbox[0]
                label_height = label_bbox[3] - label_bbox[1]
                
                # Position label above the bounding box
                label_x = left
                label_y = max(0, top - label_height - 5)
                
                # Draw label background with better contrast
                label_bg_color = (255, 255, 255)  # White background
                label_text_color = (0, 0, 0)      # Black text for readability
                
                # Draw label background with white fill and colored border
                draw.rectangle(
                    [label_x, label_y, label_x + label_width, label_y + label_height],
                    fill=label_bg_color,
                    outline=color,
                    width=2
                )
                
                # Draw label text in black for maximum readability
                draw.text(
                    (label_x, label_y),
                    label_text,
                    fill=label_text_color,
                    font=font
                )
                

            
            # Save annotated image
            output_path.parent.mkdir(parents=True, exist_ok=True)
            pil_image.save(output_path, 'JPEG', quality=95)
            
            self.logger.info(f"Successfully saved annotated image: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to draw bounding boxes: {e}")
            return False
    

    
    def process_workflow_result(self, workflow_result: Dict[str, Any], 
                              output_dir: Path) -> Dict[str, Any]:
        """
        Process a workflow result and create annotated images
        
        Args:
            workflow_result: Complete workflow result
            output_dir: Directory to save annotated images
            
        Returns:
            Processing result with file paths
        """
        try:
            self.logger.info(f"Processing workflow: {workflow_result.get('workflow_id', 'Unknown')}")
            
            # Extract key information
            s3_key = workflow_result.get('document_processing', {}).get('s3_key', '')
            extraction_results = workflow_result.get('extraction_results', {})
            
            if not s3_key:
                self.logger.error("No S3 key found in workflow result")
                return {'success': False, 'error': 'No S3 key found'}
            
            # Create output paths
            filename = Path(s3_key).name
            base_name = Path(filename).stem
            
            # Download passport image
            temp_image_path = output_dir / f"temp_{filename}"
            if not self.download_passport_image(s3_key, temp_image_path):
                return {'success': False, 'error': 'Failed to download image'}
            
            # Check if we have Bedrock geometry data
            raw_response = extraction_results.get('raw_response', {})
            explainability_info = raw_response.get('explainability_info', [])
            
            result_files = {}
            
            if explainability_info:
                # Parse geometry data
                geometry_data = self.parse_bedrock_geometry(explainability_info)
                
                if geometry_data:
                    # Create bounding box image
                    bbox_output_path = output_dir / f"{base_name}_with_bboxes.jpg"
                    if self.draw_bounding_boxes(temp_image_path, geometry_data, bbox_output_path):
                        result_files['bounding_box_image'] = str(bbox_output_path)
                        self.logger.info(f"Created bounding box image: {bbox_output_path}")
                    else:
                        self.logger.warning("Failed to create bounding box image")
                else:
                    self.logger.warning("No valid geometry data found")
            

            
            # Clean up temporary file
            if temp_image_path.exists():
                temp_image_path.unlink()
            
            return {
                'success': True,
                'workflow_id': workflow_result.get('workflow_id', 'Unknown'),
                'original_image': s3_key,
                'result_files': result_files
            }
            
        except Exception as e:
            self.logger.error(f"Failed to process workflow result: {e}")
            return {'success': False, 'error': str(e)}
    
    def batch_process_workflows(self, workflow_results: List[Dict[str, Any]], 
                              output_dir: Path) -> Dict[str, Any]:
        """
        Process multiple workflow results in batch
        
        Args:
            workflow_results: List of workflow results
            output_dir: Directory to save annotated images
            
        Returns:
            Batch processing results
        """
        self.logger.info(f"Starting batch processing of {len(workflow_results)} workflows")
        
        results = []
        successful = 0
        failed = 0
        
        for i, workflow_result in enumerate(workflow_results, 1):
            self.logger.info(f"Processing {i}/{len(workflow_results)}: {workflow_result.get('workflow_id', 'Unknown')}")
            
            result = self.process_workflow_result(workflow_result, output_dir)
            results.append(result)
            
            if result['success']:
                successful += 1
            else:
                failed += 1
        
        self.logger.info(f"Batch processing completed: {successful} successful, {failed} failed")
        
        return {
            'total_processed': len(workflow_results),
            'successful': successful,
            'failed': failed,
            'results': results
        }
