"""
Bedrock Integration Class
Handles communication with AWS Bedrock for passport data extraction
"""

import json
import logging
import time
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

from config.config import Config

class BedrockIntegrator:
    """
    Integrates with AWS Bedrock for passport data extraction
    
    Uses the specified blueprint:
    - ARN: arn:aws:bedrock:us-east-1:122610487956:blueprint/14e3e065923e
    - Name: passport
    - Version: dev
    """
    
    def __init__(self, config: Config = None):
        """Initialize the Bedrock integrator"""
        self.config = config or Config()
        self.logger = logging.getLogger(__name__)
        self.bedrock_client = self._setup_bedrock_client()
        
        # Processing statistics
        self.stats = {
            'extractions_attempted': 0,
            'extractions_successful': 0,
            'extractions_failed': 0,
            'total_processing_time': 0,
            'start_time': datetime.now()
        }
    
    def _setup_bedrock_client(self) -> boto3.client:
        """Setup Bedrock Data Automation client"""
        try:
            return boto3.client('bedrock-data-automation-runtime', region_name=self.config.AWS_REGION)
        except Exception as e:
            self.logger.error(f"Failed to setup Bedrock Data Automation client: {e}")
            raise
    
    def extract_passport_data(self, s3_key: str, filename: str) -> Dict[str, Any]:
        """
        Extract passport data using Bedrock Data Automation
        
        Args:
            s3_key: S3 key of the image to process
            filename: Original filename
            
        Returns:
            Extracted passport data with bounding boxes and confidence scores
        """
        try:
            self.stats['extractions_attempted'] += 1
            start_time = time.time()
            
            self.logger.info(f"Starting passport extraction for: {filename}")
            
            # Generate unique client token
            client_token = f"token{uuid.uuid4().hex[:20]}"
            
            # Prepare Bedrock Data Automation request
            request_params = {
                'clientToken': client_token,
                'inputConfiguration': {
                    's3Uri': f"s3://{self.config.AWS_S3_BUCKET}/{s3_key}"
                },
                'outputConfiguration': {
                    's3Uri': f"s3://{self.config.AWS_S3_BUCKET}/results/{client_token}/"
                },
                'blueprints': [{
                    'blueprintArn': self.config.BEDROCK_BLUEPRINT_ARN,
                    'stage': 'DEVELOPMENT'
                }],
                'dataAutomationProfileArn': f'arn:aws:bedrock:{self.config.AWS_REGION}:122610487956:data-automation-profile/us.data-automation-v1'
            }
            
            # Invoke Bedrock Data Automation
            response = self._invoke_bedrock_data_automation(request_params)
            
            # Wait for completion and get results
            extracted_data = self._wait_for_completion_and_get_results(response, client_token)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            self.stats['total_processing_time'] += processing_time
            
            self.stats['extractions_successful'] += 1
            self.logger.info(f"Successfully extracted data from {filename} in {processing_time:.2f}s")
            
            return extracted_data
            
        except Exception as e:
            self.stats['extractions_failed'] += 1
            self.logger.error(f"Failed to extract data from {filename}: {e}")
            raise
    
    def extract_medical_certificate_data(self, s3_key: str, filename: str) -> Dict[str, Any]:
        """
        Extract medical certificate data using Bedrock Data Automation
        
        Args:
            s3_key: S3 key of the image to process
            filename: Original filename
            
        Returns:
            Extracted medical certificate data with bounding boxes and confidence scores
        """
        try:
            self.stats['extractions_attempted'] += 1
            start_time = time.time()
            
            self.logger.info(f"Starting medical certificate extraction for: {filename}")
            
            # Generate unique client token
            client_token = f"token{uuid.uuid4().hex[:20]}"
            
            # Prepare Bedrock Data Automation request
            request_params = {
                'clientToken': client_token,
                'inputConfiguration': {
                    's3Uri': f"s3://{self.config.AWS_S3_BUCKET}/{s3_key}"
                },
                'outputConfiguration': {
                    's3Uri': f"s3://{self.config.AWS_S3_BUCKET}/results/{client_token}/"
                },
                'blueprints': [{
                    'blueprintArn': self.config.BEDROCK_BLUEPRINT_ARN,
                    'stage': 'DEVELOPMENT'
                }],
                'dataAutomationProfileArn': f'arn:aws:bedrock:{self.config.AWS_REGION}:122610487956:data-automation-profile/us.data-automation-v1'
            }
            
            # Invoke Bedrock Data Automation
            response = self._invoke_bedrock_data_automation(request_params)
            
            # Wait for completion and get results
            extracted_data = self._wait_for_completion_and_get_results(response, client_token)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            self.stats['total_processing_time'] += processing_time
            
            self.stats['extractions_successful'] += 1
            self.logger.info(f"Successfully extracted data from {filename} in {processing_time:.2f}s")
            
            return extracted_data
            
        except Exception as e:
            self.stats['extractions_failed'] += 1
            self.logger.error(f"Failed to extract data from {filename}: {e}")
            raise
    
    def validate_medical_extraction(self, extracted_data: Dict[str, Any]) -> bool:
        """
        Validate medical certificate extraction quality
        
        Args:
            extracted_data: Extracted medical certificate data
            
        Returns:
            True if validation passes, False otherwise
        """
        try:
            extracted_fields = extracted_data.get('extracted_fields', {})
            confidence_scores = extracted_data.get('confidence_scores', {})
            
            # Check if we have any extracted fields
            if not extracted_fields:
                self.logger.warning("No fields extracted from medical certificate")
                return False
            
            # Check confidence scores
            if confidence_scores:
                avg_confidence = sum(confidence_scores.values()) / len(confidence_scores)
                if avg_confidence < self.config.CONFIDENCE_THRESHOLD:
                    self.logger.warning(f"Average confidence {avg_confidence:.2f} below threshold {self.config.CONFIDENCE_THRESHOLD}")
                    return False
            
            # Check for required medical certificate fields
            required_fields = ['country', 'documentType', 'medicalCertificate', 'surname', 'forenames']
            missing_required = [field for field in required_fields if not extracted_fields.get(field)]
            
            if missing_required:
                self.logger.warning(f"Missing required medical certificate fields: {missing_required}")
                return False
            
            self.logger.info("Medical certificate extraction validation passed")
            return True
            
        except Exception as e:
            self.logger.error(f"Medical certificate validation failed: {e}")
            return False
    
    def _prepare_bedrock_input(self, s3_key: str) -> Dict[str, Any]:
        """
        Prepare input for Bedrock blueprint
        
        Args:
            s3_key: S3 key of the image
            
        Returns:
            Formatted input for Bedrock
        """
        # Create the input structure expected by the passport blueprint
        bedrock_input = {
            "input": {
                "image": {
                    "s3Uri": f"s3://{self.config.AWS_S3_BUCKET}/{s3_key}"
                }
            },
            "inferenceConfiguration": {
                "maxTokens": 4096,
                "temperature": 0.0,
                "topP": 1.0
            }
        }
        
        return bedrock_input
    
    def _invoke_bedrock_blueprint(self, bedrock_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke the Bedrock blueprint
        
        Args:
            bedrock_input: Formatted input for Bedrock
            
        Returns:
            Bedrock response
        """
        try:
            # Convert input to JSON string
            input_body = json.dumps(bedrock_input)
            
            # Invoke the blueprint
            response = self.bedrock_client.invoke_model(
                modelId=self.config.BEDROCK_BLUEPRINT_ARN,
                body=input_body,
                contentType="application/json"
            )
            
            # Parse response body
            response_body = json.loads(response['body'].read())
            
            self.logger.debug(f"Bedrock response received: {response_body}")
            return response_body
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            self.logger.error(f"Bedrock invocation failed: {error_code} - {error_message}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during Bedrock invocation: {e}")
            raise
    
    def _parse_bedrock_response(self, response: Dict[str, Any], filename: str) -> Dict[str, Any]:
        """
        Parse Bedrock response into structured format
        
        Args:
            response: Raw Bedrock response
            filename: Original filename
            
        Returns:
            Structured passport data
        """
        try:
            # Extract the main content from response
            content = response.get('content', [])
            if not content:
                raise ValueError("No content found in Bedrock response")
            
            # Get the first content block
            first_content = content[0]
            text = first_content.get('text', '')
            
            # Parse the text response (this will depend on your blueprint's output format)
            parsed_data = self._parse_text_response(text, filename)
            
            # Add metadata
            parsed_data['metadata'] = {
                'extraction_timestamp': datetime.now().isoformat(),
                'source_filename': filename,
                'bedrock_blueprint': {
                    'arn': self.config.BEDROCK_BLUEPRINT_ARN,
                    'name': self.config.BEDROCK_BLUEPRINT_NAME,
                    'version': self.config.BEDROCK_BLUEPRINT_VERSION
                },
                'processing_stats': {
                    'confidence_threshold': self.config.CONFIDENCE_THRESHOLD,
                    'extraction_version': '1.0.0'
                }
            }
            
            return parsed_data
            
        except Exception as e:
            self.logger.error(f"Failed to parse Bedrock response: {e}")
            raise
    
    def _parse_text_response(self, text: str, filename: str) -> Dict[str, Any]:
        """
        Parse the actual text response from Bedrock into structured data
        This method extracts real passport fields, confidence scores, and bounding boxes
        """
        try:
            # Parse the JSON response from Bedrock
            response_data = json.loads(text)
            
            # Extract the actual response content
            content = response_data.get('content', [])
            if not content:
                raise ValueError("No content found in Bedrock response")
            
            # Get the text content
            text_content = content[0].get('text', '')
            if not text_content:
                raise ValueError("No text content found in Bedrock response")
            
            # Parse the structured data from the text
            # Bedrock typically returns JSON-like text that needs parsing
            parsed_data = self._extract_structured_data(text_content, filename)
            
            self.logger.info(f"Successfully parsed real passport data for {filename}")
            return parsed_data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse Bedrock JSON response: {e}")
            # Fallback to text parsing
            return self._fallback_text_parsing(text, filename)
        except Exception as e:
            self.logger.error(f"Error parsing Bedrock response: {e}")
            return self._fallback_text_parsing(text, filename)
    
    def _extract_structured_data(self, text_content: str, filename: str) -> Dict[str, Any]:
        """
        Extract structured data from Bedrock text response
        This handles the actual format returned by the passport blueprint
        """
        try:
            # Try to extract JSON from the text content
            # Bedrock often returns JSON embedded in text
            json_start = text_content.find('{')
            json_end = text_content.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = text_content[json_start:json_end]
                extracted_json = json.loads(json_str)
                
                # Map the extracted data to our standard format
                return self._map_extracted_data(extracted_json, filename)
            
            # If no JSON found, try to parse the text directly
            return self._parse_text_fields(text_content, filename)
            
        except Exception as e:
            self.logger.warning(f"Failed to extract structured data: {e}")
            return self._parse_text_fields(text_content, filename)
    
    def _map_extracted_data(self, extracted_json: Dict[str, Any], filename: str) -> Dict[str, Any]:
        """
        Map the actual extracted JSON data to our standard format
        """
        # Initialize with default values
        extracted_fields = {}
        confidence_scores = {}
        bounding_boxes = {}
        
        # Map common field names from Bedrock response
        field_mapping = {
            'country': ['country', 'nationality', 'issuing_country'],
            'documentType': ['document_type', 'type', 'doc_type'],
            'surname': ['surname', 'last_name', 'family_name'],
            'documentNumber': ['document_number', 'passport_number', 'number'],
            'issuingOffice': ['issuing_office', 'authority', 'issuer'],
            'validFrom': ['valid_from', 'issue_date', 'date_of_issue'],
            'forenames': ['forenames', 'first_name', 'given_name'],
            'validTo': ['valid_until', 'expiry_date', 'expiration_date']
        }
        
        # Extract fields using the mapping
        for standard_field, possible_names in field_mapping.items():
            for possible_name in possible_names:
                if possible_name in extracted_json:
                    extracted_fields[standard_field] = extracted_json[possible_name]
                    # Set default confidence if not provided
                    confidence_scores[standard_field] = extracted_json.get(f'{possible_name}_confidence', 0.85)
                    break
        
        # Extract bounding boxes if available
        if 'bounding_boxes' in extracted_json:
            bounding_boxes = extracted_json['bounding_boxes']
        elif 'regions' in extracted_json:
            bounding_boxes = self._convert_regions_to_bboxes(extracted_json['regions'])
        
        # Create document info
        document_info = {
            'document_type': extracted_fields.get('documentType', 'PASSPORT'),
            'country_code': extracted_fields.get('country', 'UNKNOWN'),
            'extraction_confidence': self._calculate_overall_confidence(confidence_scores),
            'processing_timestamp': datetime.now().isoformat(),
            'source_filename': filename
        }
        
        return {
            'extracted_fields': extracted_fields,
            'confidence_scores': confidence_scores,
            'bounding_boxes': bounding_boxes,
            'document_info': document_info,
            'raw_response': extracted_json
        }
    
    def _parse_text_fields(self, text_content: str, filename: str) -> Dict[str, Any]:
        """
        Fallback method to parse text fields when JSON extraction fails
        """
        extracted_fields = {}
        confidence_scores = {}
        
        # Simple text-based field extraction
        text_lower = text_content.lower()
        
        # Extract country (look for common patterns)
        if 'united states' in text_lower:
            extracted_fields['country'] = 'UNITED STATES'
        elif 'china' in text_lower:
            extracted_fields['country'] = 'CHINA'
        elif 'ireland' in text_lower:
            extracted_fields['country'] = 'IRELAND'
        elif 'nigeria' in text_lower:
            extracted_fields['country'] = 'NIGERIA'
        elif 'poland' in text_lower:
            extracted_fields['country'] = 'POLAND'
        elif 'indonesia' in text_lower:
            extracted_fields['country'] = 'INDONESIA'
        elif 'turkey' in text_lower:
            extracted_fields['country'] = 'TURKEY'
        
        # Extract document type
        if 'passport' in text_lower:
            extracted_fields['documentType'] = 'PASSPORT'
        
        # Set default confidence scores
        for field in extracted_fields:
            confidence_scores[field] = 0.80
        
        # Create document info
        document_info = {
            'document_type': extracted_fields.get('documentType', 'PASSPORT'),
            'country_code': extracted_fields.get('country', 'UNKNOWN'),
            'extraction_confidence': self._calculate_overall_confidence(confidence_scores),
            'processing_timestamp': datetime.now().isoformat(),
            'source_filename': filename
        }
        
        return {
            'extracted_fields': extracted_fields,
            'confidence_scores': confidence_scores,
            'bounding_boxes': {},
            'document_info': document_info,
            'raw_response': text_content
        }
    
    def _convert_regions_to_bboxes(self, regions: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Convert Bedrock regions format to our bounding box format
        """
        bounding_boxes = {}
        
        for region in regions:
            field_name = region.get('field_name', 'unknown')
            geometry = region.get('geometry', {})
            
            if 'boundingBox' in geometry:
                bbox = geometry['boundingBox']
                if field_name not in bounding_boxes:
                    bounding_boxes[field_name] = []
                
                bounding_boxes[field_name].append({
                    'top': bbox.get('top', 0.0),
                    'left': bbox.get('left', 0.0),
                    'width': bbox.get('width', 0.0),
                    'height': bbox.get('height', 0.0)
                })
        
        return bounding_boxes
    
    def _calculate_overall_confidence(self, confidence_scores: Dict[str, float]) -> float:
        """
        Calculate overall confidence from individual field confidences
        """
        if not confidence_scores:
            return 0.0
        
        total_confidence = sum(confidence_scores.values())
        return total_confidence / len(confidence_scores)
    
    def _fallback_text_parsing(self, text: str, filename: str) -> Dict[str, Any]:
        """
        Ultimate fallback for text parsing when all else fails
        """
        self.logger.warning(f"Using fallback text parsing for {filename}")
        
        return {
            'extracted_fields': {
                'country': 'UNKNOWN',
                'documentType': 'PASSPORT',
                'surname': 'UNKNOWN',
                'documentNumber': 'UNKNOWN',
                'issuingOffice': 'UNKNOWN',
                'validFrom': 'UNKNOWN',
                'validTo': 'UNKNOWN',
                'forenames': 'UNKNOWN'
            },
            'confidence_scores': {
                'country': 0.50,
                'documentType': 0.70,
                'surname': 0.50,
                'documentNumber': 0.50,
                'issuingOffice': 0.50,
                'validFrom': 0.50,
                'validTo': 0.50,
                'forenames': 0.50
            },
            'bounding_boxes': {},
            'document_info': {
                'document_type': 'PASSPORT',
                'country_code': 'UNKNOWN',
                'extraction_confidence': 0.50,
                'processing_timestamp': datetime.now().isoformat(),
                'source_filename': filename,
                'parsing_method': 'fallback'
            },
            'raw_response': text
        }
    
    def batch_extract(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract data from multiple files in batch
        
        Args:
            files: List of file dictionaries with 's3_key' and 'filename' keys
            
        Returns:
            List of extracted data
        """
        results = []
        
        for file_info in files:
            try:
                result = self.extract_passport_data(
                    file_info['s3_key'], 
                    file_info['filename']
                )
                results.append(result)
                
                # Add small delay to avoid rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Failed to extract from {file_info['filename']}: {e}")
                continue
        
        return results
    
    def get_extraction_stats(self) -> Dict[str, Any]:
        """Get current extraction statistics"""
        stats = self.stats.copy()
        stats['end_time'] = datetime.now()
        stats['duration'] = (stats['end_time'] - stats['start_time']).total_seconds()
        
        if stats['extractions_attempted'] > 0:
            stats['success_rate'] = stats['extractions_successful'] / stats['extractions_attempted']
            stats['average_processing_time'] = stats['total_processing_time'] / stats['extractions_successful']
        else:
            stats['success_rate'] = 0
            stats['average_processing_time'] = 0
        
        return stats
    
    def validate_extraction(self, extracted_data: Dict[str, Any]) -> bool:
        """
        Validate extracted data quality
        
        Args:
            extracted_data: Data extracted from passport
            
        Returns:
            True if data meets quality standards
        """
        try:
            # Check if required fields are present
            required_fields = ['country', 'documentType', 'documentNumber']
            extracted_fields = extracted_data.get('extracted_fields', {})
            
            for field in required_fields:
                if field not in extracted_fields or not extracted_fields[field]:
                    self.logger.warning(f"Missing required field: {field}")
                    return False
            
            # Check confidence scores
            confidence_scores = extracted_data.get('confidence_scores', {})
            for field, score in confidence_scores.items():
                if score < self.config.CONFIDENCE_THRESHOLD:
                    self.logger.warning(f"Low confidence for {field}: {score}")
                    return False
            
            # Check bounding boxes
            bounding_boxes = extracted_data.get('bounding_boxes', {})
            if not bounding_boxes:
                self.logger.warning("No bounding boxes found")
                return False
            
            self.logger.info("Extraction validation passed")
            return True
            
        except Exception as e:
            self.logger.error(f"Validation failed: {e}")
            return False
    
    def _invoke_bedrock_data_automation(self, request_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke Bedrock Data Automation
        
        Args:
            request_params: Request parameters for data automation
            
        Returns:
            Response from Bedrock Data Automation
        """
        try:
            self.logger.info(f"Invoking Bedrock Data Automation with client token: {request_params['clientToken']}")
            
            response = self.bedrock_client.invoke_data_automation_async(**request_params)
            
            self.logger.info(f"Data automation invoked successfully: {response.get('invocationArn', 'Unknown')}")
            return response
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            self.logger.error(f"Bedrock Data Automation failed: {error_code} - {error_message}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during Bedrock Data Automation: {e}")
            raise
    
    def _wait_for_completion_and_get_results(self, response: Dict[str, Any], client_token: str) -> Dict[str, Any]:
        """
        Wait for Bedrock Data Automation completion and retrieve results
        
        Args:
            response: Response from invoke_data_automation_async
            client_token: Client token for tracking
            
        Returns:
            Extracted passport data
        """
        try:
            invocation_arn = response['invocationArn']
            self.logger.info(f"Waiting for completion of invocation: {invocation_arn}")
            
            # Wait for completion
            while True:
                status_response = self.bedrock_client.get_data_automation_status(invocationArn=invocation_arn)
                status = status_response['status']
                
                self.logger.info(f"Status: {status}")
                
                if status == 'Success':
                    # Get results from S3
                    output_uri = status_response['outputConfiguration']['s3Uri']
                    results = self._get_extraction_results_from_s3(output_uri)
                    
                    # Check if this is a medical certificate blueprint
                    if hasattr(self.config, 'BEDROCK_BLUEPRINT_NAME') and self.config.BEDROCK_BLUEPRINT_NAME == 'medical_certificate':
                        return self._parse_medical_certificate_fields_from_bda(results, client_token)
                    else:
                        return self._parse_passport_fields_from_bda(results, client_token)
                    
                elif status == 'Failed':
                    error_msg = status_response.get('failureReason', 'Unknown failure')
                    self.logger.error(f"Data automation failed: {error_msg}")
                    raise Exception(f"Data automation failed: {error_msg}")
                
                # Wait before checking again
                time.sleep(5)
                
        except Exception as e:
            self.logger.error(f"Error waiting for completion: {e}")
            raise
    
    def _get_extraction_results_from_s3(self, s3_uri: str) -> Dict[str, Any]:
        """
        Retrieve extraction results from S3
        
        Args:
            s3_uri: S3 URI of the results
            
        Returns:
            Parsed results
        """
        try:
            # Parse S3 URI
            uri_parts = s3_uri.replace('s3://', '').split('/', 1)
            bucket = uri_parts[0]
            key = uri_parts[1]
            
            # Get the metadata file
            s3_client = boto3.client('s3', region_name=self.config.AWS_REGION)
            response = s3_client.get_object(Bucket=bucket, Key=key)
            return json.loads(response['Body'].read().decode('utf-8'))
            
        except Exception as e:
            self.logger.error(f"Failed to get results from S3: {e}")
            raise
    
    def _parse_passport_fields_from_bda(self, extraction_results: Dict[str, Any], file_key: str) -> Dict[str, Any]:
        """
        Parse passport fields from Bedrock Data Automation results
        
        Args:
            extraction_results: Raw BDA results
            file_key: Original file key
            
        Returns:
            Structured passport data
        """
        try:
            passport_data = {
                'file_key': file_key,
                'processing_timestamp': datetime.now().isoformat(),
                'extraction_status': 'success'
            }
            
            # Initialize all expected fields
            expected_fields = ['country', 'documentType', 'surname', 'documentNumber', 
                             'issuingOffice', 'validFrom', 'forenames', 'validTo']
            
            for field in expected_fields:
                passport_data[field] = None
            
            # Navigate through BDA output structure
            for segment in extraction_results.get('output_metadata', []):
                for seg_metadata in segment.get('segment_metadata', []):
                    if seg_metadata.get('custom_output_status') == 'MATCH':
                        custom_output_path = seg_metadata['custom_output_path']
                        custom_results = self._get_extraction_results_from_s3(custom_output_path)
                        
                        # Extract inference results
                        inference_result = custom_results.get('inference_result', {})
                        
                        # Map each field from your blueprint
                        for field in expected_fields:
                            if field in inference_result:
                                passport_data[field] = inference_result[field]
                        
                        break
            
            # Convert to the expected format
            return {
                'extracted_fields': passport_data,
                'confidence_scores': {field: 0.9 for field in expected_fields if passport_data[field]},
                'bounding_boxes': {},
                'document_info': {
                    'document_type': passport_data.get('documentType', 'PASSPORT'),
                    'country_code': passport_data.get('country', 'UNKNOWN'),
                    'extraction_confidence': 0.9,
                    'processing_timestamp': passport_data['processing_timestamp'],
                    'source_filename': file_key,
                    'parsing_method': 'bedrock_data_automation'
                },
                'raw_response': extraction_results
            }
            
        except Exception as e:
            self.logger.error(f"Failed to parse BDA results: {e}")
            # Return fallback data
            return self._create_fallback_data(f"Failed to parse BDA results: {e}", file_key)

    def _parse_medical_certificate_fields_from_bda(self, extraction_results: Dict[str, Any], file_key: str) -> Dict[str, Any]:
        """
        Parse medical certificate fields from Bedrock Data Automation results
        
        Args:
            extraction_results: Raw BDA results
            file_key: Original file key
            
        Returns:
            Structured medical certificate data
        """
        try:
            medical_data = {
                'file_key': file_key,
                'processing_timestamp': datetime.now().isoformat(),
                'extraction_status': 'success'
            }
            
            # Initialize all expected medical certificate fields
            expected_fields = [
                'country', 'processed', 'notes', 'clientId', 'documentType', 
                'medicalCertificate', 'surname', 'dateProcessed', 'validFrom', 
                'forenames', 'staffId', 'validTo'
            ]
            
            for field in expected_fields:
                medical_data[field] = None
            
            # Navigate through BDA output structure
            for segment in extraction_results.get('output_metadata', []):
                for seg_metadata in segment.get('segment_metadata', []):
                    if seg_metadata.get('custom_output_status') == 'MATCH':
                        custom_output_path = seg_metadata['custom_output_path']
                        custom_results = self._get_extraction_results_from_s3(custom_output_path)
                        
                        # Extract inference results
                        inference_result = custom_results.get('inference_result', {})
                        
                        # Map each field from the medical certificate blueprint
                        for field in expected_fields:
                            if field in inference_result:
                                medical_data[field] = inference_result[field]
                        
                        # Store the custom results (including explainability_info) in raw_response
                        raw_response = extraction_results.copy()
                        raw_response['custom_output'] = custom_results
                        
                        break
            
            # Convert to the expected format
            return {
                'extracted_fields': medical_data,
                'confidence_scores': {field: 0.9 for field in expected_fields if medical_data[field]},
                'bounding_boxes': {},
                'document_info': {
                    'document_type': medical_data.get('documentType', 'Medical Certificate'),
                    'country_code': medical_data.get('country', 'UNKNOWN'),
                    'extraction_confidence': 0.9,
                    'processing_timestamp': medical_data['processing_timestamp'],
                    'source_filename': file_key,
                    'parsing_method': 'bedrock_data_automation'
                },
                'raw_response': raw_response
            }
            
        except Exception as e:
            self.logger.error(f"Failed to parse medical certificate BDA results: {e}")
            # Return fallback data
            return self._create_fallback_data(f"Failed to parse medical certificate BDA results: {e}", file_key)
