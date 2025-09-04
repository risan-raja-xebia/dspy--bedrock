#!/usr/bin/env python3

import sys
from pathlib import Path
import logging

sys.path.append(str(Path(__file__).parent))

from config.config import Config
from src.passport_orchestrator import PassportOrchestrator

def main():
    print("🚀 Starting Passport Processing Pipeline")
    print("=" * 60)
    
    try:
        config = Config()
        orchestrator = PassportOrchestrator(config)
        
        print("⚙️ Initializing configuration...")
        print(f"📦 S3 Bucket: {config.AWS_S3_BUCKET}")
        print(f"🤖 Bedrock Blueprint: {config.BEDROCK_BLUEPRINT_ARN}")
        print(f"🌍 AWS Region: {config.AWS_REGION}")
        
        print("\n📄 Loading passport images...")
        data_dir = Path("../dataAutomation-bedrock/test_passport")
        
        if not data_dir.exists():
            print(f"❌ Passport images directory not found: {data_dir}")
            return
        
        image_files = list(data_dir.glob("*"))
        image_files = [f for f in image_files if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.jfif', '.webp', '.bmp', '.tiff']]
        
        if not image_files:
            print(f"❌ No image files found in: {data_dir}")
            return
        
        print(f"📄 Found {len(image_files)} passport images")
        
        files = []
        for img_file in image_files:
            with open(img_file, 'rb') as f:
                files.append({
                    'filename': img_file.name,
                    'bytes': f.read(),
                    'size': img_file.stat().st_size
                })
            print(f"✅ Loaded: {img_file.name} ({img_file.stat().st_size} bytes)")
        
        print(f"\n📊 Processing {len(files)} passport images...")
        print("-" * 60)
        
        results = orchestrator.batch_process_workflows(files)
        
        print("\n" + "=" * 60)
        print("📊 PIPELINE STATISTICS")
        print("=" * 60)
        
        stats = orchestrator.get_statistics()
        print(f"🚀 Total Workflows Started: {stats['total_workflows_started']}")
        print(f"✅ Successful Workflows: {stats['successful_workflows']}")
        print(f"❌ Failed Workflows: {stats['failed_workflows']}")
        print(f"📈 Success Rate: {stats['success_rate']:.2f}%")
        print(f"⏱️ Total Duration: {stats['total_duration']:.2f} seconds")
        
        print(f"\n📄 Documents Processed: {stats['total_documents_processed']}")
        print(f"🤖 Extractions Performed: {stats['total_extractions_performed']}")
        print(f"🎨 Bounding Boxes Created: {stats['total_bounding_boxes_created']}")
        
        print(f"\n📋 INDIVIDUAL RESULTS SUMMARY:")
        print("-" * 60)
        
        for i, result in enumerate(results, 1):
            workflow_id = result.get('workflow_id', 'unknown')
            filename = result.get('document_processing', {}).get('s3_key', 'unknown')
            success = result.get('success', False)
            validation_passed = result.get('validation_passed', False)
            cleanup_success = result.get('s3_cleanup', {}).get('success', False)
            
            status = "✅ SUCCESS" if success else "❌ FAILED"
            validation_status = "✅ PASSED" if validation_passed else "⚠️ WARNINGS"
            cleanup_status = "🧹 CLEANED" if cleanup_success else "⚠️ CLEANUP ISSUE"
            
            print(f"{i:2d}. {status} | {validation_status} | {cleanup_status} | {workflow_id[:12]} | {Path(filename).name}")
        
        print("\n🎉 Passport Processing Pipeline completed successfully!")
        
    except Exception as e:
        print(f"❌ Pipeline failed with error: {e}")

if __name__ == "__main__":
    main()
