#!/usr/bin/env python3
"""
Generate Email Summary HTML for Testing and Validation

This script generates the exact same email summary HTML that users receive in production.
It uses the production code from worker/src/transcripts/core/ with no duplication.

Purpose:
    - Test different AI models (GPT-5, GPT-4o, etc.) for summary quality
    - Validate timestamp accuracy before deploying changes
    - Compare summaries side-by-side in candidates/ folder
    - Preview what users will receive

Requirements:
    - OpenAI API key (set OPENAI_API_KEY env var or use --api-key)
    - Transcript JSON file (must have 'text', 'segments', 'duration' fields)
    - Python packages: openai (from worker requirements)

Usage Examples (run from project root):

    # Basic usage with GPT-5
    python scripts/generate_summary_email.py conversation/features/better-summaries/data/episode-4.json -o conversation/features/better-summaries/candidates/gpt5.html -m gpt-5

    # Compare multiple models
    for model in gpt-5 gpt-4o gpt-4o-mini; do
        python scripts/generate_summary_email.py conversation/features/better-summaries/data/episode-4.json -o conversation/features/better-summaries/candidates/$model.html -m $model
    done

    # Use environment variable for model
    export OPENAI_SUMMARIZATION_MODEL=gpt-5
    python scripts/generate_summary_email.py conversation/features/better-summaries/data/episode-4.json -o conversation/features/better-summaries/candidates/default.html

    # View in browser after generation
    python scripts/generate_summary_email.py input.json -o output.html -m gpt-5
    open output.html

Output:
    - HTML file with the exact email users receive
    - Timestamp validation printed to console
    - Summary statistics (topics, action items, decisions)

What It Uses (Production Code):
    - worker/src/transcripts/core/topic_analyzer.py - AI analysis
    - worker/src/transcripts/core/html_email_template.py - Email generation
    - worker/src/transcripts/config.py - Configuration defaults
"""

import json
import sys
import argparse
from pathlib import Path

# Add worker source to path to import production code
worker_src = Path(__file__).parent.parent / "worker" / "src"
sys.path.insert(0, str(worker_src))

from transcripts.core.topic_analyzer import TopicAnalyzer
from transcripts.core.html_email_template import HTMLEmailTemplate


def main():
    parser = argparse.ArgumentParser(
        description='Generate email summary HTML from transcript JSON',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate with default model
  %(prog)s input.json -o output.html

  # Generate with specific model
  %(prog)s input.json -o candidates/gpt5.html -m gpt-5-mini

  # Use episode-4 example
  %(prog)s conversation/features/better-summaries/data/episode-4.json \\
    -o conversation/features/better-summaries/candidates/gpt5.html \\
    -m gpt-5-mini
        """
    )

    parser.add_argument(
        'input_json',
        type=Path,
        help='Path to transcript JSON file'
    )

    parser.add_argument(
        '-o', '--output',
        type=Path,
        required=True,
        help='Output path for HTML email (e.g., candidates/gpt5.html)'
    )

    parser.add_argument(
        '-m', '--model',
        type=str,
        help='OpenAI model to use (default: from OPENAI_SUMMARIZATION_MODEL env var or config default)'
    )

    parser.add_argument(
        '--api-key',
        type=str,
        help='OpenAI API key (default: from OPENAI_API_KEY env var)'
    )

    args = parser.parse_args()

    # Validate input file exists
    if not args.input_json.exists():
        print(f"❌ Input file not found: {args.input_json}")
        sys.exit(1)

    # Load transcript data
    print(f"📂 Loading transcript from: {args.input_json}")
    with open(args.input_json, 'r') as f:
        transcript_data = json.load(f)

    print(f"✅ Loaded transcript:")
    print(f"   - Segments: {len(transcript_data.get('segments', []))}")
    print(f"   - Duration: {transcript_data.get('duration', 'unknown')}s")
    print(f"   - Text length: {len(transcript_data.get('text', ''))} characters")

    # Get API key
    import os
    api_key = args.api_key or os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print("❌ OpenAI API key required. Set OPENAI_API_KEY env var or use --api-key")
        sys.exit(1)

    # Initialize analyzer with production code
    print(f"\n🔧 Initializing TopicAnalyzer...")
    if args.model:
        print(f"   Using model: {args.model}")
        analyzer = TopicAnalyzer(api_key=api_key, model=args.model)
    else:
        print(f"   Using model from config/env")
        analyzer = TopicAnalyzer(api_key=api_key)

    # Run analysis using production code
    print(f"\n🚀 Analyzing transcript (this may take 1-2 minutes)...")
    topic_analysis = analyzer.analyze_transcript(transcript_data)

    # Check for errors
    if topic_analysis.get('metadata', {}).get('error'):
        print(f"❌ Analysis failed: {topic_analysis['metadata']['error']}")
        sys.exit(1)

    print(f"\n✅ Analysis complete!")
    print(f"   - Quotes identified: {len(topic_analysis.get('quotes', []))}")
    print(f"   - Standalone snippets: {len(topic_analysis.get('reel_snippets_standalone', []))}")
    print(f"   - Context snippets: {len(topic_analysis.get('reel_snippets_context', []))}")
    print(f"   - Model used: {topic_analysis.get('metadata', {}).get('model_used', 'unknown')}")

    # Print first few quotes for quick validation
    print(f"\n📊 First 3 quotes:")
    for i, quote in enumerate(topic_analysis.get('quotes', [])[:3], 1):
        print(f"   {i}. \"{quote}\"")

    # Generate HTML email using production code
    print(f"\n📧 Generating email HTML using production template...")

    # Use the original filename from the JSON or input path
    original_filename = args.input_json.stem + args.input_json.suffix

    # Mock dropbox links (not needed for validation)
    dropbox_links = {
        'summary_share_url': '#',
        'txt_share_url': '#'
    }

    html_email = HTMLEmailTemplate.generate_summary_email(
        transcript_data=transcript_data,
        topic_analysis=topic_analysis,
        original_file_name=original_filename,
        dropbox_links=dropbox_links
    )

    # Create output directory if needed
    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Save HTML to file
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(html_email)

    print(f"\n✅ Email HTML saved to: {args.output}")

    # Also save the analysis JSON for validation
    analysis_output = args.output.with_suffix('.json')
    with open(analysis_output, 'w', encoding='utf-8') as f:
        json.dump(topic_analysis, f, indent=2)

    print(f"✅ Analysis JSON saved to: {analysis_output}")

    print(f"\n💡 Open in browser to review:")
    print(f"   open {args.output}")

    # Summary stats
    quotes = topic_analysis.get('quotes', [])
    standalone = topic_analysis.get('reel_snippets_standalone', [])
    context = topic_analysis.get('reel_snippets_context', [])

    print(f"\n📈 Summary stats:")
    print(f"   Quotes: {len(quotes)}")
    print(f"   Standalone Snippets: {len(standalone)}")
    print(f"   Context Snippets: {len(context)}")


if __name__ == "__main__":
    main()
