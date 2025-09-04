#!/usr/bin/env python3

import sys
from pathlib import Path
import logging

sys.path.append(str(Path(__file__).parent))

from config.config import Config
from src.unified_medical_pipeline import UnifiedMedicalPipeline

def main():
    print("🚀 Starting Medical Certificate Processing Pipeline")
    print("=" * 60)
    
    try:
        config = Config()
        pipeline = UnifiedMedicalPipeline(config)
        
        print("⚙️ Initializing configuration...")
        print(f"📦 S3 Bucket: {config.AWS_S3_BUCKET}")
        print(f"🤖 Bedrock Blueprint: {config.BEDROCK_BLUEPRINT_ARN}")
        print(f"🌍 AWS Region: {config.AWS_REGION}")
        
        print("\n📄 Loading medical certificates...")
        data_dir = Path("../dataAutomation-bedrock/medical_certificates")
        
        if not data_dir.exists():
            print(f"❌ Medical certificates directory not found: {data_dir}")
            return
        
        pdf_files = list(data_dir.glob("*.pdf"))
        
        if not pdf_files:
            print(f"❌ No PDF files found in: {data_dir}")
            return
        
        print(f"📄 Found {len(pdf_files)} medical certificate PDF files")
        
        files = []
        for pdf_file in pdf_files:
            with open(pdf_file, 'rb') as f:
                files.append({
                    'filename': pdf_file.name,
                    'bytes': f.read(),
                    'size': pdf_file.stat().st_size
                })
            print(f"✅ Loaded: {pdf_file.name} ({pdf_file.stat().st_size} bytes)")
        
        print(f"\n📊 Processing {len(files)} medical certificates...")
        print("-" * 60)
        
        results = pipeline.batch_process_documents(files)
        
        print("\n" + "=" * 60)
        print("📊 PIPELINE STATISTICS")
        print("=" * 60)
        
        stats = pipeline.get_pipeline_stats()
        print(f"🚀 Total Pipelines Started: {stats['pipelines_started']}")
        print(f"✅ Successful Pipelines: {stats['pipelines_completed']}")
        print(f"❌ Failed Pipelines: {stats['pipelines_failed']}")
        print(f"📈 Success Rate: {stats['success_rate']:.2f}%")
        print(f"⏱️ Total Duration: {stats['total_duration']:.2f} seconds")
        
        print(f"\n📄 Documents Processed: {stats['total_documents_processed']}")
        print(f"🤖 Extractions Performed: {stats['total_extractions_performed']}")
        print(f"🎨 Highlights Created: {stats['total_highlights_created']}")
        
        print(f"\n📋 INDIVIDUAL RESULTS SUMMARY:")
        print("-" * 60)
        
        for i, result in enumerate(results, 1):
            pipeline_id = result.get('pipeline_id', 'unknown')
            filename = result.get('document_processing', {}).get('s3_key', 'unknown')
            success = result.get('success', False)
            validation_passed = result.get('validation_passed', False)
            cleanup_success = result.get('s3_cleanup', {}).get('success', False)
            
            status = "✅ SUCCESS" if success else "❌ FAILED"
            validation_status = "✅ PASSED" if validation_passed else "⚠️ WARNINGS"
            cleanup_status = "🧹 CLEANED" if cleanup_success else "⚠️ CLEANUP ISSUE"
            
            print(f"{i:2d}. {status} | {validation_status} | {cleanup_status} | {pipeline_id[:12]} | {Path(filename).name}")
        
        print("\n🎉 Medical Certificate Processing Pipeline completed successfully!")
        
    except Exception as e:
        print(f"❌ Pipeline failed with error: {e}")

if __name__ == "__main__":
    main()
