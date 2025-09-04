"""
Unified Medical Certificate Pipeline
Combines all steps from document processing to PDF highlighting in one streamlined workflow
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import time

import sys
from pathlib import Path

# Add parent directory to path for config import
sys.path.append(str(Path(__file__).parent.parent))

from config.config import Config
from .document_processor import DocumentProcessor
from .bedrock_integrator import BedrockIntegrator
from .medical_highlight_visualizer import MedicalHighlightVisualizer

class UnifiedMedicalPipeline:
    """
    Unified Medical Certificate Pipeline
    
    Combines all processing steps into one streamlined workflow:
    1. Document Processing & S3 Upload
    2. Bedrock Data Extraction
    3. Quality Validation
    4. PDF Highlighting with Translucent Overlays
    5. Result Storage (Local & S3)
    6. S3 Cleanup (Input & Output Data)
    """
    
    def __init__(self, config: Config = None):
        """Initialize the unified medical pipeline"""
        self.config = config or Config()
        self.logger = self._setup_logging()
        
        # Initialize components
        self.document_processor = DocumentProcessor(self.config)
        self.bedrock_integrator = BedrockIntegrator(self.config)
        self.highlight_visualizer = MedicalHighlightVisualizer(self.config)
        
        # Override blueprint ARN for medical certificates
        self.config.BEDROCK_BLUEPRINT_ARN = "arn:aws:bedrock:us-east-1:122610487956:blueprint/8794f71ed722"
        self.config.BEDROCK_BLUEPRINT_NAME = "medical_certificate"
        
        # Medical certificate specific fields
        self.config.MEDICAL_CERTIFICATE_FIELDS = [
            'country', 'processed', 'notes', 'clientId', 'documentType', 
            'medicalCertificate', 'surname', 'dateProcessed', 'validFrom', 
            'forenames', 'staffId', 'validTo'
        ]
        
        # Pipeline statistics
        self.pipeline_stats = {
            'pipelines_started': 0,
            'pipelines_completed': 0,
            'pipelines_failed': 0,
            'total_documents_processed': 0,
            'total_extractions_performed': 0,
            'total_highlights_created': 0,
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
    
    def process_medical_certificate(self, bytes_data: bytes, filename: str) -> Dict[str, Any]:
        """
        Execute the complete unified medical certificate processing pipeline
        
        Args:
            bytes_data: Raw bytes of the medical certificate document
            filename: Original filename
            
        Returns:
            Complete pipeline result with all processing steps
        """
        try:
            self.pipeline_stats['pipelines_started'] += 1
            pipeline_id = f"pipeline_{int(time.time())}_{self.pipeline_stats['pipelines_started']}"
            
            self.logger.info(f"🚀 Starting unified medical certificate pipeline {pipeline_id} for: {filename}")
            
            # Step 1: Document Processing (Bytes -> Document -> S3 -> DocumentObject)
            self.logger.info("📄 Step 1: Document Processing & S3 Upload")
            document_object = self.document_processor.process_bytes(bytes_data, filename)
            
            # Step 2: Bedrock Data Extraction
            self.logger.info("🤖 Step 2: Bedrock Data Extraction")
            extracted_data = self.bedrock_integrator.extract_medical_certificate_data(
                document_object['s3_key'], 
                filename
            )
            
            # Step 3: Quality Validation
            self.logger.info("✅ Step 3: Quality Validation")
            validation_passed = self.bedrock_integrator.validate_medical_extraction(extracted_data)
            
            # Step 4: Create Final Result Object
            self.logger.info("📊 Step 4: Creating Final Result")
            final_result = self._create_final_result(
                pipeline_id, 
                document_object, 
                extracted_data, 
                validation_passed
            )
            
            # Step 5: PDF Highlighting with Translucent Overlays
            self.logger.info("🎨 Step 5: PDF Highlighting with Translucent Overlays")
            highlight_result = self._create_pdf_highlights(final_result, pipeline_id)
            
            # Step 6: Store Results with UUID-based Path
            self.logger.info("💾 Step 6: Storing Results with UUID Path")
            self._store_pipeline_results(final_result, pipeline_id, highlight_result)
            
            # Step 7: Cleanup S3 inputs and outputs now that results are stored locally
            self.logger.info("🧹 Step 7: Cleaning up S3 inputs and outputs")
            s3_cleanup_result = {'success': False, 'error': 'Cleanup not performed'}
            try:
                self._cleanup_s3_artifacts(
                    input_s3_key=document_object['s3_key'],
                    workflow_id=pipeline_id,
                    result_uuid=document_object.get('result_uuid'),
                    extracted_data=extracted_data
                )
                s3_cleanup_result = {
                    'success': True,
                    'input_deleted': True,
                    'results_deleted': True,
                    'cleanup_timestamp': datetime.now().isoformat()
                }
            except Exception as cleanup_error:
                self.logger.warning(f"Cleanup encountered an issue: {cleanup_error}")
                s3_cleanup_result = {
                    'success': False,
                    'error': str(cleanup_error),
                    'input_deleted': False,
                    'results_deleted': False
                }
            
            # Step 8: Update final result with cleanup info
            self.logger.info("📊 Step 8: Updating Final Result with Cleanup Info")
            final_result['s3_cleanup'] = s3_cleanup_result
            
            # Update statistics
            self.pipeline_stats['pipelines_completed'] += 1
            self.pipeline_stats['total_documents_processed'] += 1
            self.pipeline_stats['total_extractions_performed'] += 1
            if highlight_result.get('success'):
                self.pipeline_stats['total_highlights_created'] += 1
            
            self.logger.info(f"🎉 Unified pipeline {pipeline_id} completed successfully for: {filename}")
            
            return {
                'pipeline_id': pipeline_id,
                'success': True,
                'document_processing': document_object,
                'extraction_results': extracted_data,
                'validation_passed': validation_passed,
                'highlight_results': highlight_result,
                's3_cleanup': s3_cleanup_result,
                'final_result': final_result,
                'created_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.pipeline_stats['pipelines_failed'] += 1
            self.logger.error(f"❌ Unified pipeline failed for {filename}: {e}")
            raise
    
    def _create_final_result(self, pipeline_id: str, document_object: Dict[str, Any], 
                           extracted_data: Dict[str, Any], validation_passed: bool) -> Dict[str, Any]:
        """
        Create the final result object combining all processing steps
        
        Args:
            pipeline_id: Unique pipeline identifier
            document_object: Document processing result
            extracted_data: Bedrock extraction result
            validation_passed: Quality validation result
            
        Returns:
            Complete pipeline result
        """
        final_result = {
            'pipeline_id': pipeline_id,
            'pipeline_timestamp': datetime.now().isoformat(),
            'pipeline_version': '1.0.0',
            'status': 'completed' if validation_passed else 'completed_with_warnings',
            
            # Document processing results
            'document_processing': {
                'document_id': document_object['document_id'],
                's3_key': document_object['s3_key'],
                's3_bucket': document_object['s3_bucket'],
                'size_bytes': document_object['size_bytes'],
                'format': document_object['format'],
                'upload_timestamp': document_object['created_at']
            },
            
            # Bedrock extraction results
            'extraction_results': {
                'extracted_fields': extracted_data.get('extracted_fields', {}),
                'confidence_scores': extracted_data.get('confidence_scores', {}),
                'bounding_boxes': extracted_data.get('bounding_boxes', {}),
                'document_info': extracted_data.get('document_info', {}),
                'extraction_metadata': extracted_data.get('metadata', {}),
                'raw_response': extracted_data.get('raw_response', {})
            },
            
            # Quality metrics
            'quality_metrics': {
                'validation_passed': validation_passed,
                'confidence_threshold': self.config.CONFIDENCE_THRESHOLD,
                'overall_confidence': self._calculate_overall_confidence(extracted_data),
                'field_completeness': self._calculate_field_completeness(extracted_data)
            },
            
            # Processing metadata
            'processing_metadata': {
                'processor_version': '1.0.0',
                'config_used': {
                    'bucket': self.config.AWS_S3_BUCKET,
                    'region': self.config.AWS_REGION,
                    'blueprint_arn': self.config.BEDROCK_BLUEPRINT_ARN,
                    'confidence_threshold': self.config.CONFIDENCE_THRESHOLD
                },
                'pipeline_duration': None  # Will be calculated later
            }
        }
        
        return final_result
    
    def _create_pdf_highlights(self, final_result: Dict[str, Any], pipeline_id: str) -> Dict[str, Any]:
        """
        Create PDF highlights with translucent overlays
        
        Args:
            final_result: Complete pipeline result
            pipeline_id: Pipeline identifier
            
        Returns:
            Highlight creation result
        """
        try:
            # Create output directory for highlights
            output_dir = Path('highlighted_medical_certificates') / pipeline_id
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Create highlights using the visualizer
            highlight_result = self.highlight_visualizer.process_workflow_result(final_result, output_dir)
            
            return highlight_result
            
        except Exception as e:
            self.logger.error(f"Failed to create PDF highlights: {e}")
            return {
                'success': False,
                'error': str(e),
                'pipeline_id': pipeline_id
            }
    
    def _calculate_overall_confidence(self, extracted_data: Dict[str, Any]) -> float:
        """Calculate overall confidence score"""
        confidence_scores = extracted_data.get('confidence_scores', {})
        if not confidence_scores:
            return 0.0
        
        scores = list(confidence_scores.values())
        return sum(scores) / len(scores)
    
    def _calculate_field_completeness(self, extracted_data: Dict[str, Any]) -> float:
        """Calculate field completeness percentage"""
        extracted_fields = extracted_data.get('extracted_fields', {})
        required_fields = self.config.MEDICAL_CERTIFICATE_FIELDS
        
        if not required_fields:
            return 0.0
        
        completed_fields = sum(1 for field in required_fields if field in extracted_fields and extracted_fields[field])
        return (completed_fields / len(required_fields)) * 100
    
    def _store_pipeline_results(self, final_result: Dict[str, Any], pipeline_id: str, highlight_result: Dict[str, Any]):
        """
        Store pipeline results with UUID-based path structure
        
        Args:
            final_result: Complete pipeline result
            pipeline_id: Unique pipeline identifier
            highlight_result: Highlight creation result
        """
        try:
            # Create the UUID-based path structure
            result_key = self.config.get_s3_key_for_result(pipeline_id, 'pipeline_result.json')
            
            # Add highlight results to the final result
            final_result['highlight_results'] = highlight_result
            
            # Store the complete result in S3
            self.document_processor.s3_client.put_object(
                Bucket=self.config.AWS_S3_BUCKET,
                Key=result_key,
                Body=json.dumps(final_result, indent=2, default=str),
                ContentType='application/json',
                Metadata={
                    'pipeline_id': pipeline_id,
                    'pipeline_timestamp': final_result['pipeline_timestamp'],
                    'status': final_result['status'],
                    'stored_timestamp': datetime.now().isoformat()
                }
            )
            
            self.logger.info(f"💾 Stored pipeline results: s3://{self.config.AWS_S3_BUCKET}/{result_key}")
            
            # Store results locally as JSON files
            self._store_pipeline_results_locally(final_result, pipeline_id)
            
        except Exception as e:
            self.logger.error(f"Failed to store pipeline results: {e}")
            raise
    
    def _store_pipeline_results_locally(self, final_result: Dict[str, Any], pipeline_id: str):
        """
        Store pipeline results locally as JSON files
        
        Args:
            final_result: Complete pipeline result
            pipeline_id: Unique pipeline identifier
        """
        try:
            # Create local results directory structure
            local_results_dir = Path('local_medical_results') / pipeline_id
            local_results_dir.mkdir(parents=True, exist_ok=True)
            
            # Store the complete pipeline result
            pipeline_result_path = local_results_dir / 'pipeline_result.json'
            with open(pipeline_result_path, 'w', encoding='utf-8') as f:
                json.dump(final_result, f, indent=2, default=str, ensure_ascii=False)
            
            self.logger.info(f"💾 Stored local pipeline result: {pipeline_result_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to store local results: {e}")
            # Don't raise - local storage failure shouldn't break the pipeline
    
    def batch_process_documents(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process multiple documents in batch pipelines
        
        Args:
            files: List of file dictionaries with 'bytes' and 'filename' keys
            
        Returns:
            List of pipeline results
        """
        results = []
        
        self.logger.info(f"🚀 Starting batch processing of {len(files)} documents")
        
        for i, file_info in enumerate(files):
            try:
                self.logger.info(f"📄 Processing document {i+1}/{len(files)}: {file_info['filename']}")
                
                result = self.process_medical_certificate(
                    file_info['bytes'], 
                    file_info['filename']
                )
                results.append(result)
                
                # Add small delay between files
                if i < len(files) - 1:
                    time.sleep(0.5)
                
            except Exception as e:
                self.logger.error(f"Failed to process {file_info['filename']}: {e}")
                continue
        
        self.logger.info(f"✅ Batch processing completed. {len(results)}/{len(files)} documents processed successfully")
        return results
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get comprehensive pipeline statistics"""
        stats = self.pipeline_stats.copy()
        stats['end_time'] = datetime.now()
        stats['duration'] = (stats['end_time'] - stats['start_time']).total_seconds()
        
        # Calculate success rate
        if stats['pipelines_started'] > 0:
            stats['success_rate'] = (stats['pipelines_completed'] / stats['pipelines_started']) * 100
        else:
            stats['success_rate'] = 0
        
        # Add component statistics
        stats['document_processing_stats'] = self.document_processor.get_processing_stats()
        stats['bedrock_extraction_stats'] = self.bedrock_integrator.get_extraction_stats()
        stats['highlight_stats'] = self.highlight_visualizer.get_highlight_stats()
        
        return stats
    
    def create_pipeline_report(self) -> Dict[str, Any]:
        """Create a comprehensive pipeline report"""
        stats = self.get_pipeline_stats()
        
        report = {
            'report_timestamp': datetime.now().isoformat(),
            'pipeline_summary': {
                'total_pipelines': stats['pipelines_started'],
                'successful_pipelines': stats['pipelines_completed'],
                'failed_pipelines': stats['pipelines_failed'],
                'success_rate_percentage': stats['success_rate'],
                'total_duration_seconds': stats['duration']
            },
            'processing_metrics': {
                'documents_processed': stats['total_documents_processed'],
                'extractions_performed': stats['total_extractions_performed'],
                'highlights_created': stats['total_highlights_created'],
                'average_pipeline_duration': stats['duration'] / max(stats['pipelines_started'], 1)
            },
            'component_performance': {
                'document_processor': stats['document_processing_stats'],
                'bedrock_integrator': stats['bedrock_extraction_stats'],
                'highlight_visualizer': stats['highlight_stats']
            },
            'configuration_used': {
                's3_bucket': self.config.AWS_S3_BUCKET,
                'region': self.config.AWS_REGION,
                'blueprint_arn': self.config.BEDROCK_BLUEPRINT_ARN,
                'confidence_threshold': self.config.CONFIDENCE_THRESHOLD
            }
        }
        
        return report
    
    def _cleanup_s3_artifacts(self, input_s3_key: str, workflow_id: str, result_uuid: str = None, extracted_data: Dict[str, Any] = None):
        """Delete input object and results prefixes from S3 after local persistence.
        - Deletes uploaded input document (input_s3_key)
        - Deletes our results prefix results/<workflow_id>/
        - Deletes document_processor result metadata results/<result_uuid>/ (if present)
        - Deletes Bedrock clientToken results results/<client_token>/ (if discoverable)
        """
        bucket = self.config.AWS_S3_BUCKET
        s3 = self.document_processor.s3_client

        def _delete_key(key: str):
            if not key:
                return
            try:
                s3.delete_object(Bucket=bucket, Key=key)
                self.logger.info(f"🗑️ Deleted s3://{bucket}/{key}")
            except Exception as e:
                self.logger.debug(f"Skip delete (may not exist) {key}: {e}")

        def _delete_prefix(prefix: str):
            if not prefix:
                return
            try:
                paginator = s3.get_paginator('list_objects_v2')
                to_delete = []
                for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                    for obj in page.get('Contents', []):
                        to_delete.append({'Key': obj['Key']})
                        if len(to_delete) == 1000:
                            s3.delete_objects(Bucket=bucket, Delete={'Objects': to_delete})
                            to_delete.clear()
                if to_delete:
                    s3.delete_objects(Bucket=bucket, Delete={'Objects': to_delete})
                self.logger.info(f"🧹 Deleted prefix s3://{bucket}/{prefix}")
            except Exception as e:
                self.logger.debug(f"Skip delete prefix {prefix}: {e}")

        # 1) Delete input document
        _delete_key(input_s3_key)

        # 2) Delete pipeline workflow results
        _delete_prefix(self.config.get_s3_key_for_result(workflow_id, ''))

        # 3) Delete DocumentProcessor result metadata path
        if result_uuid:
            _delete_prefix(self.config.get_s3_key_for_result(result_uuid, ''))

        # 4) Delete Bedrock clientToken results if we can infer it
        try:
            raw = (extracted_data or {}).get('raw_response', {})
            client_token = None
            for segment in raw.get('output_metadata', []):
                for seg in segment.get('segment_metadata', []):
                    path = seg.get('custom_output_path') or ''
                    if '/results/' in path:
                        after = path.split('/results/', 1)[1]
                        token = after.split('/', 1)[0]
                        if token:
                            client_token = token
                            break
                if client_token:
                    break
            if client_token:
                _delete_prefix(f"results/{client_token}/")
        except Exception as e:
            self.logger.debug(f"Could not infer client token for cleanup: {e}")
