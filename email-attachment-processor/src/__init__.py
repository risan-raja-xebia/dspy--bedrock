"""
Email Attachment Processor - Core Processing Modules
"""

__version__ = "1.0.0"
__author__ = "Document Processing Team"

# Core modules
from .document_processor import DocumentProcessor
from .bedrock_integrator import BedrockIntegrator
from .passport_orchestrator import PassportOrchestrator
from .unified_medical_pipeline import UnifiedMedicalPipeline
from .medical_highlight_visualizer import MedicalHighlightVisualizer

__all__ = [
    'DocumentProcessor',
    'BedrockIntegrator', 
    'PassportOrchestrator',
    'UnifiedMedicalPipeline',
    'MedicalHighlightVisualizer'
]
