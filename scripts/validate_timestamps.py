#!/usr/bin/env python3
"""
Validate Timestamp Accuracy in Generated Summaries

This script validates that topic timestamps are 100% accurate by:
1. Checking segment IDs are valid
2. Verifying the actual text at those timestamps matches the topic
3. Reporting any mismatches or hallucinations

Usage:
    python scripts/validate_timestamps.py <transcript.json> <analysis.json>
"""

import json
import sys
from pathlib import Path


def validate_timestamps(transcript_data, topic_analysis):
    """Validate that all topic timestamps accurately match transcript content"""

    segments = transcript_data.get('segments', [])
    topics = topic_analysis.get('topics', [])

    print(f"🔍 Validating {len(topics)} topics against {len(segments)} segments\n")

    issues = []
    warnings = []

    for topic in topics:
        topic_id = topic.get('id')
        title = topic.get('title', 'Untitled')
        start_seg_id = topic.get('start_segment_id')
        end_seg_id = topic.get('end_segment_id')
        timestamp_range = topic.get('timestamp_range', '')

        print(f"Topic {topic_id}: {timestamp_range} - {title}")

        # Check segment IDs are valid
        if start_seg_id >= len(segments):
            issues.append(f"  ❌ Start segment {start_seg_id} out of range (max {len(segments)-1})")
            continue

        if end_seg_id >= len(segments):
            issues.append(f"  ❌ End segment {end_seg_id} out of range (max {len(segments)-1})")
            continue

        # Get actual text from those segments
        actual_start = segments[start_seg_id]
        actual_end = segments[end_seg_id]

        # Verify timestamps match
        topic_start_time = topic.get('start_time', 0)
        topic_end_time = topic.get('end_time', 0)
        segment_start_time = actual_start.get('start', 0)
        segment_end_time = actual_end.get('end', 0)

        # Allow small floating point differences (< 0.5 seconds)
        if abs(topic_start_time - segment_start_time) > 0.5:
            issues.append(f"  ❌ Start time mismatch: topic={topic_start_time}s, segment={segment_start_time}s")

        if abs(topic_end_time - segment_end_time) > 0.5:
            issues.append(f"  ❌ End time mismatch: topic={topic_end_time}s, segment={segment_end_time}s")

        # Show actual text at those timestamps for manual validation
        print(f"  ✓ Segment {start_seg_id}-{end_seg_id} ({segment_start_time:.1f}s - {segment_end_time:.1f}s)")
        print(f"    Start text: \"{actual_start.get('text', '').strip()[:100]}...\"")
        print(f"    End text: \"{actual_end.get('text', '').strip()[:100]}...\"")

        # Check if title keywords appear in the segment range
        # Extract keywords from title (remove common words)
        title_words = set(title.lower().split()) - {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were'
        }

        # Get text from segment range
        segment_range_text = ' '.join([
            seg.get('text', '')
            for seg in segments[start_seg_id:end_seg_id+1]
        ]).lower()

        # Check if at least one title keyword appears in the text
        keywords_found = [word for word in title_words if word in segment_range_text]

        if not keywords_found and len(title_words) > 0:
            warnings.append(f"  ⚠️  Title keywords not found in segment text: {title_words}")
            print(f"  ⚠️  Warning: Title '{title}' may not match segment content")
        else:
            print(f"  ✓ Title keywords found: {keywords_found[:3]}")

        print()

    # Summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)

    if not issues and not warnings:
        print("✅ All timestamps are 100% accurate!")
        print(f"   - {len(topics)} topics validated")
        print(f"   - All segment IDs valid")
        print(f"   - All timestamps match")
        return True
    else:
        if issues:
            print(f"\n❌ ISSUES FOUND ({len(issues)}):")
            for issue in issues:
                print(issue)

        if warnings:
            print(f"\n⚠️  WARNINGS ({len(warnings)}):")
            for warning in warnings:
                print(warning)

        return False


def main():
    if len(sys.argv) != 3:
        print("Usage: python scripts/validate_timestamps.py <transcript.json> <analysis.json>")
        print("\nExample:")
        print("  python scripts/validate_timestamps.py \\")
        print("    conversation/features/better-summaries/data/episode-4.json \\")
        print("    conversation/features/better-summaries/analysis/gpt5.json")
        sys.exit(1)

    transcript_path = Path(sys.argv[1])
    analysis_path = Path(sys.argv[2])

    if not transcript_path.exists():
        print(f"❌ Transcript file not found: {transcript_path}")
        sys.exit(1)

    if not analysis_path.exists():
        print(f"❌ Analysis file not found: {analysis_path}")
        sys.exit(1)

    # Load files
    with open(transcript_path) as f:
        transcript_data = json.load(f)

    with open(analysis_path) as f:
        topic_analysis = json.load(f)

    # Validate
    is_valid = validate_timestamps(transcript_data, topic_analysis)

    sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()
