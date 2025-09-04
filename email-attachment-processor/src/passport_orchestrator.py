"""
Passport Processing Orchestrator
Main class that coordinates the entire workflow:
1. Document Processing
2. Bedrock Integration
3. Result Storage with UUID paths
4. Quality Validation
"""

import os
import uuid
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import boto3

from config.config import Config
from .document_processor import DocumentProcessor
from .bedrock_integrator import BedrockIntegrator
from .bounding_box_visualizer import BoundingBoxVisualizer

class PassportOrchestrator:
    """
    Main orchestrator for passport processing workflow
    
    Implements the complete flowchart:
    Bytes -> Format Check -> Conversion -> Document -> S3 Upload -> Bedrock Processing -> DocumentObject
    """
    
    def __init__(self, config: Config = None):
        """Initialize the passport orchestrator"""
        self.config = config or Config()
        self.logger = self._setup_logging()
        
        # Initialize components
        self.document_processor = DocumentProcessor(self.config)
        self.bedrock_integrator = BedrockIntegrator(self.config)
        self.bounding_box_visualizer = BoundingBoxVisualizer(self.config)
        
        # Workflow statistics
        self.workflow_stats = {
            'workflows_started': 0,
            'workflows_completed': 0,
            'workflows_failed': 0,
            'total_documents_processed': 0,
            'total_extractions_performed': 0,
            'total_bounding_boxes_created': 0,
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
    
    def process_passport_workflow(self, bytes_data: bytes, filename: str) -> Dict[str, Any]:
        """
        Execute the complete passport processing workflow
        
        Args:
            bytes_data: Raw bytes of the passport image
            filename: Original filename
            
        Returns:
            Complete workflow result with UUID-based storage
        """
        try:
            self.workflow_stats['workflows_started'] += 1
            workflow_id = str(uuid.uuid4())
            
            self.logger.info(f"🚀 Starting passport workflow {workflow_id} for: {filename}")
            
            # Step 1: Document Processing (Bytes -> Document -> S3 -> DocumentObject)
            self.logger.info("📄 Step 1: Document Processing")
            document_object = self.document_processor.process_bytes(bytes_data, filename)
            
            # Step 2: Bedrock Data Extraction
            self.logger.info("🤖 Step 2: Bedrock Data Extraction")
            extracted_data = self.bedrock_integrator.extract_passport_data(
                document_object['s3_key'], 
                filename
            )
            
            # Step 3: Quality Validation
            self.logger.info("✅ Step 3: Quality Validation")
            validation_passed = self.bedrock_integrator.validate_extraction(extracted_data)
            
            # Step 4: Create Bounding Box Visualization
            self.logger.info("🎨 Step 4: Creating Bounding Box Visualization")
            bounding_box_result = self._create_bounding_box_visualization(
                workflow_id, 
                document_object, 
                extracted_data
            )
            
            # Step 5: Create Final Result Object (without cleanup info for now)
            self.logger.info("📊 Step 5: Creating Final Result")
            final_result = self._create_final_result(
                workflow_id, 
                document_object, 
                extracted_data, 
                validation_passed,
                bounding_box_result
            )
            
            # Step 6: Store Results with UUID-based Path
            self.logger.info("💾 Step 6: Storing Results with UUID Path")
            self._store_workflow_results(final_result, workflow_id)

            # Step 7: Cleanup S3 inputs and outputs now that results are stored locally
            self.logger.info("🧹 Step 7: Cleaning up S3 inputs and outputs")
            s3_cleanup_result = {'success': False, 'error': 'Cleanup not performed'}
            try:
                self._cleanup_s3_artifacts(
                    input_s3_key=document_object['s3_key'],
                    workflow_id=workflow_id,
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
            self.workflow_stats['workflows_completed'] += 1
            self.workflow_stats['total_documents_processed'] += 1
            self.workflow_stats['total_extractions_performed'] += 1
            if bounding_box_result.get('success'):
                self.workflow_stats['total_bounding_boxes_created'] += 1
            
            self.logger.info(f"🎉 Workflow {workflow_id} completed successfully for: {filename}")
            
            return final_result
            
        except Exception as e:
            self.workflow_stats['workflows_failed'] += 1
            self.logger.error(f"❌ Workflow failed for {filename}: {e}")
            raise
    
    def _create_final_result(self, workflow_id: str, document_object: Dict[str, Any], 
                           extracted_data: Dict[str, Any], validation_passed: bool, 
                           bounding_box_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create the final result object combining all processing steps
        
        Args:
            workflow_id: Unique workflow identifier
            document_object: Document processing result
            extracted_data: Bedrock extraction result
            validation_passed: Quality validation result
            
        Returns:
            Complete workflow result
        """
        final_result = {
            'workflow_id': workflow_id,
            'workflow_timestamp': datetime.now().isoformat(),
            'workflow_version': '1.0.0',
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
                'extraction_metadata': extracted_data.get('metadata', {})
            },
            
            # Quality metrics
            'quality_metrics': {
                'validation_passed': validation_passed,
                'confidence_threshold': self.config.CONFIDENCE_THRESHOLD,
                'overall_confidence': self._calculate_overall_confidence(extracted_data),
                'field_completeness': self._calculate_field_completeness(extracted_data),
                'bounding_box_count': self._count_bounding_boxes(extracted_data)
            },
            
            # Bounding box visualization results
            'bounding_box_visualization': {
                'success': bounding_box_result.get('success', False),
                'output_files': bounding_box_result.get('result_files', {}),
                'error': bounding_box_result.get('error', None),
                'created_at': datetime.now().isoformat()
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
                'workflow_duration': None  # Will be calculated later
            }
        }
        
        return final_result
    
    def _create_bounding_box_visualization(self, workflow_id: str, document_object: Dict[str, Any], 
                                         extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create bounding box visualization for the processed passport
        
        Args:
            workflow_id: Unique workflow identifier
            document_object: Document processing result
            extracted_data: Bedrock extraction result
            
        Returns:
            Bounding box creation result
        """
        try:
            self.logger.info(f"🎨 Creating bounding box visualization for workflow {workflow_id}")
            
            # Check if we have geometry data for bounding boxes
            raw_response = extracted_data.get('raw_response', {})
            
            # Look for geometry data in the Bedrock Data Automation response structure
            explainability_info = None
            
            # Navigate through the BDA output structure to find explainability_info
            for segment in raw_response.get('output_metadata', []):
                for seg_metadata in segment.get('segment_metadata', []):
                    if seg_metadata.get('custom_output_status') == 'MATCH':
                        custom_output_path = seg_metadata.get('custom_output_path', '')
                        if custom_output_path:
                            try:
                                # Get the custom output results that contain explainability_info
                                s3_client = boto3.client('s3', region_name=self.config.AWS_REGION)
                                uri_parts = custom_output_path.replace('s3://', '').split('/', 1)
                                bucket = uri_parts[0]
                                key = uri_parts[1]
                                
                                response = s3_client.get_object(Bucket=bucket, Key=key)
                                custom_results = json.loads(response['Body'].read().decode('utf-8'))
                                
                                # Look for explainability_info in the custom results
                                if 'explainability_info' in custom_results:
                                    explainability_info = custom_results['explainability_info']
                                    break
                                    
                            except Exception as e:
                                self.logger.warning(f"Failed to retrieve custom output for geometry data: {e}")
                                continue
                
                if explainability_info:
                    break
            
            if not explainability_info:
                self.logger.warning(f"⚠️ No geometry data available for workflow {workflow_id}. Skipping bounding box creation.")
                return {
                    'success': False,
                    'error': 'No geometry data available',
                    'workflow_id': workflow_id
                }
            
            # Create output directory for this workflow
            output_dir = Path('annotated_passports') / workflow_id
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Create a mock workflow result structure for the visualizer
            mock_workflow_result = {
                'workflow_id': workflow_id,
                'document_processing': {
                    's3_key': document_object['s3_key']
                },
                'extraction_results': {
                    'raw_response': {
                        'explainability_info': explainability_info
                    },
                    'extracted_fields': extracted_data.get('extracted_fields', {}),
                    'file_key': document_object['s3_key']
                }
            }
            
            # Process the workflow result to create bounding box visualization
            result = self.bounding_box_visualizer.process_workflow_result(
                mock_workflow_result, 
                output_dir
            )
            
            if result['success']:
                self.logger.info(f"✅ Bounding box visualization created successfully for workflow {workflow_id}")
                # Store the bounding box result path in S3 for future reference
                self._store_bounding_box_result(workflow_id, result, output_dir)
            else:
                self.logger.warning(f"⚠️ Bounding box visualization failed for workflow {workflow_id}: {result.get('error', 'Unknown error')}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Failed to create bounding box visualization for workflow {workflow_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'workflow_id': workflow_id
            }
    
    def _store_bounding_box_result(self, workflow_id: str, result: Dict[str, Any], output_dir: Path):
        """Store bounding box result information in S3"""
        try:
            # Create a summary of the bounding box creation
            bbox_summary = {
                'workflow_id': workflow_id,
                'bounding_box_creation_timestamp': datetime.now().isoformat(),
                'success': result['success'],
                'output_files': result.get('result_files', {}),
                'output_directory': str(output_dir),
                'status': 'completed' if result['success'] else 'failed'
            }
            
            if not result['success']:
                bbox_summary['error'] = result.get('error', 'Unknown error')
            
            # Store the summary
            summary_key = self.config.get_s3_key_for_result(workflow_id, 'bounding_box_summary.json')
            self.document_processor.s3_client.put_object(
                Bucket=self.config.AWS_S3_BUCKET,
                Key=summary_key,
                Body=json.dumps(bbox_summary, indent=2, default=str),
                ContentType='application/json'
            )
            
            self.logger.info(f"💾 Stored bounding box summary: s3://{self.config.AWS_S3_BUCKET}/{summary_key}")
            
        except Exception as e:
            self.logger.error(f"Failed to store bounding box summary: {e}")
    
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
        required_fields = self.config.PASSPORT_FIELDS
        
        if not required_fields:
            return 0.0
        
        completed_fields = sum(1 for field in required_fields if field in extracted_fields and extracted_fields[field])
        return (completed_fields / len(required_fields)) * 100
    
    def _count_bounding_boxes(self, extracted_data: Dict[str, Any]) -> int:
        """Count total bounding boxes"""
        bounding_boxes = extracted_data.get('bounding_boxes', {})
        total_boxes = 0
        
        for field_boxes in bounding_boxes.values():
            if isinstance(field_boxes, list):
                total_boxes += len(field_boxes)
        
        return total_boxes
    
    def _store_workflow_results(self, final_result: Dict[str, Any], workflow_id: str):
        """
        Store workflow results with UUID-based path structure
        
        Args:
            final_result: Complete workflow result
            workflow_id: Unique workflow identifier
        """
        try:
            # Create the UUID-based path structure
            result_key = self.config.get_s3_key_for_result(workflow_id, 'workflow_result.json')
            
            # Store the complete result in S3
            self.document_processor.s3_client.put_object(
                Bucket=self.config.AWS_S3_BUCKET,
                Key=result_key,
                Body=json.dumps(final_result, indent=2, default=str),
                ContentType='application/json',
                Metadata={
                    'workflow_id': workflow_id,
                    'workflow_timestamp': final_result['workflow_timestamp'],
                    'status': final_result['status'],
                    'stored_timestamp': datetime.now().isoformat()
                }
            )
            
            self.logger.info(f"💾 Stored workflow results: s3://{self.config.AWS_S3_BUCKET}/{result_key}")
            
            # Also store a summary for quick access in S3
            summary_key = self.config.get_s3_key_for_result(workflow_id, 'summary.json')
            summary = {
                'workflow_id': workflow_id,
                'status': final_result['status'],
                'filename': final_result['document_processing']['s3_key'].split('/')[-1],
                'overall_confidence': final_result['quality_metrics']['overall_confidence'],
                'field_completeness': final_result['quality_metrics']['field_completeness'],
                'bounding_box_count': final_result['quality_metrics']['bounding_box_count'],
                'timestamp': final_result['workflow_timestamp']
            }
            
            self.document_processor.s3_client.put_object(
                Bucket=self.config.AWS_S3_BUCKET,
                Key=summary_key,
                Body=json.dumps(summary, indent=2, default=str),
                ContentType='application/json'
            )
            
            # NEW: Store results locally as JSON files
            self._store_workflow_results_locally(final_result, workflow_id, summary)
            
        except Exception as e:
            self.logger.error(f"Failed to store workflow results: {e}")
            raise
    
    def _store_workflow_results_locally(self, final_result: Dict[str, Any], workflow_id: str, summary: Dict[str, Any]):
        """
        Store workflow results locally as JSON files
        
        Args:
            final_result: Complete workflow result
            workflow_id: Unique workflow identifier
            summary: Workflow summary
        """
        try:
            # Create local results directory structure
            local_results_dir = Path('local_results') / workflow_id
            local_results_dir.mkdir(parents=True, exist_ok=True)
            
            # Store only the complete workflow result
            workflow_result_path = local_results_dir / 'workflow_result.json'
            with open(workflow_result_path, 'w', encoding='utf-8') as f:
                json.dump(final_result, f, indent=2, default=str, ensure_ascii=False)
            
            self.logger.info(f"💾 Stored local workflow result: {workflow_result_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to store local results: {e}")
            # Don't raise - local storage failure shouldn't break the workflow
    
    def _cleanup_s3_artifacts(self, input_s3_key: str, workflow_id: str, result_uuid: str = None, extracted_data: Dict[str, Any] = None):
        """Delete input object and results prefixes from S3 after local persistence.
        - Deletes uploaded input image (input_s3_key)
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

        # 1) Delete input image
        _delete_key(input_s3_key)

        # 2) Delete orchestrator workflow results
        _delete_prefix(self.config.get_s3_key_for_result(workflow_id, ''))

        # 3) Delete DocumentProcessor result metadata path
        if result_uuid:
            _delete_prefix(self.config.get_s3_key_for_result(result_uuid, ''))

        # 4) Delete Bedrock clientToken results if we can infer it
        # Try to discover client token from extraction raw_response -> output_metadata paths
        try:
            raw = (extracted_data or {}).get('raw_response', {})
            client_token = None
            for segment in raw.get('output_metadata', []):
                for seg in segment.get('segment_metadata', []):
                    path = seg.get('custom_output_path') or ''
                    # path like s3://bucket/results/<clientToken>/... => extract folder name after results/
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

    def batch_process_workflows(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process multiple files in batch workflows
        
        Args:
            files: List of file dictionaries with 'bytes' and 'filename' keys
            
        Returns:
            List of workflow results
        """
        results = []
        
        self.logger.info(f"🚀 Starting batch processing of {len(files)} files")
        
        for i, file_info in enumerate(files):
            try:
                self.logger.info(f"📄 Processing file {i+1}/{len(files)}: {file_info['filename']}")
                
                result = self.process_passport_workflow(
                    file_info['bytes'], 
                    file_info['filename']
                )
                results.append(result)
                
                # Add small delay between files
                if i < len(files) - 1:
                    import time
                    time.sleep(0.5)
                
            except Exception as e:
                self.logger.error(f"Failed to process {file_info['filename']}: {e}")
                continue
        
        self.logger.info(f"✅ Batch processing completed. {len(results)}/{len(files)} files processed successfully")
        return results
    
    def get_workflow_stats(self) -> Dict[str, Any]:
        """Get comprehensive workflow statistics"""
        stats = self.workflow_stats.copy()
        stats['end_time'] = datetime.now()
        stats['duration'] = (stats['end_time'] - stats['start_time']).total_seconds()
        
        # Calculate success rate
        if stats['workflows_started'] > 0:
            stats['success_rate'] = (stats['workflows_completed'] / stats['workflows_started']) * 100
        else:
            stats['success_rate'] = 0
        
        # Add component statistics
        stats['document_processing_stats'] = self.document_processor.get_processing_stats()
        stats['bedrock_extraction_stats'] = self.bedrock_integrator.get_extraction_stats()
        
        return stats
    
    def create_workflow_report(self) -> Dict[str, Any]:
        """Create a comprehensive workflow report"""
        stats = self.get_workflow_stats()
        
        report = {
            'report_timestamp': datetime.now().isoformat(),
            'workflow_summary': {
                'total_workflows': stats['workflows_started'],
                'successful_workflows': stats['workflows_completed'],
                'failed_workflows': stats['workflows_failed'],
                'success_rate_percentage': stats['success_rate'],
                'total_duration_seconds': stats['duration']
            },
            'processing_metrics': {
                'documents_processed': stats['total_documents_processed'],
                'extractions_performed': stats['total_extractions_performed'],
                'average_workflow_duration': stats['duration'] / max(stats['workflows_started'], 1)
            },
            'component_performance': {
                'document_processor': stats['document_processing_stats'],
                'bedrock_integrator': stats['bedrock_extraction_stats']
            },
            'configuration_used': {
                's3_bucket': self.config.AWS_S3_BUCKET,
                'region': self.config.AWS_REGION,
                'blueprint_arn': self.config.BEDROCK_BLUEPRINT_ARN,
                'confidence_threshold': self.config.CONFIDENCE_THRESHOLD
            }
        }
        
        return report
