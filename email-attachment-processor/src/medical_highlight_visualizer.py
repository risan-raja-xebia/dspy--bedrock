"""
Medical Certificate Highlight Visualizer
Creates highlighted regions with translucent shading for medical certificate fields
This is more appropriate for PDF documents than bounding boxes
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json
import boto3
from PIL import Image, ImageDraw, ImageFont
import io
import fitz  # PyMuPDF for PDF manipulation

import sys
from pathlib import Path

# Add parent directory to path for config import
sys.path.append(str(Path(__file__).parent.parent))

from config.config import Config

class MedicalHighlightVisualizer:
    """
    Medical Certificate Highlight Visualizer
    
    Creates translucent highlighted regions for medical certificate fields
    instead of bounding boxes, which is more appropriate for PDF documents
    """
    
    def __init__(self, config: Config = None):
        """Initialize the medical highlight visualizer"""
        self.config = config or Config()
        self.logger = self._setup_logging()
        self.s3_client = self._setup_s3_client()
        
        # Medical certificate field colors with alpha (translucent)
        self.field_colors = {
            'country': (220, 20, 60, 128),           # Crimson Red with 50% opacity
            'processed': (34, 139, 34, 128),          # Forest Green with 50% opacity
            'notes': (25, 25, 112, 128),              # Midnight Blue with 50% opacity
            'clientId': (255, 140, 0, 128),          # Dark Orange with 50% opacity
            'documentType': (138, 43, 226, 128),      # Blue Violet with 50% opacity
            'medicalCertificate': (0, 100, 100, 128), # Dark Cyan with 50% opacity
            'surname': (75, 0, 130, 128),             # Indigo with 50% opacity
            'dateProcessed': (178, 34, 34, 128),      # Fire Brick with 50% opacity
            'validFrom': (128, 0, 128, 128),          # Purple with 50% opacity
            'forenames': (0, 128, 128, 128),          # Teal with 50% opacity
            'staffId': (255, 69, 0, 128),             # Orange Red with 50% opacity
            'validTo': (0, 100, 0, 128)               # Dark Green with 50% opacity
        }
        
        # Default color for unknown fields
        self.default_color = (128, 128, 128, 128)  # Gray with 50% opacity
        
        # Processing statistics
        self.stats = {
            'highlights_created': 0,
            'fields_highlighted': 0,
            'errors': 0,
            'start_time': datetime.now()
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Setup simple console logging only"""
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
        except Exception as e:
            self.logger.error(f"Failed to setup S3 client: {e}")
            raise
    
    def process_workflow_result(self, workflow_result: Dict[str, Any], output_dir: Path) -> Dict[str, Any]:
        """
        Process workflow result to create highlighted regions
        
        Args:
            workflow_result: Complete workflow result with extraction data
            output_dir: Output directory for highlighted images
            
        Returns:
            Highlight creation result
        """
        try:
            workflow_id = workflow_result.get('workflow_id', 'unknown')
            self.logger.info(f"🎨 Creating highlighted regions for workflow {workflow_id}")
            
            # Extract data from workflow result
            extraction_results = workflow_result.get('extraction_results', {})
            extracted_fields = extraction_results.get('extracted_fields', {})
            document_processing = workflow_result.get('document_processing', {})
            
            # Get document info
            s3_key = document_processing.get('s3_key', '')
            document_format = document_processing.get('format', '')
            
            # Check if we have geometry data for highlighting
            explainability_info = self._extract_geometry_data(extraction_results)
            
            if not explainability_info:
                self.logger.warning(f"⚠️ No geometry data available for workflow {workflow_id}")
                return {
                    'success': False,
                    'error': 'No geometry data available for highlighting',
                    'workflow_id': workflow_id
                }
            
            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Download document for highlighting
            document_path = self._download_document_for_highlighting(s3_key, output_dir)
            
            # Create highlighted version
            highlighted_path = self._create_highlighted_regions(
                document_path, 
                explainability_info, 
                extracted_fields, 
                output_dir,
                workflow_id
            )
            
            if highlighted_path:
                self.stats['highlights_created'] += 1
                self.logger.info(f"✅ Highlighted regions created successfully: {highlighted_path}")
                
                return {
                    'success': True,
                    'result_files': {
                        'highlighted_document': str(highlighted_path),
                        'original_document': str(document_path)
                    },
                    'workflow_id': workflow_id,
                    'fields_highlighted': len(extracted_fields),
                    'created_at': datetime.now().isoformat()
                }
            else:
                self.stats['errors'] += 1
                return {
                    'success': False,
                    'error': 'Failed to create highlighted regions',
                    'workflow_id': workflow_id
                }
                
        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"❌ Failed to create highlighted regions: {e}")
            return {
                'success': False,
                'error': str(e),
                'workflow_id': workflow_result.get('workflow_id', 'unknown')
            }
    
    def _extract_geometry_data(self, extraction_results: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """
        Extract geometry data from Bedrock extraction results
        
        Args:
            extraction_results: Extraction results from Bedrock
            
        Returns:
            List of geometry data for highlighting
        """
        try:
            # First, try to get explainability_info directly from the extraction results
            if 'explainability_info' in extraction_results:
                self.logger.info("✅ Found explainability_info directly in extraction results")
                return extraction_results['explainability_info']
            
            # Check in raw_response
            raw_response = extraction_results.get('raw_response', {})
            if 'explainability_info' in raw_response:
                self.logger.info("✅ Found explainability_info in raw_response")
                return raw_response['explainability_info']
            
            # Check in custom_output within raw_response
            if 'custom_output' in raw_response:
                custom_output = raw_response['custom_output']
                if 'explainability_info' in custom_output:
                    self.logger.info("✅ Found explainability_info in custom_output")
                    return custom_output['explainability_info']
            
            # Navigate through the BDA output structure to find explainability_info
            for segment in raw_response.get('output_metadata', []):
                for seg_metadata in segment.get('segment_metadata', []):
                    if seg_metadata.get('custom_output_status') == 'MATCH':
                        custom_output_path = seg_metadata.get('custom_output_path', '')
                        if custom_output_path:
                            try:
                                # Get the custom output results that contain explainability_info
                                uri_parts = custom_output_path.replace('s3://', '').split('/', 1)
                                bucket = uri_parts[0]
                                key = uri_parts[1]
                                
                                response = self.s3_client.get_object(Bucket=bucket, Key=key)
                                custom_results = json.loads(response['Body'].read().decode('utf-8'))
                                
                                # Look for explainability_info in the custom results
                                if 'explainability_info' in custom_results:
                                    self.logger.info("✅ Found explainability_info in custom output")
                                    return custom_results['explainability_info']
                                    
                            except Exception as e:
                                self.logger.warning(f"Failed to retrieve custom output for geometry data: {e}")
                                continue
            
            self.logger.warning("❌ No explainability_info found in any location")
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to extract geometry data: {e}")
            return None
    
    def _download_document_for_highlighting(self, s3_key: str, output_dir: Path) -> Path:
        """
        Download document from S3 for highlighting
        
        Args:
            s3_key: S3 key of the document
            output_dir: Output directory
            
        Returns:
            Path to the downloaded document
        """
        try:
            filename = Path(s3_key).name
            local_path = output_dir / f"original_{filename}"
            
            self.s3_client.download_file(self.config.AWS_S3_BUCKET, s3_key, str(local_path))
            self.logger.info(f"✅ Successfully downloaded document: {local_path}")
            return local_path
            
        except Exception as e:
            self.logger.error(f"Failed to download document: {e}")
            raise
    
    def _create_highlighted_regions(self, document_path: Path, explainability_info: List[Dict[str, Any]], 
                                   extracted_fields: Dict[str, Any], output_dir: Path, workflow_id: str) -> Optional[Path]:
        """
        Create highlighted regions with translucent shading directly on the PDF
        
        Args:
            document_path: Path to the original document
            explainability_info: Geometry data from Bedrock
            extracted_fields: Extracted field data
            output_dir: Output directory
            workflow_id: Workflow identifier
            
        Returns:
            Path to the highlighted document
        """
        try:
            # Check if the document is a PDF
            if document_path.suffix.lower() == '.pdf':
                # Create highlighted PDF with translucent overlays
                highlighted_pdf_path = self._create_highlighted_pdf(
                    document_path, 
                    explainability_info, 
                    extracted_fields, 
                    output_dir, 
                    workflow_id
                )
                
                if highlighted_pdf_path:
                    # Also create a JSON file with highlight coordinates for reference
                    highlight_data = self._create_highlight_coordinates(explainability_info, extracted_fields)
                    highlight_json_path = output_dir / f"highlight_coordinates_{workflow_id}.json"
                    
                    with open(highlight_json_path, 'w', encoding='utf-8') as f:
                        json.dump(highlight_data, f, indent=2, default=str, ensure_ascii=False)
                    
                    self.logger.info(f"✅ Created highlighted PDF: {highlighted_pdf_path}")
                    self.logger.info(f"✅ Created highlight coordinates: {highlight_json_path}")
                    
                    return highlighted_pdf_path
            else:
                # For non-PDF documents, create a summary image
                summary_image = self._create_field_summary_image(extracted_fields, explainability_info, workflow_id)
                
                if summary_image:
                    output_path = output_dir / f"highlighted_summary_{workflow_id}.png"
                    summary_image.save(output_path, 'PNG')
                    
                    # Also create a JSON file with highlight coordinates for reference
                    highlight_data = self._create_highlight_coordinates(explainability_info, extracted_fields)
                    highlight_json_path = output_dir / f"highlight_coordinates_{workflow_id}.json"
                    
                    with open(highlight_json_path, 'w', encoding='utf-8') as f:
                        json.dump(highlight_data, f, indent=2, default=str, ensure_ascii=False)
                    
                    self.logger.info(f"✅ Created highlight summary: {output_path}")
                    self.logger.info(f"✅ Created highlight coordinates: {highlight_json_path}")
                    
                    return output_path
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to create highlighted regions: {e}")
            return None
    
    def _create_highlighted_pdf(self, document_path: Path, explainability_info: List[Dict[str, Any]], 
                               extracted_fields: Dict[str, Any], output_dir: Path, workflow_id: str) -> Optional[Path]:
        """
        Create a highlighted PDF with translucent overlays on the extracted fields
        
        Args:
            document_path: Path to the original PDF
            explainability_info: Geometry data from Bedrock
            extracted_fields: Extracted field data
            output_dir: Output directory
            workflow_id: Workflow identifier
            
        Returns:
            Path to the highlighted PDF
        """
        try:
            # Open the PDF document
            pdf_document = fitz.open(str(document_path))
            
            # Create output path
            output_path = output_dir / f"highlighted_{document_path.name}"
            
            # Process each page that has highlights
            if explainability_info and len(explainability_info) > 0:
                field_data = explainability_info[0]  # Get the first (and only) object
                
                for field_name, field_info in field_data.items():
                    if isinstance(field_info, dict) and 'geometry' in field_info:
                        geometry = field_info['geometry']
                        
                        # Get the page number (default to 1 if not specified)
                        page_num = geometry[0].get('page', 1) - 1  # PyMuPDF uses 0-based indexing
                        
                        if 0 <= page_num < len(pdf_document):
                            page = pdf_document[page_num]
                            
                            # Get the bounding box coordinates
                            bbox = geometry[0].get('boundingBox', {})
                            
                            # Convert normalized coordinates to PDF coordinates
                            page_width = page.rect.width
                            page_height = page.rect.height
                            
                            # Calculate rectangle coordinates
                            left = bbox.get('left', 0) * page_width
                            top = bbox.get('top', 0) * page_height
                            width = bbox.get('width', 0) * page_width
                            height = bbox.get('height', 0) * page_height
                            
                            # Create rectangle for highlighting
                            rect = fitz.Rect(left, top, left + width, top + height)
                            
                            # Get color for this field (convert RGBA to RGB)
                            color = self.field_colors.get(field_name, self.default_color)
                            rgb_color = (color[0] / 255, color[1] / 255, color[2] / 255)
                            
                            # Add highlight annotation
                            highlight = page.add_highlight_annot(rect)
                            highlight.set_colors(stroke=rgb_color)
                            highlight.set_opacity(0.5)  # 50% opacity
                            
                            # Add text annotation with field name
                            text_rect = fitz.Rect(left, top - 15, left + 100, top)
                            text_annot = page.add_text_annot(text_rect.tl, field_name)
                            text_annot.set_colors(stroke=(0, 0, 0))
                            text_annot.set_opacity(0.8)
                            
                            self.stats['fields_highlighted'] += 1
            
            # Save the highlighted PDF
            pdf_document.save(str(output_path))
            pdf_document.close()
            
            return output_path
            
        except Exception as e:
            self.logger.error(f"Failed to create highlighted PDF: {e}")
            return None
    
    def _create_field_summary_image(self, extracted_fields: Dict[str, Any], 
                                  explainability_info: List[Dict[str, Any]], 
                                  workflow_id: str) -> Optional[Image.Image]:
        """
        Create a summary image showing extracted fields with highlighted regions
        
        Args:
            extracted_fields: Extracted field data
            explainability_info: Geometry data from Bedrock
            workflow_id: Workflow identifier
            
        Returns:
            Summary image with highlights
        """
        try:
            # Create a summary image
            image_width = 800
            image_height = 600
            margin = 20
            
            # Create base image with white background
            image = Image.new('RGBA', (image_width, image_height), (255, 255, 255, 255))
            draw = ImageDraw.Draw(image)
            
            # Try to load a font (fallback to default if not available)
            try:
                font = ImageFont.truetype("arial.ttf", 14)
                title_font = ImageFont.truetype("arial.ttf", 18)
            except:
                font = ImageFont.load_default()
                title_font = ImageFont.load_default()
            
            # Draw title
            title = f"Medical Certificate Highlights - {workflow_id[:8]}"
            draw.text((margin, margin), title, fill=(0, 0, 0, 255), font=title_font)
            
            # Draw timestamp
            timestamp = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            draw.text((margin, margin + 30), timestamp, fill=(100, 100, 100, 255), font=font)
            
            # Draw extracted fields with highlights
            y_position = margin + 80
            field_count = 0
            
            for field_name, field_value in extracted_fields.items():
                if field_count >= 15:  # Limit to prevent overflow
                    break
                
                # Get color for this field
                color = self.field_colors.get(field_name, self.default_color)
                
                # Draw field name with background highlight
                field_text = f"{field_name}: {field_value}"
                text_bbox = draw.textbbox((margin + 10, y_position), field_text, font=font)
                
                # Draw translucent background
                draw.rectangle(text_bbox, fill=color)
                
                # Draw text
                draw.text((margin + 10, y_position), field_text, fill=(0, 0, 0, 255), font=font)
                
                y_position += 25
                field_count += 1
                self.stats['fields_highlighted'] += 1
            
            # Draw legend
            legend_y = image_height - 120
            draw.text((margin, legend_y), "Field Highlight Legend:", fill=(0, 0, 0, 255), font=title_font)
            
            legend_items = list(self.field_colors.items())[:6]  # Show first 6 colors
            for i, (field_name, color) in enumerate(legend_items):
                legend_x = margin + (i % 3) * 200
                legend_y_pos = legend_y + 30 + (i // 3) * 20
                
                # Draw color box
                draw.rectangle([legend_x, legend_y_pos, legend_x + 15, legend_y_pos + 15], fill=color)
                draw.text((legend_x + 20, legend_y_pos), field_name, fill=(0, 0, 0, 255), font=font)
            
            return image
            
        except Exception as e:
            self.logger.error(f"Failed to create field summary image: {e}")
            return None
    
    def _create_highlight_coordinates(self, explainability_info: List[Dict[str, Any]], 
                                     extracted_fields: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create highlight coordinates data for reference
        
        Args:
            explainability_info: Geometry data from Bedrock
            extracted_fields: Extracted field data
            
        Returns:
            Highlight coordinates data
        """
        try:
            highlight_data = {
                'workflow_timestamp': datetime.now().isoformat(),
                'total_fields': len(extracted_fields),
                'highlighted_regions': [],
                'field_mapping': {}
            }
            
            # Process explainability info to extract coordinates
            # explainability_info is a list with one object containing all field data
            if explainability_info and len(explainability_info) > 0:
                field_data = explainability_info[0]  # Get the first (and only) object
                
                for field_name, field_info in field_data.items():
                    if isinstance(field_info, dict) and 'geometry' in field_info:
                        region_data = {
                            'field_name': field_name,
                            'coordinates': field_info['geometry'],
                            'confidence': field_info.get('confidence', 0.0),
                            'extracted_value': field_info.get('value', ''),
                            'success': field_info.get('success', False)
                        }
                        
                        highlight_data['highlighted_regions'].append(region_data)
                        highlight_data['field_mapping'][field_name] = len(highlight_data['highlighted_regions']) - 1
            
            return highlight_data
            
        except Exception as e:
            self.logger.error(f"Failed to create highlight coordinates: {e}")
            return {
                'error': str(e),
                'workflow_timestamp': datetime.now().isoformat()
            }
    
    def get_highlight_stats(self) -> Dict[str, Any]:
        """Get current highlighting statistics"""
        stats = self.stats.copy()
        stats['end_time'] = datetime.now()
        stats['duration'] = (stats['end_time'] - stats['start_time']).total_seconds()
        return stats
