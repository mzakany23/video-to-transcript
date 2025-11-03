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
                "response_format": {"type": "json_object"},
            }

            # GPT-5 only supports temperature=1.0 (default), so only set for other models
            if not self.model.startswith("gpt-5"):
                api_params["temperature"] = 0.3

            response = self.client.chat.completions.create(**api_params)

            # Parse the response
            result_text = response.choices[0].message.content
            analysis = json.loads(result_text)

            print(f"✅ Analysis complete: {len(analysis.get('quotes', []))} quotes, {len(analysis.get('reel_snippets_standalone', []))} standalone snippets")

            # Validate and format the analysis
            formatted_analysis = self._format_analysis(analysis, segments, duration, language)

            return formatted_analysis

        except Exception as e:
            print(f"❌ Error analyzing transcript: {str(e)}")
            return self._empty_analysis(error=str(e))

    def _build_analysis_prompt(self, full_text: str, segments: List[Dict], duration: float) -> str:
        """Build the prompt for GPT analysis - Instagram-focused"""

        duration_formatted = format_timestamp(duration)

        prompt = f"""Analyze this transcript to extract content optimized for Instagram.

The goal is to provide a clean summary and copy-pastable content for Instagram carousel reels.

═══════════════════════════════════════════════════════════════════════════════
TRANSCRIPT
═══════════════════════════════════════════════════════════════════════════════
Duration: {duration_formatted}

{full_text}

═══════════════════════════════════════════════════════════════════════════════
YOUR MISSION - INSTAGRAM-FIRST CONTENT
═══════════════════════════════════════════════════════════════════════════════

Extract 3 key deliverables optimized for Instagram:

**1. SUMMARY (one full paragraph)**
- Write a compelling paragraph that captures the interesting concepts discussed
- Focus on WHAT was discussed, not WHO said it
- NO mention of narrative perspective (no "first person", "third person", etc.)
- Just explain the interesting ideas, insights, and topics covered
- Make it engaging and informative
- 4-6 sentences

**2. QUOTES (maximum 5 - quality over quantity)**
- Select ONLY the most quotable, shareable, and impactful moments
- These should be statements people would want to remember or share
- AVOID: Pleasantries, greetings, thank-yous, generic statements
- AVOID: "Your shares have meant so much", "Thanks for listening"
- CHOOSE: Wisdom, insights, metaphors, profound statements
- CHOOSE: Actionable advice, perspective shifts, memorable phrasing
- Example GOOD: "The mind is a wonderful servant, but a terrible master"
- Example BAD: "Your thoughtful messages have meant so much to me"
- If there aren't 5 truly great quotes, provide fewer (quality > quantity)

**3. INSTAGRAM REEL SNIPPETS (provide BOTH formats below)**

Format A: Standalone Insights (5-8 snippets)
- Short, punchy insights (1-2 sentences each)
- Can be used as individual carousel panels
- Direct, impactful statements
- Each should stand alone
- Example: "Start your day with 5 minutes of silence before checking your phone"
- Example: "Decision fatigue is real - make important choices in the morning"

Format B: Mini-Posts with Context (3-5 snippets)
- Longer snippets with context (2-4 sentences each)
- Provide background and application
- More narrative and explanatory
- Each is a complete thought with setup and payoff
- Example: "Why morning routines matter: Most successful people protect the first hour of their day. Instead of reacting to emails, they invest in themselves first."
- Example: "The power of constraints: Limitations force creativity. When you have all the time in the world, you procrastinate. When you have 2 hours, you find a way."

═══════════════════════════════════════════════════════════════════════════════
JSON STRUCTURE
═══════════════════════════════════════════════════════════════════════════════

Return your analysis as ONLY valid JSON (no other text) with this structure:

{{
  "summary": "One full paragraph describing the interesting concepts discussed...",
  "quotes": [
    "Powerful quote 1",
    "Memorable quote 2",
    "Insight quote 3",
    "Wisdom quote 4",
    "Actionable quote 5"
  ],
  "reel_snippets_standalone": [
    "Short punchy insight 1",
    "Direct statement 2",
    "Memorable insight 3",
    "Actionable tip 4",
    "Perspective shift 5"
  ],
  "reel_snippets_context": [
    "Mini-post with context 1...",
    "Narrative snippet 2...",
    "Explanatory insight 3..."
  ],
  "metadata": {{
    "content_type": "podcast/meeting/coaching/interview/workshop/etc"
  }}
}}

═══════════════════════════════════════════════════════════════════════════════
GUIDELINES
═══════════════════════════════════════════════════════════════════════════════

✓ FOCUS ON VALUE: What makes this content worth sharing on Instagram?
✓ BE SPECIFIC: Use actual concepts and details from the transcript
✓ MAKE IT SHAREABLE: Every element should be Instagram-ready
✓ QUALITY OVER QUANTITY: 3 great quotes beat 5 mediocre ones
✓ NO EMOJIS: Keep all text clean and emoji-free
✓ COPY-PASTABLE: All snippets should be ready to use as-is
✓ ACTIONABLE: Prioritize insights people can actually apply
✓ ENGAGING: Make people want to read and share

✗ AVOID: Generic platitudes that could apply to any content
✗ AVOID: Quotes that aren't actually inspiring or useful
✗ AVOID: Overly long or complex snippets
✗ AVOID: Mentioning timestamps, speakers by name (unless critical to the insight)
✗ AVOID: Emojis in any section

═══════════════════════════════════════════════════════════════════════════════
CRITICAL: HALLUCINATION PREVENTION
═══════════════════════════════════════════════════════════════════════════════

**NEVER INVENT INFORMATION**
- DO NOT fabricate quotes that aren't actually spoken
- DO NOT invent concepts, frameworks, or ideas not explicitly mentioned
- Every quote, insight, and snippet must come from the actual transcript
- If you're uncertain about a detail, OMIT IT rather than guess
- If there aren't enough great quotes, provide fewer

**ONLY USE INFORMATION DIRECTLY FROM THE TRANSCRIPT**
If the transcript doesn't explicitly mention something, DO NOT include it.

═══════════════════════════════════════════════════════════════════════════════

IMPORTANT: Return ONLY valid JSON, no markdown, no explanations, just pure JSON."""

        return prompt

    def _format_analysis(self, analysis: Dict, segments: List[Dict],
                        duration: float, language: str) -> Dict[str, Any]:
        """Format and validate the analysis results - Instagram-focused"""

        return {
            'summary': analysis.get('summary', ''),
            'quotes': analysis.get('quotes', []),
            'reel_snippets_standalone': analysis.get('reel_snippets_standalone', []),
            'reel_snippets_context': analysis.get('reel_snippets_context', []),
            'content_type': analysis.get('metadata', {}).get('content_type', 'conversation'),
            'metadata': {
                'duration': duration,
                'duration_formatted': format_timestamp(duration),
                'language': language,
                'model_used': self.model,
                'analyzed_at': datetime.now().isoformat()
            }
        }

    def _empty_analysis(self, error: str = None) -> Dict[str, Any]:
        """Return empty analysis structure"""
        return {
            'summary': '',
            'quotes': [],
            'reel_snippets_standalone': [],
            'reel_snippets_context': [],
            'content_type': 'unknown',
            'metadata': {
                'error': error
            }
        }
