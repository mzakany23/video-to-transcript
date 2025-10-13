"""
Premium HTML email template for transcript summaries
Creates sleek, professional emails that users can read, copy, and paste
"""

from typing import Dict, Any, List
from datetime import datetime


class HTMLEmailTemplate:
    """Generates beautiful HTML emails for transcript summaries"""

    @staticmethod
    def generate_summary_email(
        transcript_data: Dict[str, Any],
        topic_analysis: Dict[str, Any],
        original_file_name: str,
        dropbox_links: Dict[str, str]
    ) -> str:
        """
        Generate a premium HTML email with the transcript summary

        Args:
            transcript_data: Original transcript data with segments
            topic_analysis: Topic analysis from TopicAnalyzer
            original_file_name: Name of the original file
            dropbox_links: Dictionary with share URLs for Dropbox files

        Returns:
            HTML email string
        """
        # Extract metadata
        duration = topic_analysis.get('metadata', {}).get('duration_formatted', '00:00')
        language = topic_analysis.get('metadata', {}).get('language', 'unknown').upper()
        processed_at = datetime.now().strftime('%B %d, %Y')
        topics = topic_analysis.get('topics', [])
        exec_summary = topic_analysis.get('executive_summary', '')
        themes = topic_analysis.get('metadata', {}).get('main_themes', [])

        # Calculate stats
        total_actions = sum(len(t.get('action_items', [])) for t in topics)
        total_decisions = sum(len(t.get('decisions', [])) for t in topics)

        # Generate topic cards HTML
        topic_cards_html = HTMLEmailTemplate._generate_topic_cards(topics)

        # Generate themes HTML
        themes_html = HTMLEmailTemplate._generate_themes(themes)

        # Get dropbox link
        dropbox_link = dropbox_links.get('summary_share_url', dropbox_links.get('txt_share_url', '#'))

        # Generate all timestamps list for copy button
        all_timestamps = '\n'.join([
            f"{topic.get('timestamp_range', '')} - {topic.get('title', '')}"
            for topic in topics
        ])
        # Escape backticks for JavaScript
        all_timestamps_escaped = all_timestamps.replace('`', '\\`')

        # Build the email
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Transcript Summary</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f5f5f7; color: #1d1d1f;">
    <div style="max-width: 680px; margin: 0 auto; background-color: #ffffff;">

        <!-- Header -->
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 30px; color: white;">
            <div style="font-size: 14px; text-transform: uppercase; letter-spacing: 1px; opacity: 0.9; margin-bottom: 8px;">
                Transcript Summary
            </div>
            <h1 style="margin: 0; font-size: 28px; font-weight: 600; line-height: 1.3;">
                {HTMLEmailTemplate._escape_html(original_file_name)}
            </h1>
            <div style="margin-top: 16px; font-size: 14px; opacity: 0.95;">
                <span style="margin-right: 16px;">{processed_at}</span>
                <span style="margin-right: 16px;">•</span>
                <span style="margin-right: 16px;">{duration}</span>
                <span style="margin-right: 16px;">•</span>
                <span>{language}</span>
            </div>
        </div>

        <!-- Executive Summary -->
        {HTMLEmailTemplate._generate_executive_summary(exec_summary)}

        <!-- Main Themes -->
        {themes_html}

        <!-- Copy All Timestamps Button -->
        <div style="padding: 20px 30px 10px 30px; text-align: center;">
            <button onclick="copyAllTimestamps()" id="copyAllBtn" style="background: #667eea; color: white; border: none; padding: 12px 24px; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                Copy All Timestamps
            </button>
            <div id="copyStatus" style="margin-top: 8px; font-size: 13px; color: #10b981; display: none;">
                ✓ Copied to clipboard!
            </div>
        </div>

        <!-- Topics -->
        <div style="padding: 30px;">
            <h2 style="margin: 0 0 20px 0; font-size: 20px; font-weight: 600; color: #1d1d1f;">
                Topics & Timestamps
            </h2>

            {topic_cards_html}
        </div>

        <!-- Quick Stats -->
        <div style="background: #f9fafb; padding: 30px; margin: 0 30px 30px 30px; border-radius: 12px;">
            <h3 style="margin: 0 0 20px 0; font-size: 16px; font-weight: 600; color: #1d1d1f; text-align: center;">
                Quick Reference
            </h3>
            <div style="display: table; width: 100%; table-layout: fixed;">
                <div style="display: table-row;">
                    <div style="display: table-cell; text-align: center; padding: 10px;">
                        <div style="font-size: 32px; font-weight: 700; color: #667eea; margin-bottom: 4px;">
                            {len(topics)}
                        </div>
                        <div style="color: #6b7280; font-size: 13px;">
                            Topics
                        </div>
                    </div>
                    <div style="display: table-cell; text-align: center; padding: 10px;">
                        <div style="font-size: 32px; font-weight: 700; color: #10b981; margin-bottom: 4px;">
                            {total_actions}
                        </div>
                        <div style="color: #6b7280; font-size: 13px;">
                            Action Items
                        </div>
                    </div>
                    <div style="display: table-cell; text-align: center; padding: 10px;">
                        <div style="font-size: 32px; font-weight: 700; color: #3b82f6; margin-bottom: 4px;">
                            {total_decisions}
                        </div>
                        <div style="color: #6b7280; font-size: 13px;">
                            Decisions
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Dropbox Link -->
        <div style="padding: 30px; text-align: center; border-top: 1px solid #e5e7eb;">
            <a href="{dropbox_link}" style="display: inline-block; background-color: #667eea; color: white; padding: 14px 28px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 15px;">
                View Full Transcript in Dropbox
            </a>
        </div>

        <!-- Footer -->
        <div style="text-align: center; color: #9ca3af; font-size: 12px; padding: 20px 30px 30px 30px; line-height: 1.6;">
            Generated with AI • Timestamps link to original segments
        </div>

    </div>

    <!-- JavaScript for copy functionality -->
    <script>
        const allTimestamps = `{all_timestamps_escaped}`;

        function copyAllTimestamps() {{
            // Use clipboard API if available
            if (navigator.clipboard && navigator.clipboard.writeText) {{
                navigator.clipboard.writeText(allTimestamps).then(() => {{
                    showCopyStatus();
                }}).catch(err => {{
                    // Fallback for older browsers
                    fallbackCopy(allTimestamps);
                }});
            }} else {{
                fallbackCopy(allTimestamps);
            }}
        }}

        function fallbackCopy(text) {{
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            document.body.appendChild(textarea);
            textarea.select();
            try {{
                document.execCommand('copy');
                showCopyStatus();
            }} catch (err) {{
                console.error('Failed to copy:', err);
            }}
            document.body.removeChild(textarea);
        }}

        function showCopyStatus() {{
            const status = document.getElementById('copyStatus');
            status.style.display = 'block';
            setTimeout(() => {{
                status.style.display = 'none';
            }}, 3000);
        }}
    </script>
</body>
</html>"""

        return html

    @staticmethod
    def _escape_html(text: str) -> str:
        """Escape HTML special characters"""
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;'))

    @staticmethod
    def _generate_executive_summary(exec_summary: str) -> str:
        """Generate executive summary HTML section"""
        if not exec_summary:
            return ''

        return f"""
        <div style="background: #f0f9ff; border-left: 4px solid #0284c7; padding: 24px 30px; margin: 0;">
            <h2 style="margin: 0 0 12px 0; font-size: 16px; font-weight: 600; color: #0c4a6e; text-transform: uppercase; letter-spacing: 0.5px;">
                Executive Summary
            </h2>
            <p style="color: #0f172a; line-height: 1.6; margin: 0; font-size: 15px;">
                {HTMLEmailTemplate._escape_html(exec_summary)}
            </p>
        </div>"""

    @staticmethod
    def _generate_themes(themes: List[str]) -> str:
        """Generate main themes section"""
        if not themes:
            return ''

        theme_pills = ''.join([
            f"""<span style="background: #e0e7ff; color: #4338ca; padding: 8px 16px; border-radius: 20px; margin: 4px 8px 4px 0; display: inline-block; font-size: 13px; font-weight: 500;">
                {HTMLEmailTemplate._escape_html(theme)}
            </span>"""
            for theme in themes
        ])

        return f"""
        <div style="padding: 24px 30px; background: white;">
            <h3 style="margin: 0 0 12px 0; font-size: 14px; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px;">
                Main Themes
            </h3>
            <div style="line-height: 2;">
                {theme_pills}
            </div>
        </div>"""

    @staticmethod
    def _generate_topic_cards(topics: List[Dict[str, Any]]) -> str:
        """Generate HTML for all topic cards"""
        if not topics:
            return '<p style="color: #6b7280; font-style: italic;">No topics identified.</p>'

        cards = []
        for topic in topics:
            card_html = HTMLEmailTemplate._generate_single_topic_card(topic)
            cards.append(card_html)

        return '\n'.join(cards)

    @staticmethod
    def _generate_single_topic_card(topic: Dict[str, Any]) -> str:
        """Generate a single topic card with collapsible sections"""
        timestamp_range = topic.get('timestamp_range', '[00:00 - 00:00]')
        title = topic.get('title', 'Untitled Topic')
        topic_id = topic.get('id', '')
        summary = topic.get('summary', '')
        key_points = topic.get('key_points', [])
        quotes = topic.get('key_quotes', [])
        actions = topic.get('action_items', [])
        decisions = topic.get('decisions', [])

        # Generate key points HTML
        key_points_html = ''
        if key_points:
            points_list = ''.join([
                f'<li style="margin: 8px 0; color: #4b5563; line-height: 1.5;">{HTMLEmailTemplate._escape_html(point)}</li>'
                for point in key_points
            ])
            key_points_html = f"""
            <details style="margin: 16px 0;">
                <summary style="cursor: pointer; color: #667eea; font-weight: 600; font-size: 14px; padding: 8px 0;">
                    Key Points ({len(key_points)})
                </summary>
                <ul style="margin: 12px 0; padding-left: 20px;">
                    {points_list}
                </ul>
            </details>"""

        # Generate quotes HTML
        quotes_html = ''
        if quotes:
            quotes_list = ''.join([
                f"""<div style="border-left: 3px solid #d1d5db; padding-left: 16px; margin: 12px 0; color: #4b5563; font-style: italic;">
                    "{HTMLEmailTemplate._escape_html(quote)}"
                </div>"""
                for quote in quotes
            ])
            quotes_html = f"""
            <details style="margin: 16px 0;">
                <summary style="cursor: pointer; color: #667eea; font-weight: 600; font-size: 14px; padding: 8px 0;">
                    Key Quotes ({len(quotes)})
                </summary>
                {quotes_list}
            </details>"""

        # Generate action items HTML
        actions_html = ''
        if actions:
            actions_list = ''.join([
                f'<li style="margin: 8px 0; color: #78350f; line-height: 1.5;">{HTMLEmailTemplate._escape_html(action)}</li>'
                for action in actions
            ])
            actions_html = f"""
            <div style="background: #fef3c7; border-left: 3px solid #f59e0b; padding: 16px; margin: 16px 0; border-radius: 4px;">
                <strong style="color: #92400e; font-size: 14px;">Action Items:</strong>
                <ul style="margin: 8px 0 0 0; padding-left: 20px;">
                    {actions_list}
                </ul>
            </div>"""

        # Generate decisions HTML
        decisions_html = ''
        if decisions:
            decisions_list = ''.join([
                f'<li style="margin: 8px 0; color: #065f46; line-height: 1.5;">{HTMLEmailTemplate._escape_html(decision)}</li>'
                for decision in decisions
            ])
            decisions_html = f"""
            <div style="background: #d1fae5; border-left: 3px solid #10b981; padding: 16px; margin: 16px 0; border-radius: 4px;">
                <strong style="color: #065f46; font-size: 14px;">Decisions Made:</strong>
                <ul style="margin: 8px 0 0 0; padding-left: 20px;">
                    {decisions_list}
                </ul>
            </div>"""

        # Copy button for timestamp (using data attribute for easy JS copy)
        copy_button_html = f"""
        <button onclick="navigator.clipboard.writeText('{timestamp_range}')" style="background: #f3f4f6; border: 1px solid #d1d5db; color: #4b5563; padding: 4px 12px; border-radius: 4px; font-size: 12px; cursor: pointer; margin-left: 8px;">
            Copy
        </button>"""

        return f"""
        <div style="border: 1px solid #e5e7eb; border-radius: 8px; padding: 24px; margin: 0 0 16px 0; background: #ffffff;">
            <div style="display: flex; align-items: center; margin-bottom: 12px; flex-wrap: wrap;">
                <span style="background: #10b981; color: white; padding: 6px 12px; border-radius: 6px; font-size: 13px; font-weight: 600; white-space: nowrap;">
                    {HTMLEmailTemplate._escape_html(timestamp_range)}
                </span>
                {copy_button_html}
            </div>
            <h4 style="margin: 0 0 12px 0; color: #1d1d1f; font-size: 18px; font-weight: 600;">
                {topic_id}. {HTMLEmailTemplate._escape_html(title)}
            </h4>

            <p style="color: #6b7280; margin: 0 0 16px 0; line-height: 1.6; font-size: 15px;">
                {HTMLEmailTemplate._escape_html(summary)}
            </p>

            {key_points_html}
            {quotes_html}
            {actions_html}
            {decisions_html}
        </div>"""

    @staticmethod
    def generate_plain_text_summary(
        transcript_data: Dict[str, Any],
        topic_analysis: Dict[str, Any],
        original_file_name: str,
        dropbox_links: Dict[str, str]
    ) -> str:
        """
        Generate a plain text version of the summary email

        Args:
            transcript_data: Original transcript data
            topic_analysis: Topic analysis from TopicAnalyzer
            original_file_name: Name of original file
            dropbox_links: Dictionary with Dropbox share URLs

        Returns:
            Plain text email string
        """
        duration = topic_analysis.get('metadata', {}).get('duration_formatted', '00:00')
        language = topic_analysis.get('metadata', {}).get('language', 'unknown').upper()
        processed_at = datetime.now().strftime('%B %d, %Y')
        topics = topic_analysis.get('topics', [])
        exec_summary = topic_analysis.get('executive_summary', '')
        themes = topic_analysis.get('metadata', {}).get('main_themes', [])

        # Calculate stats
        total_actions = sum(len(t.get('action_items', [])) for t in topics)
        total_decisions = sum(len(t.get('decisions', [])) for t in topics)

        # Build plain text email
        text = f"""TRANSCRIPT SUMMARY
{'=' * 60}

{original_file_name}
{processed_at} | {duration} | {language}

"""

        # Executive Summary
        if exec_summary:
            text += f"""EXECUTIVE SUMMARY
{'-' * 60}

{exec_summary}

"""

        # Main Themes
        if themes:
            text += "MAIN THEMES\n"
            text += '-' * 60 + '\n'
            for theme in themes:
                text += f"• {theme}\n"
            text += "\n"

        # Topics
        text += "TOPICS & TIMESTAMPS\n"
        text += '=' * 60 + '\n\n'

        for topic in topics:
            timestamp_range = topic.get('timestamp_range', '[00:00 - 00:00]')
            title = topic.get('title', 'Untitled Topic')
            topic_id = topic.get('id', '')
            summary = topic.get('summary', '')
            key_points = topic.get('key_points', [])
            actions = topic.get('action_items', [])
            decisions = topic.get('decisions', [])

            text += f"{timestamp_range} {topic_id}. {title}\n"
            text += '-' * 60 + '\n'

            if summary:
                text += f"{summary}\n\n"

            if key_points:
                text += "Key Points:\n"
                for point in key_points:
                    text += f"  • {point}\n"
                text += "\n"

            if actions:
                text += "Action Items:\n"
                for action in actions:
                    text += f"  ✓ {action}\n"
                text += "\n"

            if decisions:
                text += "Decisions Made:\n"
                for decision in decisions:
                    text += f"  ✓ {decision}\n"
                text += "\n"

            text += "\n"

        # Quick Stats
        text += "QUICK REFERENCE\n"
        text += '=' * 60 + '\n'
        text += f"Topics: {len(topics)}\n"
        text += f"Action Items: {total_actions}\n"
        text += f"Decisions: {total_decisions}\n\n"

        # Dropbox link
        dropbox_link = dropbox_links.get('summary_share_url', dropbox_links.get('txt_share_url', ''))
        if dropbox_link:
            text += f"View Full Transcript: {dropbox_link}\n\n"

        text += '-' * 60 + '\n'
        text += 'Generated with AI • Timestamps link to original segments\n'

        return text
