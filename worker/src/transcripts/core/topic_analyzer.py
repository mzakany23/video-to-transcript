"""
Topic analyzer for transcripts using OpenAI GPT models
Identifies topic boundaries, key points, and generates structured summaries
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    from openai import OpenAI
except ImportError:
    raise ImportError("OpenAI SDK not installed. Run: uv add openai")

from ..config import Config
from ..utils.timestamp_formatter import format_timestamp, format_timestamp_range


class TopicAnalyzer:
    """Analyzes transcripts to identify topics and generate summaries"""

    def __init__(self, api_key: str = None, model: str = None):
        """
        Initialize topic analyzer

        Args:
            api_key: OpenAI API key (defaults to Config.OPENAI_API_KEY)
            model: Model to use for analysis (defaults to Config.OPENAI_SUMMARIZATION_MODEL)
        """
        self.api_key = api_key or Config.OPENAI_API_KEY
        self.model = model or Config.OPENAI_SUMMARIZATION_MODEL

        if not self.api_key:
            raise ValueError("OpenAI API key is required for topic analysis")

        self.client = OpenAI(api_key=self.api_key)
        print(f"✅ Topic analyzer initialized with model: {self.model}")

    def analyze_transcript(self, transcript_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze transcript to identify topics and generate summary

        Args:
            transcript_data: Transcript data with 'text' and 'segments' fields

        Returns:
            Dictionary with topics, executive summary, and metadata
        """
        try:
            full_text = transcript_data.get('text', '')
            segments = transcript_data.get('segments', [])
            duration = transcript_data.get('duration', 0)
            language = transcript_data.get('language', 'unknown')

            if not full_text or not segments:
                print("⚠️ No text or segments found in transcript")
                return self._empty_analysis()

            print(f"🔍 Analyzing transcript: {len(full_text)} characters, {len(segments)} segments")

            # Build the analysis prompt
            prompt = self._build_analysis_prompt(full_text, segments, duration)

            # Call OpenAI API
            print(f"🤖 Calling {self.model} for topic analysis...")

            # Build API call parameters
            api_params = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing transcripts and identifying logical topic boundaries. You provide structured, accurate summaries with timestamps."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "response_format": {"type": "json_object"}
            }

            # GPT-5 models only support default temperature (1.0)
            # Other models support custom temperature
            if not self.model.startswith("gpt-5"):
                api_params["temperature"] = 0.3  # Lower temperature for more consistent analysis

            response = self.client.chat.completions.create(**api_params)

            # Parse the response
            result_text = response.choices[0].message.content
            analysis = json.loads(result_text)

            print(f"✅ Analysis complete: {len(analysis.get('topics', []))} topics identified")

            # Validate and format the analysis
            formatted_analysis = self._format_analysis(analysis, segments, duration, language)

            return formatted_analysis

        except Exception as e:
            print(f"❌ Error analyzing transcript: {str(e)}")
            return self._empty_analysis(error=str(e))

    def _build_analysis_prompt(self, full_text: str, segments: List[Dict], duration: float) -> str:
        """Build the prompt for GPT analysis"""

        # Include segment timestamps for reference
        segment_info = []
        for i, seg in enumerate(segments[:50]):  # Limit to first 50 for context
            start = seg.get('start', 0)
            text = seg.get('text', '').strip()
            segment_info.append(f"[{format_timestamp(start)}] {text}")

        segments_text = "\n".join(segment_info)
        if len(segments) > 50:
            segments_text += f"\n... ({len(segments) - 50} more segments)"

        duration_formatted = format_timestamp(duration)

        prompt = f"""Analyze this transcript and identify logical topic boundaries.

TRANSCRIPT INFO:
- Duration: {duration_formatted}
- Total segments: {len(segments)}

SAMPLE SEGMENTS WITH TIMESTAMPS:
{segments_text}

FULL TRANSCRIPT TEXT:
{full_text[:8000]}{"..." if len(full_text) > 8000 else ""}

TASK:
Identify 3-8 logical topics in this transcript. For each topic:
1. Determine start and end segment IDs (0-based index)
2. Create a descriptive title (5-8 words)
3. Write a 2-3 sentence summary
4. Extract 3-5 key points (bullet format)
5. Identify any key quotes (if notable)
6. List any action items mentioned
7. List any decisions made

Also provide:
- An executive summary (2-3 sentences) of the entire conversation
- Overall themes and takeaways

Return your analysis as a JSON object with this structure:
{{
  "executive_summary": "2-3 sentence overview",
  "topics": [
    {{
      "id": 1,
      "title": "Topic title here",
      "start_segment_id": 0,
      "end_segment_id": 10,
      "summary": "2-3 sentence summary",
      "key_points": ["point 1", "point 2", "point 3"],
      "key_quotes": ["quote if notable"],
      "action_items": ["action if any"],
      "decisions": ["decision if any"]
    }}
  ],
  "metadata": {{
    "total_topics": 5,
    "main_themes": ["theme 1", "theme 2"]
  }}
}}

IMPORTANT: Return ONLY valid JSON, no other text."""

        return prompt

    def _format_analysis(self, analysis: Dict, segments: List[Dict],
                        duration: float, language: str) -> Dict[str, Any]:
        """Format and validate the analysis results"""

        topics = analysis.get('topics', [])
        formatted_topics = []

        for topic in topics:
            start_seg_id = topic.get('start_segment_id', 0)
            end_seg_id = topic.get('end_segment_id', len(segments) - 1)

            # Ensure segment IDs are valid
            start_seg_id = max(0, min(start_seg_id, len(segments) - 1))
            end_seg_id = max(start_seg_id, min(end_seg_id, len(segments) - 1))

            # Get actual timestamps from segments
            start_time = segments[start_seg_id].get('start', 0) if start_seg_id < len(segments) else 0
            end_time = segments[end_seg_id].get('end', duration) if end_seg_id < len(segments) else duration

            formatted_topic = {
                'id': topic.get('id', len(formatted_topics) + 1),
                'title': topic.get('title', f'Topic {len(formatted_topics) + 1}'),
                'start_time': start_time,
                'end_time': end_time,
                'start_time_formatted': format_timestamp(start_time),
                'end_time_formatted': format_timestamp(end_time),
                'timestamp_range': format_timestamp_range(start_time, end_time),
                'start_segment_id': start_seg_id,
                'end_segment_id': end_seg_id,
                'summary': topic.get('summary', ''),
                'key_points': topic.get('key_points', []),
                'key_quotes': topic.get('key_quotes', []),
                'action_items': topic.get('action_items', []),
                'decisions': topic.get('decisions', [])
            }

            formatted_topics.append(formatted_topic)

        return {
            'executive_summary': analysis.get('executive_summary', ''),
            'topics': formatted_topics,
            'metadata': {
                'total_topics': len(formatted_topics),
                'duration': duration,
                'duration_formatted': format_timestamp(duration),
                'language': language,
                'main_themes': analysis.get('metadata', {}).get('main_themes', []),
                'model_used': self.model,
                'analyzed_at': datetime.now().isoformat()
            }
        }

    def _empty_analysis(self, error: str = None) -> Dict[str, Any]:
        """Return empty analysis structure"""
        return {
            'executive_summary': '',
            'topics': [],
            'metadata': {
                'total_topics': 0,
                'error': error
            }
        }
