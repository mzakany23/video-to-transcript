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
                        "content": """You are an expert transcript analyst with deep expertise in extracting insights, patterns, and wisdom from conversations.

Your mission is to go beyond surface-level summarization and provide rich, actionable analysis that helps people understand not just WHAT was said, but WHY it matters, WHAT it means, and HOW to apply it.

You excel at:
- Identifying key insights, breakthrough moments, and wisdom
- Extracting practical lessons and actionable takeaways
- Capturing memorable stories, anecdotes, and personal experiences
- Recognizing patterns, themes, and connections across topics
- Highlighting resources, tools, techniques, and frameworks mentioned
- Understanding context, subtext, and deeper meaning
- Finding the gold nuggets that make content truly valuable
- Detecting shifts in energy, tone, or direction in conversations

You analyze all types of content: business meetings, podcasts, coaching calls, interviews, workshops, brainstorms, client calls, and more. You adapt your analysis style to the content type while maintaining depth and insight."""
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

        prompt = f"""Analyze this transcript deeply to extract maximum value, insights, and wisdom.

═══════════════════════════════════════════════════════════════════════════════
TRANSCRIPT DETAILS
═══════════════════════════════════════════════════════════════════════════════
Duration: {duration_formatted}
Total segments: {len(segments)}

SAMPLE SEGMENTS WITH TIMESTAMPS:
{segments_text}

FULL TRANSCRIPT TEXT:
{full_text[:12000]}{"..." if len(full_text) > 12000 else ""}

═══════════════════════════════════════════════════════════════════════════════
YOUR ANALYSIS MISSION
═══════════════════════════════════════════════════════════════════════════════

**STEP 1: Identify Topics (5-15 topics depending on length)**
Break down the conversation into natural topic boundaries. For short content (<15 min), aim for 5-8 topics. For longer content (>30 min), aim for 10-15 topics for better granularity.

**STEP 2: For EACH topic, provide:**

1. **Title**: Compelling, specific title (5-10 words) that captures the essence
2. **Segment IDs**: start_segment_id and end_segment_id (0-based index)
3. **Summary**: 2-4 sentences that explain WHAT was discussed and WHY it matters
4. **Key Insights** (3-7 items): The breakthrough moments, wisdom, and learnings. Go deep here - what can people actually learn and apply?
5. **Memorable Quotes** (1-5 if applicable): Powerful, quotable moments that capture wisdom or emotion. Include speaker context if relevant.
6. **Stories/Anecdotes** (if any): Personal experiences or examples shared. These make content memorable.
7. **Resources Mentioned** (if any): Books, tools, frameworks, techniques, practices, or methodologies mentioned
8. **Action Items** (if any): Specific actions, next steps, or commitments made
9. **Decisions** (if any): Conclusions reached or choices made
10. **Key Themes** (1-3): Overarching themes present in this topic

**STEP 3: Executive Summary**
Write a compelling 3-5 sentence executive summary that captures:
- The main narrative arc or purpose of the conversation
- The most important insights or takeaways
- Who would benefit from this content and why

**STEP 4: Overall Analysis**
Provide:
- **Main Themes** (3-7): The big-picture themes across the entire conversation
- **Content Type** (infer this): Is this a podcast, business meeting, coaching call, interview, workshop, brainstorm, etc.?
- **Key Takeaways** (5-10): The most valuable lessons, insights, or wisdom someone should remember

═══════════════════════════════════════════════════════════════════════════════
JSON STRUCTURE
═══════════════════════════════════════════════════════════════════════════════

Return your analysis as ONLY valid JSON (no other text) with this structure:

{{
  "executive_summary": "3-5 sentence compelling overview",
  "content_type": "podcast/meeting/coaching/interview/workshop/etc",
  "topics": [
    {{
      "id": 1,
      "title": "Compelling specific title here",
      "start_segment_id": 0,
      "end_segment_id": 10,
      "summary": "2-4 sentences explaining what AND why it matters",
      "key_insights": ["Deep insight 1", "Wisdom point 2", "Practical learning 3"],
      "key_quotes": ["Memorable quote 1", "Powerful quote 2"],
      "stories": ["Brief description of story/anecdote if shared"],
      "resources": ["Book: The Power of Now by Eckhart Tolle", "Technique: Box breathing"],
      "action_items": ["Specific action if mentioned"],
      "decisions": ["Decision if made"],
      "themes": ["Theme 1", "Theme 2"]
    }}
  ],
  "metadata": {{
    "total_topics": 12,
    "main_themes": ["Theme 1", "Theme 2", "Theme 3"],
    "key_takeaways": ["Takeaway 1", "Takeaway 2", "Takeaway 3"]
  }}
}}

═══════════════════════════════════════════════════════════════════════════════
ANALYSIS GUIDELINES
═══════════════════════════════════════════════════════════════════════════════

✓ GO DEEP: Extract real insights, not just "they discussed X"
✓ BE SPECIFIC: Use actual examples, numbers, and details from the transcript
✓ CAPTURE WISDOM: Find the profound moments and breakthrough insights
✓ TELL STORIES: Highlight personal experiences and anecdotes shared
✓ FIND PATTERNS: Connect ideas across topics and identify recurring themes
✓ EXTRACT VALUE: Focus on what makes this content worth consuming
✓ BE GRANULAR: More topics = better navigation (aim for 5-8 min per topic)
✓ INCLUDE RESOURCES: Always capture books, tools, and techniques mentioned

✗ AVOID: Generic summaries like "they talked about mindfulness"
✗ AVOID: Missing important quotes, stories, or resources
✗ AVOID: Too few topics for long content (>1 hour should have 10+ topics)

IMPORTANT: Return ONLY valid JSON, no markdown, no explanations, just pure JSON."""

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
                'key_points': topic.get('key_points', topic.get('key_insights', [])),  # Support both old and new field names
                'key_quotes': topic.get('key_quotes', []),
                'stories': topic.get('stories', []),
                'resources': topic.get('resources', []),
                'action_items': topic.get('action_items', []),
                'decisions': topic.get('decisions', []),
                'themes': topic.get('themes', [])
            }

            formatted_topics.append(formatted_topic)

        return {
            'executive_summary': analysis.get('executive_summary', ''),
            'content_type': analysis.get('content_type', 'conversation'),
            'topics': formatted_topics,
            'metadata': {
                'total_topics': len(formatted_topics),
                'duration': duration,
                'duration_formatted': format_timestamp(duration),
                'language': language,
                'main_themes': analysis.get('metadata', {}).get('main_themes', []),
                'key_takeaways': analysis.get('metadata', {}).get('key_takeaways', []),
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
