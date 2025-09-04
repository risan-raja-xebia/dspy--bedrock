"""
Configuration file for Robust Passport Processor
Enterprise-grade document processing workflow based on the flowchart design
"""

import os
from pathlib import Path
from typing import Dict, List, Any

class Config:
    """Main configuration class for the Robust Passport Processor"""
    
    # AWS Configuration
    AWS_REGION = "us-east-1"
    AWS_S3_BUCKET = "test-passport-data"
    AWS_S3_RESULTS_PREFIX = "results/"
    AWS_S3_IMAGES_PREFIX = "test_passport/"
    
    # Bedrock Configuration
    BEDROCK_BLUEPRINT_ARN = "arn:aws:bedrock:us-east-1:122610487956:blueprint/14e3e065923e"
    BEDROCK_BLUEPRINT_NAME = "passport"
    BEDROCK_BLUEPRINT_VERSION = "dev"
    
    # File Paths
    BASE_DIR = Path(__file__).parent.parent
    SRC_DIR = BASE_DIR / "src"
    TESTS_DIR = BASE_DIR / "tests"
    
    # Input/Output Configuration
    SUPPORTED_FORMATS = ['.jpg', '.jpeg', '.png', '.jfif', '.webp', '.bmp', '.tiff', '.pdf']
    MAX_FILE_SIZE_MB = 50
    BATCH_SIZE = 10
    
    # Processing Configuration
    CONFIDENCE_THRESHOLD = 0.7
    MAX_RETRIES = 3
    RETRY_DELAY_SECONDS = 5
    

    
    # UUID Configuration
    UUID_NAMESPACE = "passport-processing"
    
    # Field Mapping
    PASSPORT_FIELDS = [
        'country', 'documentType', 'surname', 'documentNumber',
        'issuingOffice', 'validFrom', 'forenames', 'validTo'
    ]
    
    # Color Configuration for Bounding Boxes
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
    
    @classmethod
    def get_s3_key_for_result(cls, uuid: str, filename: str) -> str:
        """Generate S3 key for result storage"""
        return f"{cls.AWS_S3_RESULTS_PREFIX}{uuid}/{filename}"
    
    @classmethod
    def get_s3_key_for_image(cls, filename: str) -> str:
        """Generate S3 key for image storage"""
        return f"{cls.AWS_S3_IMAGES_PREFIX}{filename}"
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate configuration settings"""
        required_dirs = [cls.SRC_DIR, cls.TESTS_DIR]
        
        for directory in required_dirs:
            if not directory.exists():
                directory.mkdir(parents=True, exist_ok=True)
        
        return True

# Simple configuration - no environment complexity
def get_config() -> Config:
    """Get the main configuration"""
    config = Config()
    config.validate_config()
    return config

# Default configuration
config = get_config()
