"""
Smoke tests for API key validation.
Fast (~10 second) tests that verify API keys work through production code paths.
Costs <$0.01 total per run.
"""

import sys
import os
import pytest
from pathlib import Path

# Add worker/src to path for imports
worker_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(worker_dir / "src"))


# --- Helpers ---

def has_openai_key():
    return bool(os.environ.get("OPENAI_API_KEY"))


def has_anthropic_key():
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


SKIP_NO_OPENAI = pytest.mark.skipif(
    not has_openai_key(),
    reason="OPENAI_API_KEY required",
)

SKIP_NO_ANTHROPIC = pytest.mark.skipif(
    not has_anthropic_key(),
    reason="ANTHROPIC_API_KEY required",
)


# --- Direct API key tests ---

@pytest.mark.smoke
@SKIP_NO_OPENAI
def test_openai_api_key_valid():
    """Verify OpenAI API key works via models.list() (free, instant)."""
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    models = client.models.list()
    model_ids = [m.id for m in models.data]
    assert len(model_ids) > 0, "No models returned — key may be invalid"
    assert "whisper-1" in model_ids, "whisper-1 not found — transcription won't work"


@pytest.mark.smoke
@SKIP_NO_ANTHROPIC
def test_anthropic_api_key_valid():
    """Verify Anthropic API key works via LiteLLM completion (claude-haiku-4-5, ~$0.001)."""
    import litellm

    os.environ["ANTHROPIC_API_KEY"] = os.environ["ANTHROPIC_API_KEY"]
    response = litellm.completion(
        model="claude-haiku-4-5-20251001",
        messages=[{"role": "user", "content": "Reply with the word 'ok'"}],
        max_tokens=5,
    )
    text = response.choices[0].message.content.strip().lower()
    assert "ok" in text, f"Unexpected response: {text}"


@pytest.mark.smoke
@SKIP_NO_OPENAI
def test_openai_summarization_via_litellm():
    """Verify OpenAI summarization path works via LiteLLM (gpt-4o-mini, ~$0.001)."""
    import litellm

    os.environ["OPENAI_API_KEY"] = os.environ["OPENAI_API_KEY"]
    response = litellm.completion(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Reply with the word 'ok'"}],
        max_tokens=5,
    )
    text = response.choices[0].message.content.strip().lower()
    assert "ok" in text, f"Unexpected response: {text}"


# --- TopicAnalyzer integration tests ---

MOCK_TRANSCRIPT = {
    "text": "Today we discussed project timelines and budget allocation. "
            "The team agreed to extend the deadline by two weeks.",
    "segments": [
        {"start": 0.0, "end": 15.0, "text": "Today we discussed project timelines and budget allocation."},
        {"start": 15.0, "end": 30.0, "text": "The team agreed to extend the deadline by two weeks."},
    ],
    "duration": 30.0,
    "language": "en",
}


@pytest.mark.smoke
@SKIP_NO_OPENAI
def test_topic_analyzer_openai():
    """Verify TopicAnalyzer works end-to-end with gpt-4o-mini."""
    from transcripts.core.topic_analyzer import TopicAnalyzer

    analyzer = TopicAnalyzer(model="gpt-4o-mini")
    result = analyzer.analyze_transcript(MOCK_TRANSCRIPT)

    assert "summary" in result, "Missing 'summary' in analysis result"
    assert len(result["summary"]) > 0, "Empty summary returned"


@pytest.mark.smoke
@SKIP_NO_ANTHROPIC
def test_topic_analyzer_anthropic():
    """Verify TopicAnalyzer works end-to-end with claude-haiku-4-5."""
    from transcripts.core.topic_analyzer import TopicAnalyzer

    analyzer = TopicAnalyzer(model="claude-haiku-4-5-20251001")
    result = analyzer.analyze_transcript(MOCK_TRANSCRIPT)

    assert "summary" in result, "Missing 'summary' in analysis result"
    assert len(result["summary"]) > 0, "Empty summary returned"
