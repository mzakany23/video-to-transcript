"""
Summary formatter for creating readable summary documents from topic analysis
"""

from typing import Dict, Any
from datetime import datetime


class SummaryFormatter:
    """Formats topic analysis into readable summary documents"""

    @staticmethod
    def format_summary_text(transcript_data: Dict[str, Any],
                           topic_analysis: Dict[str, Any],
                           original_file_name: str) -> str:
        """
        Format topic analysis into a readable text summary

        Args:
            transcript_data: Original transcript data
            topic_analysis: Topic analysis from TopicAnalyzer
            original_file_name: Name of original audio file

        Returns:
            Formatted summary text
        """
        # Header
        duration = topic_analysis.get('metadata', {}).get('duration_formatted', '00:00')
        language = topic_analysis.get('metadata', {}).get('language', 'unknown')
        processed_at = datetime.now().strftime('%Y-%m-%d %H:%M')

        summary = f"""TRANSCRIPT SUMMARY: {original_file_name}
{'=' * (20 + len(original_file_name))}
Duration: {duration}
Processed: {processed_at}
Language: {language.upper()}
Topics: {topic_analysis.get('metadata', {}).get('total_topics', 0)}

"""

        # Executive Summary
        exec_summary = topic_analysis.get('executive_summary', '')
        if exec_summary:
            summary += f"""EXECUTIVE SUMMARY
-----------------
{exec_summary}

"""

        # Main Themes
        themes = topic_analysis.get('metadata', {}).get('main_themes', [])
        if themes:
            summary += "MAIN THEMES\n-----------\n"
            for theme in themes:
                summary += f"• {theme}\n"
            summary += "\n"

        # Topics with timestamps
        summary += """TOPICS & TIMESTAMPS
-------------------

"""

        topics = topic_analysis.get('topics', [])
        for topic in topics:
            timestamp_range = topic.get('timestamp_range', '[00:00 - 00:00]')
            title = topic.get('title', 'Untitled Topic')
            topic_summary = topic.get('summary', '')

            summary += f"{timestamp_range} {topic.get('id', 0)}. {title}\n"

            if topic_summary:
                summary += f"    {topic_summary}\n"

            # Key points
            key_points = topic.get('key_points', [])
            if key_points:
                summary += "\n"
                for point in key_points:
                    summary += f"    • {point}\n"

            # Key quotes
            quotes = topic.get('key_quotes', [])
            if quotes:
                summary += "\n"
                for quote in quotes:
                    summary += f'    💬 "{quote}"\n'

            # Action items
            actions = topic.get('action_items', [])
            if actions:
                summary += "\n    Action Items:\n"
                for action in actions:
                    summary += f"    ✓ {action}\n"

            # Decisions
            decisions = topic.get('decisions', [])
            if decisions:
                summary += "\n    Decisions Made:\n"
                for decision in decisions:
                    summary += f"    ✓ {decision}\n"

            summary += "\n"

        # Quick reference footer
        total_actions = sum(len(t.get('action_items', [])) for t in topics)
        total_decisions = sum(len(t.get('decisions', [])) for t in topics)

        summary += f"""QUICK REFERENCE
---------------
Total Duration: {duration}
Topics Covered: {len(topics)}
Action Items: {total_actions}
Decisions Made: {total_decisions}

"""

        # Add note about full transcript
        summary += """---
📄 For complete transcript with all details, see the full transcript file.
🤖 Summary generated with AI - timestamps link to original audio segments.
"""

        return summary

    @staticmethod
    def format_summary_markdown(transcript_data: Dict[str, Any],
                                topic_analysis: Dict[str, Any],
                                original_file_name: str) -> str:
        """
        Format topic analysis into markdown with clickable timestamps

        Args:
            transcript_data: Original transcript data
            topic_analysis: Topic analysis from TopicAnalyzer
            original_file_name: Name of original audio file

        Returns:
            Formatted markdown summary
        """
        # Header
        duration = topic_analysis.get('metadata', {}).get('duration_formatted', '00:00')
        language = topic_analysis.get('metadata', {}).get('language', 'unknown')
        processed_at = datetime.now().strftime('%Y-%m-%d %H:%M')

        md = f"""# Transcript Summary: {original_file_name}

**Duration:** {duration} | **Language:** {language.upper()} | **Processed:** {processed_at}

---

## Executive Summary

{topic_analysis.get('executive_summary', 'No summary available.')}

"""

        # Main Themes
        themes = topic_analysis.get('metadata', {}).get('main_themes', [])
        if themes:
            md += "## Main Themes\n\n"
            for theme in themes:
                md += f"- {theme}\n"
            md += "\n"

        # Topics
        md += "## Topics & Timestamps\n\n"

        topics = topic_analysis.get('topics', [])
        for topic in topics:
            timestamp_range = topic.get('timestamp_range', '[00:00 - 00:00]')
            title = topic.get('title', 'Untitled Topic')
            topic_summary = topic.get('summary', '')

            md += f"### {timestamp_range} {topic.get('id', 0)}. {title}\n\n"

            if topic_summary:
                md += f"{topic_summary}\n\n"

            # Key points
            key_points = topic.get('key_points', [])
            if key_points:
                md += "**Key Points:**\n"
                for point in key_points:
                    md += f"- {point}\n"
                md += "\n"

            # Key quotes
            quotes = topic.get('key_quotes', [])
            if quotes:
                md += "**Key Quotes:**\n"
                for quote in quotes:
                    md += f'> "{quote}"\n\n'

            # Action items
            actions = topic.get('action_items', [])
            if actions:
                md += "**Action Items:**\n"
                for action in actions:
                    md += f"- [ ] {action}\n"
                md += "\n"

            # Decisions
            decisions = topic.get('decisions', [])
            if decisions:
                md += "**Decisions Made:**\n"
                for decision in decisions:
                    md += f"- ✓ {decision}\n"
                md += "\n"

        # Quick reference
        total_actions = sum(len(t.get('action_items', [])) for t in topics)
        total_decisions = sum(len(t.get('decisions', [])) for t in topics)

        md += f"""---

## Quick Reference

| Metric | Value |
|--------|-------|
| Total Duration | {duration} |
| Topics Covered | {len(topics)} |
| Action Items | {total_actions} |
| Decisions Made | {total_decisions} |

---

*📄 For complete transcript with all details, see the full transcript file.*
*🤖 Summary generated with AI - timestamps link to original audio segments.*
"""

        return md
