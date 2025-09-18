#!/usr/bin/env python3
"""Minimal pipeline test to identify issues"""

import os
import sys

# Set dummy keys to avoid hangs
os.environ['USE_SHEETS_SOURCES'] = 'false'
os.environ['OPENAI_API_KEY'] = 'sk-dummy-key'
os.environ['ELEVENLABS_API_KEY'] = 'dummy'
os.environ['SHOTSTACK_API_KEY'] = 'dummy'

print("=" * 80)
print("MINIMAL PIPELINE TEST")
print("=" * 80)

# Test imports
print("\n1. Testing imports...")
try:
    from src.editorial.story_analyzer import StoryAnalyzer
    print("   ✓ StoryAnalyzer")
except ImportError as e:
    print(f"   ✗ StoryAnalyzer: {e}")

try:
    from src.editorial.script_daily import ScriptGenerator
    print("   ✓ ScriptGenerator")
except ImportError as e:
    print(f"   ✗ ScriptGenerator: {e}")

try:
    from src.ingest.simple_sheets_manager import SimpleSheetsManager
    print("   ✓ SimpleSheetsManager")
except ImportError as e:
    print(f"   ✗ SimpleSheetsManager: {e}")

# Test script generation
print("\n2. Testing script generation...")
test_stories = [
    {
        'title': 'OpenAI Announces GPT-5',
        'summary': 'OpenAI has announced GPT-5 with breakthrough capabilities',
        'url': 'http://example.com/1',
        'source_domain': 'OpenAI Blog',
        'category': 'news',
        'full_text': 'OpenAI today announced GPT-5, featuring unprecedented reasoning abilities.'
    },
    {
        'title': 'Google Releases Gemini 2.0',
        'summary': 'Google unveils Gemini 2.0 with multimodal improvements',
        'url': 'http://example.com/2',
        'source_domain': 'Google AI Blog',
        'category': 'news',
        'full_text': 'Google has released Gemini 2.0, advancing multimodal AI capabilities.'
    }
]

try:
    from src.editorial.script_daily import ScriptGenerator
    generator = ScriptGenerator()
    result = generator.generate_script(test_stories)

    if result and result.get('vo_script'):
        print(f"   ✓ Script generated: {len(result['vo_script'])} chars")
        print(f"   ✓ Lower thirds: {len(result.get('lower_thirds', []))} items")
        print(f"   ✓ Keywords: {len(result.get('broll_keywords', []))} items")
    else:
        print("   ✗ Script generation failed")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test story analyzer
print("\n3. Testing story analyzer...")
try:
    analyzer = StoryAnalyzer()
    analyzed = analyzer.analyze_stories(test_stories)
    print(f"   ✓ Analyzed {len(analyzed)} stories")

    headlines = analyzer.extract_headlines(analyzed[:3])
    print(f"   ✓ Extracted {len(headlines)} headlines")
except Exception as e:
    print(f"   ✗ Error: {e}")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)

# If all tests pass, try the actual pipeline
if '--run-pipeline' in sys.argv:
    print("\n4. Running actual pipeline...")
    try:
        import unified_pipeline_test
        # This would run the actual pipeline
        print("   Pipeline module loaded - would run here")
    except Exception as e:
        print(f"   ✗ Pipeline error: {e}")