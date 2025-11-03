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
        Generate Instagram-focused HTML email with the transcript summary

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

        # Extract new Instagram-focused content
        summary = topic_analysis.get('summary', '')
        quotes = topic_analysis.get('quotes', [])
        reel_snippets_standalone = topic_analysis.get('reel_snippets_standalone', [])
        reel_snippets_context = topic_analysis.get('reel_snippets_context', [])

        # Generate content sections
        quotes_html = HTMLEmailTemplate._generate_quotes(quotes)
        standalone_snippets_html = HTMLEmailTemplate._generate_standalone_snippets(reel_snippets_standalone)
        context_snippets_html = HTMLEmailTemplate._generate_context_snippets(reel_snippets_context)

        # Get dropbox link
        dropbox_link = dropbox_links.get('summary_share_url', dropbox_links.get('txt_share_url', '#'))

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

        <!-- Summary -->
        {HTMLEmailTemplate._generate_summary(summary)}

        <!-- Quotes -->
        {quotes_html}

        <!-- Reel Snippets - Standalone -->
        {standalone_snippets_html}

        <!-- Reel Snippets - Context -->
        {context_snippets_html}

        <!-- Dropbox Link -->
        <div style="padding: 30px; text-align: center; border-top: 1px solid #e5e7eb;">
            <a href="{dropbox_link}" style="display: inline-block; background-color: #667eea; color: white; padding: 14px 28px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 15px;">
                View Full Transcript in Dropbox
            </a>
        </div>

        <!-- Footer -->
        <div style="text-align: center; color: #9ca3af; font-size: 12px; padding: 20px 30px 30px 30px; line-height: 1.6;">
            Generated with AI for Instagram content creation
        </div>

    </div>
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
    def _generate_summary(summary: str) -> str:
        """Generate summary HTML section"""
        if not summary:
            return ''

        return f"""
        <div style="background: #f0f9ff; border-left: 4px solid #0284c7; padding: 24px 30px; margin: 0;">
            <h2 style="margin: 0 0 12px 0; font-size: 16px; font-weight: 600; color: #0c4a6e; text-transform: uppercase; letter-spacing: 0.5px;">
                Summary
            </h2>
            <p style="color: #0f172a; line-height: 1.7; margin: 0; font-size: 15px;">
                {HTMLEmailTemplate._escape_html(summary)}
            </p>
        </div>"""

    @staticmethod
    def _generate_quotes(quotes: List[str]) -> str:
        """Generate quotes HTML section"""
        if not quotes:
            return ''

        quotes_list = ''.join([
            f"""<div style="border-left: 4px solid #667eea; padding: 16px 20px; margin: 12px 0; background: #f9fafb; border-radius: 4px;">
                <p style="color: #1d1d1f; font-style: italic; margin: 0; font-size: 15px; line-height: 1.6;">
                    "{HTMLEmailTemplate._escape_html(quote)}"
                </p>
            </div>"""
            for quote in quotes
        ])

        return f"""
        <div style="padding: 30px 30px 20px 30px; background: white;">
            <h2 style="margin: 0 0 16px 0; font-size: 18px; font-weight: 600; color: #1d1d1f;">
                Key Quotes ({len(quotes)})
            </h2>
            <div style="color: #6b7280; font-size: 13px; margin-bottom: 16px;">
                Copy-pastable quotes ready for social media
            </div>
            {quotes_list}
        </div>"""

    @staticmethod
    def _generate_standalone_snippets(snippets: List[str]) -> str:
        """Generate standalone reel snippets HTML section"""
        if not snippets:
            return ''

        snippets_list = ''.join([
            f"""<div style="background: #fef3c7; border: 1px solid #fbbf24; padding: 14px 18px; margin: 10px 0; border-radius: 6px;">
                <p style="color: #78350f; margin: 0; font-size: 14px; line-height: 1.6; font-weight: 500;">
                    {HTMLEmailTemplate._escape_html(snippet)}
                </p>
            </div>"""
            for snippet in snippets
        ])

        return f"""
        <div style="padding: 20px 30px; background: white; border-top: 1px solid #e5e7eb;">
            <h2 style="margin: 0 0 12px 0; font-size: 18px; font-weight: 600; color: #1d1d1f;">
                Reel Snippets - Standalone Insights ({len(snippets)})
            </h2>
            <div style="color: #6b7280; font-size: 13px; margin-bottom: 16px;">
                Short, punchy insights (1-2 sentences) - use as individual carousel panels
            </div>
            {snippets_list}
        </div>"""

    @staticmethod
    def _generate_context_snippets(snippets: List[str]) -> str:
        """Generate context reel snippets HTML section"""
        if not snippets:
            return ''

        snippets_list = ''.join([
            f"""<div style="background: #ecfdf5; border: 1px solid #10b981; padding: 16px 20px; margin: 12px 0; border-radius: 6px;">
                <p style="color: #065f46; margin: 0; font-size: 14px; line-height: 1.7;">
                    {HTMLEmailTemplate._escape_html(snippet)}
                </p>
            </div>"""
            for snippet in snippets
        ])

        return f"""
        <div style="padding: 20px 30px 30px 30px; background: white;">
            <h2 style="margin: 0 0 12px 0; font-size: 18px; font-weight: 600; color: #1d1d1f;">
                Reel Snippets - Mini-Posts with Context ({len(snippets)})
            </h2>
            <div style="color: #6b7280; font-size: 13px; margin-bottom: 16px;">
                Longer snippets with background and application (2-4 sentences)
            </div>
            {snippets_list}
        </div>"""

    @staticmethod
    def generate_plain_text_summary(
        transcript_data: Dict[str, Any],
        topic_analysis: Dict[str, Any],
        original_file_name: str,
        dropbox_links: Dict[str, str]
    ) -> str:
        """
        Generate Instagram-focused plain text version of the summary email

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

        # Extract Instagram-focused content
        summary = topic_analysis.get('summary', '')
        quotes = topic_analysis.get('quotes', [])
        reel_snippets_standalone = topic_analysis.get('reel_snippets_standalone', [])
        reel_snippets_context = topic_analysis.get('reel_snippets_context', [])

        # Build plain text email
        text = f"""TRANSCRIPT SUMMARY
{'=' * 60}

{original_file_name}
{processed_at} | {duration} | {language}

"""

        # Summary
        if summary:
            text += f"""SUMMARY
{'-' * 60}

{summary}

"""

        # Quotes
        if quotes:
            text += f"""KEY QUOTES ({len(quotes)})
{'-' * 60}
Copy-pastable quotes ready for social media

"""
            for i, quote in enumerate(quotes, 1):
                text += f'{i}. "{quote}"\n\n'
            text += "\n"

        # Standalone Snippets
        if reel_snippets_standalone:
            text += f"""REEL SNIPPETS - STANDALONE INSIGHTS ({len(reel_snippets_standalone)})
{'-' * 60}
Short, punchy insights (1-2 sentences) - use as individual carousel panels

"""
            for i, snippet in enumerate(reel_snippets_standalone, 1):
                text += f"{i}. {snippet}\n\n"
            text += "\n"

        # Context Snippets
        if reel_snippets_context:
            text += f"""REEL SNIPPETS - MINI-POSTS WITH CONTEXT ({len(reel_snippets_context)})
{'-' * 60}
Longer snippets with background and application (2-4 sentences)

"""
            for i, snippet in enumerate(reel_snippets_context, 1):
                text += f"{i}. {snippet}\n\n"
            text += "\n"

        # Dropbox link
        dropbox_link = dropbox_links.get('summary_share_url', dropbox_links.get('txt_share_url', ''))
        if dropbox_link:
            text += f"View Full Transcript: {dropbox_link}\n\n"

        text += '-' * 60 + '\n'
        text += 'Generated with AI for Instagram content creation\n'

        return text
