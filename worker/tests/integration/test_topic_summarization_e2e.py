"""
Integration test for topic summarization feature
Tests full pipeline using production code paths
"""

import sys
import os
import pytest
from pathlib import Path
import shutil
import tempfile

# Add worker to path
worker_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(worker_dir))

from main import TranscriptionJobProcessor


class LocalTestProcessor(TranscriptionJobProcessor):
    """
    Extends production processor to work with local files
    Uses all the same code paths, just bypasses Dropbox
    """

    def __init__(self):
        """Initialize without Dropbox dependencies"""
        self.project_id = os.environ.get('PROJECT_ID', 'test-project')
        self.openai_api_key = os.environ.get('OPENAI_API_KEY')

        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable required")

        # Initialize OpenAI client (same as production)
        from openai import OpenAI
        self.openai_client = OpenAI(api_key=self.openai_api_key)


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get('OPENAI_API_KEY'),
    reason="OPENAI_API_KEY required for integration test"
)
def test_full_transcription_and_summarization_pipeline():
    """
    E2E test: Transcription + Topic Analysis + Summary Generation
    Uses production code paths from main.py
    """
    # Setup
    project_root = Path(__file__).parent.parent.parent.parent
    audio_file = project_root / "data/test-audio/large-test.m4a"
    output_dir = project_root / "data/test-output"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not audio_file.exists():
        pytest.skip(f"Test audio file not found: {audio_file}")

    print(f"\n{'='*60}")
    print(f"E2E TEST: Production Code Path")
    print(f"{'='*60}")
    print(f"📁 File: {audio_file.name}")
    print(f"📊 Size: {audio_file.stat().st_size / (1024 * 1024):.1f} MB")
    print(f"{'='*60}\n")

    # Initialize processor with production code
    processor = LocalTestProcessor()

    # Step 1: Prepare audio (production code)
    temp_dir = Path(tempfile.mkdtemp())
    temp_file = temp_dir / audio_file.name
    shutil.copy(audio_file, temp_file)

    print("STEP 1: AUDIO PREPARATION")
    print("-" * 60)
    audio_file_path = processor._prepare_audio_file(temp_file, audio_file.name)
    assert audio_file_path is not None, "Audio preparation failed"
    print(f"✅ Audio prepared: {audio_file_path.stat().st_size / (1024 * 1024):.1f} MB\n")

    # Step 2: Transcription (production code with chunking)
    print("STEP 2: TRANSCRIPTION (Production Path)")
    print("-" * 60)

    from transcripts.core.audio_chunker import AudioChunker

    if AudioChunker.should_chunk_file(audio_file_path):
        print(f"📦 File is large, using chunked transcription")
        transcript_result = processor._transcribe_audio_chunked(audio_file_path)
    else:
        print(f"🎙️ Using single-file transcription")
        transcript_result = processor._transcribe_audio(audio_file_path)

    assert transcript_result.get('success'), f"Transcription failed: {transcript_result.get('error')}"
    transcript_data = transcript_result['transcript_data']

    print(f"\n✅ Transcription complete!")
    print(f"   Segments: {len(transcript_data.get('segments', []))}")
    print(f"   Text length: {len(transcript_data.get('text', ''))} characters\n")

    # Verify transcript structure
    assert 'text' in transcript_data
    assert 'segments' in transcript_data
    assert 'duration' in transcript_data
    assert len(transcript_data['segments']) > 0

    # Step 3: Topic Analysis (production code)
    print("STEP 3: TOPIC ANALYSIS (Production Path)")
    print("-" * 60)

    sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))
    from transcripts.config import Config
    from transcripts.core.topic_analyzer import TopicAnalyzer
    from transcripts.core.summary_formatter import SummaryFormatter

    topic_analysis = None
    if Config.ENABLE_TOPIC_SUMMARIZATION:
        print("🔍 Generating topic analysis...")
        analyzer = TopicAnalyzer()
        topic_analysis = analyzer.analyze_transcript(transcript_data)
        print(f"✅ Topic analysis complete: {topic_analysis.get('metadata', {}).get('total_topics', 0)} topics\n")

        # Show topics
        print("📋 Topics identified:")
        for topic in topic_analysis.get('topics', []):
            print(f"   • {topic.get('timestamp_range')} {topic.get('title')}")
        print()

    # Verify topic analysis structure
    if topic_analysis:
        assert 'executive_summary' in topic_analysis
        assert 'topics' in topic_analysis
        assert 'metadata' in topic_analysis
        assert len(topic_analysis['topics']) > 0

        # Verify each topic has required fields
        for topic in topic_analysis['topics']:
            assert 'title' in topic
            assert 'timestamp_range' in topic
            assert 'start_time' in topic
            assert 'end_time' in topic
            assert 'summary' in topic

    # Step 4: Save outputs (production formatting)
    print("STEP 4: SAVING OUTPUTS (Production Formatting)")
    print("-" * 60)

    base_name = audio_file.stem
    import json
    from datetime import datetime

    # Save JSON
    json_path = output_dir / f"{base_name}.json"
    json_data = {
        **transcript_data,
        'original_file': audio_file.name,
        'processed_at': datetime.now().isoformat(),
        'status': 'completed'
    }
    if topic_analysis:
        json_data['topic_analysis'] = topic_analysis

    with open(json_path, 'w') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved: {json_path.name}")

    assert json_path.exists()

    # Save summary files
    if topic_analysis and topic_analysis.get('topics'):
        summary_txt_path = output_dir / f"{base_name}_SUMMARY.txt"
        summary_content = SummaryFormatter.format_summary_text(
            transcript_data, topic_analysis, audio_file.name
        )
        with open(summary_txt_path, 'w') as f:
            f.write(summary_content)
        print(f"✅ Saved: {summary_txt_path.name}")

        summary_md_path = output_dir / f"{base_name}_SUMMARY.md"
        summary_md_content = SummaryFormatter.format_summary_markdown(
            transcript_data, topic_analysis, audio_file.name
        )
        with open(summary_md_path, 'w') as f:
            f.write(summary_md_content)
        print(f"✅ Saved: {summary_md_path.name}")

        assert summary_txt_path.exists()
        assert summary_md_path.exists()
        assert len(summary_content) > 0

    # Cleanup
    if temp_file.exists():
        temp_file.unlink()
    if audio_file_path != temp_file and audio_file_path.exists():
        audio_file_path.unlink()
    if temp_dir.exists():
        shutil.rmtree(temp_dir)

    print(f"\n{'='*60}")
    print("TEST COMPLETE! ✅")
    print(f"{'='*60}")
    print(f"\nOutput directory: {output_dir.absolute()}/")
    print(f"\n📄 Files created:")
    for file in sorted(output_dir.glob(f"{base_name}*")):
        print(f"   • {file.name}")
