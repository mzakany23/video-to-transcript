# Worker Changelog

All notable changes to the transcription worker service will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.0] - 2025-11-02

### Changed
- **MAJOR: Instagram-First Summary Redesign** - Complete overhaul based on critical user feedback
  - Goal: Optimize for Instagram carousel reels, not comprehensive analysis
  - Removed: Timestamps (didn't line up, not useful for Instagram)
  - Removed: Detailed topic breakdown (overkill for 20-min podcasts)
  - Removed: Action items (not used)
  - Simplified output to 3 key sections:
    1. Summary (one compelling paragraph, no POV mentions)
    2. Quotes (max 5, quality over quantity, Instagram-ready)
    3. Reel Snippets (both standalone and context formats)
- **Reel Snippets - Two Formats**:
  - Standalone Insights: Short punchy 1-2 sentence insights for carousel panels
  - Mini-Posts with Context: 2-4 sentence snippets with background and application
- **Cleaner Email Format** - Simplified HTML template to match new structure
  - No timestamps, no ordered lists, no complexity
  - Copy-pastable content ready for social media
  - Focus on actionable Instagram content

### Technical
- Completely rewrote analysis prompt in topic_analyzer.py for Instagram focus
- Updated _format_analysis to return new JSON structure
- Updated HTMLEmailTemplate.generate_summary_email for new sections
- Updated generate_plain_text_summary for Instagram content
- Modified generate_summary_email.py script to work with new format

**Impact**: Reduces time to create Instagram content from transcripts. Provides exactly what users need: quotable moments and copy-pastable reel snippets. No more wading through timestamps and detailed breakdowns.

**Breaking Change**: Email format completely changed. Old analysis JSON structure is incompatible with new version.

## [1.3.7] - 2025-11-02

### Fixed
- **CRITICAL: 100% Accurate Timestamps** - Include ALL transcript segments in analysis prompt
  - Previously: Only first 50 segments (~3-5 min) had timestamps, model guessed the rest
  - Now: All segments (entire transcript) included for accurate topic boundary detection
  - Result: Timestamps are now accurate to the second across entire transcript

### Changed
- **Better Quote Selection** - Enhanced prompt to avoid bland, generic quotes
  - Explicitly avoid: Pleasantries, greetings, thank-yous, generic statements
  - Choose only: Wisdom, insights, metaphors, profound statements, memorable phrasing
  - Example good quote: "The mind is a wonderful servant, but a terrible master"
  - Example bad quote: "Your thoughtful shares have meant so much to me"
- **Smarter Action Item Detection** - Context-aware filtering to avoid false positives
  - Distinguishes between real commitments vs audience calls-to-action
  - Excludes: "Download my workbook", "Visit my website", "Send me a message"
  - Includes only: Actual tasks assigned to participants in meetings/calls
  - Podcasts/monologues now correctly show 0 action items (not audience CTAs)

### Added
- **First-Person Narrative** - Smart point-of-view handling for summaries
  - Single-speaker podcasts now use first person ("I discuss" vs "Jo discusses")
  - Conversations/interviews use third person or speaker names
  - Makes summaries more personal and engaging

### Technical
- Removed segment[:50] truncation in topic_analyzer.py for full timestamp context
- Updated default model to `gpt-5` for superior reasoning and accuracy
- Added quote quality criteria with specific examples to prompt

**Impact**: This fixes the #1 user complaint about incorrect timestamps. Combined with GPT-5, summaries are now significantly more accurate and engaging.

## [1.3.6] - 2025-10-13

### Changed
- **CRITICAL: Enhanced prompt with hallucination prevention and deeper analysis**
  - Added explicit hallucination guardrails to prevent invented names, quotes, or facts
  - Increased transcript sample from 12k to 20k characters for better context
  - Stricter topic granularity: 1 topic per 5-7 minutes (12-18 topics for 73-min content)
  - Demand 5-8 key insights per topic (not just 2-3)
  - Require specific techniques, methods, and step-by-step processes
  - More substantive quotes (2-6 per topic, must be meaningful)
  - Explicit instructions to NEVER invent information not in transcript

### Fixed
- Hallucinations (e.g., making up speaker names like "Lena")
- Too few topics for long content (was 6 for 73 min, now will be 12-18)
- Shallow insights that don't teach anything actionable
- Missing specific techniques and frameworks

### Technical
- Increased full_text limit from 12,000 to 20,000 characters in prompt
- Added topic count formulas: <15min=5-8, 15-45min=8-12, 45-75min=12-18, >75min=15-20+
- Added dedicated hallucination prevention section with explicit constraints
- Updated insight requirements to capture techniques, principles, and transformations

**Recommended**: Update GitHub secret `OPENAI_SUMMARIZATION_MODEL=gpt-5` for maximum quality

## [1.3.5] - 2025-10-13

### Changed
- **MAJOR: Completely redesigned analysis prompt for deep insights and wisdom extraction**
  - Transforms summaries from generic "they discussed X" to actionable strategic insights
  - Extract 2-3x more topics (10-15 for 1-hour content vs 3-5 previously)
  - Captures stories, anecdotes, and personal experiences
  - Identifies and lists all resources mentioned (books, tools, techniques, frameworks)
  - Generates 5-10 key takeaways with strategic wisdom
  - Detects content type (podcast, meeting, coaching call, interview, etc.)
  - Much more granular topics (~5-8 min per topic for better navigation)
  - Deeper insights focus on WHY it matters and HOW to apply it
  - Goes beyond summarization to true analysis and wisdom extraction

### Added
- **New email sections**: Stories & Anecdotes, Resources Mentioned
- **Key Takeaways section**: 5-10 strategic insights from the entire conversation
- **Content Type identification**: Automatically detects if it's a podcast, meeting, etc.
- **Collapsible sections now open by default**: All content visible immediately
- Enhanced topic analysis with themes per topic
- Better quote selection (captures wisdom, not just random text)

### Technical Details
- Completely rewrote system message to prime for analytical thinking
- Increased prompt from ~500 to ~2000 characters with detailed instructions
- Added support for: stories, resources, themes, key_takeaways, content_type fields
- Updated HTML template to display new rich fields
- Added `open` attribute to all `<details>` tags for better UX

### Example Improvements
Before (73-min podcast): 4 generic topics, 0 resources, generic summary
After (73-min podcast): Expected 12-15 detailed topics, resources captured, strategic insights

Before (15-min meeting): "They discussed mobile app launch"
After (15-min meeting): "Adopt an MVP approach: ship core features first to reduce risk and improve quality"

## [1.3.4] - 2025-10-13

### Changed
- **Upgraded to GPT-5-mini for transcript summarization**
  - Switched from gpt-4o-mini to gpt-5-mini for much better quality
  - Provides detailed, nuanced summaries with excellent timestamp precision
  - Better context understanding and quote extraction
  - 400k token context window for holistic transcript analysis
  - Configurable via `OPENAI_SUMMARIZATION_MODEL` environment variable
  - Cost: ~$0.02 per hour of transcript (still very reasonable)

## [1.3.3] - 2025-10-13

### Fixed
- Fixed "Copy All Timestamps" functionality in summary emails
  - JavaScript buttons don't work in email clients (Gmail, Outlook strip JS for security)
  - Replaced JavaScript button with selectable text box using `<pre>` tag
  - All timestamps now displayed with proper line breaks in a scrollable area
  - Users can click to select all timestamps, then copy with Cmd+C/Ctrl+C
  - Removed individual copy buttons from topic cards (JS-based)

## [1.3.2] - 2025-10-13

### Fixed
- **Critical**: Fixed summary emails not being sent to users
  - Topic analysis was being generated but not passed to email notification function
  - `dropbox_handler.py` now includes topic_analysis in returned results dict
  - `main.py` now correctly checks upload_result for topic_analysis
  - Users will now receive premium HTML summary emails after successful transcription

## [1.3.1] - 2025-10-13

### Fixed
- **Critical**: Fixed Dropbox download to use streaming for large files (1-2GB recordings)
  - Now downloads in 4MB chunks instead of loading entire file into memory
  - Prevents out-of-memory issues with 1-2 hour recordings
  - Added progress logging every 100MB for large files
  - Fallback to direct download for smaller files if streaming not available

## [1.3.0] - 2025-10-13

### Added
- **Premium HTML Summary Emails**: Users now receive beautifully formatted HTML emails with transcript summaries
  - Sleek, responsive email design with collapsible sections for topics
  - Executive summary, main themes, and topic cards with timestamps
  - Action items and decisions highlighted in colored sections
  - **"Copy All Timestamps" button** - One-click to copy all timestamps with titles for easy pasting into podcasts, Instagram, or other apps
  - Individual copy buttons for each timestamp
  - Plain text fallback for email clients that don't support HTML
  - Direct link to full transcript in Dropbox
- **Email Recipient Segmentation**: Separate email lists for different notification types
  - `DEVELOPER_EMAILS` env var: Receives debug emails (job start, completion, errors)
  - `USER_EMAILS` env var: Receives only polished summary emails
  - Allows developers to get technical notifications while users only see finished results

### Changed
- Existing job completion/error/start emails now only sent to developer email list
- Summary emails are sent to user email list after successful transcription (if topic analysis available)
- Summary email subject line: "Summary Ready: [filename]"

### Technical Details
- New modules:
  - `src/transcripts/core/html_email_template.py` - HTML email template generator with responsive design
- Updated modules:
  - `src/transcripts/core/notifications.py` - Added `send_summary_email()` method and email list segmentation
  - `main.py` - Integrated summary email sending after successful transcription
  - `src/transcripts/config.py` - Added `DEVELOPER_EMAILS` and `USER_EMAILS` configuration
- Terraform changes:
  - Added `developer_emails` and `user_emails` variables to `terraform/main.tf`
  - `notification_emails` variable now deprecated (use new vars instead)

### Migration Guide
Update your `terraform.tfvars` to use the new email segmentation:

```hcl
# New (recommended):
developer_emails = ["mzakany@gmail.com"]
user_emails = ["jrpvla@gmail.com", "mzakany@gmail.com"]

# Old (still works as fallback):
# notification_emails = ["mzakany@gmail.com"]
```

## [1.2.1] - 2025-10-13

### Fixed
- Topic summarization now works in production - OpenAI API key is properly passed from Secret Manager to TopicAnalyzer
- DropboxHandler now accepts and uses the OpenAI API key for topic analysis

## [1.2.0] - 2025-10-12

### Added
- **Topic Summarization**: AI-powered topic analysis with GPT-4o-mini
  - Automatically identifies 3-8 topics with timestamps
  - Extracts key points, quotes, action items, and decisions
  - Generates executive summary of entire transcript
  - Configurable model via `OPENAI_SUMMARIZATION_MODEL` env var (default: `gpt-4o-mini`)
  - Can be disabled via `ENABLE_TOPIC_SUMMARIZATION` env var
- **Enhanced Timestamps**: Human-readable timestamp formatting
  - Timestamps now display as `HH:MM:SS` instead of decimal seconds
  - Duration formatting with appropriate units (seconds/minutes/hours)
  - Timestamp range formatting for segments
- **Summary Output Files**: New output formats for better readability
  - `_SUMMARY.txt` - Plain text summary with topics and timestamps
  - `_SUMMARY.md` - Markdown summary with formatting and links
  - Enhanced full transcript with improved timestamp readability
- **Test Infrastructure**: Comprehensive test suite
  - 16 unit tests for timestamp utilities
  - Integration test for E2E pipeline validation
  - Organized test structure: `tests/unit/` and `tests/integration/`
  - Updated Makefile with `test`, `test-unit`, `test-integration` targets

### Changed
- JSON output now includes `topic_analysis` field with structured topic data
- Full transcript TXT format enhanced with human-readable timestamps
- Test organization improved with proper unit/integration separation

### Technical Details
- New modules:
  - `src/transcripts/utils/timestamp_formatter.py` - Timestamp utilities
  - `src/transcripts/core/topic_analyzer.py` - GPT-powered topic analysis
  - `src/transcripts/core/summary_formatter.py` - Summary generation
- Updated modules:
  - `src/transcripts/core/dropbox_handler.py` - Integrated topic analysis
  - `src/transcripts/config.py` - Added summarization configuration
- Cost: ~$0.01-0.03 per 30-minute transcript with gpt-4o-mini

## [1.1.1] - 2025-10-12

### Fixed
- Job start email now displays correct file size instead of 0.0 MB
- Read TARGET_FILE_SIZE_MB environment variable from webhook

## [1.1.0] - 2025-10-12

### Added
- Audio chunking support for unlimited file sizes (processes files >25MB)
- Job start email notifications to track processing progress
- Sentry error tracking integration for production monitoring
- Semantic versioning for Docker images

### Fixed
- Email recipient parsing - multiple recipients now work correctly
- OpenAI API 413 errors for large audio files (>25MB)
- Compression target reduced from 25MB to 19MB for reliability

### Changed
- Enhanced error handling and logging
- Improved transcription processing pipeline

## [1.0.1] - 2025-08-23

### Added
- Support for all required secrets in configuration
- Generic project configuration (removed hardcoded references)

### Fixed
- Secret management - proper handling of OpenAI and Dropbox credentials
- Folder path synchronization with webhook service

### Changed
- Improved error handling and troubleshooting

## [1.0.0] - 2025-08-09

### Added
- Initial transcription worker implementation
- Email notification system with support for multiple recipients
- Toggle functionality for email notifications
- SMS notification capabilities
- Complete serverless transcription pipeline
- Support for multiple audio/video formats

### Fixed
- Pipeline workflow issues
- Dependency management improvements

[1.2.1]: https://github.com/mzakany23/video-to-transcript/releases/tag/worker-v1.2.1
[1.2.0]: https://github.com/mzakany23/video-to-transcript/releases/tag/worker-v1.2.0
[1.1.1]: https://github.com/mzakany23/video-to-transcript/releases/tag/worker-v1.1.1
[1.1.0]: https://github.com/mzakany23/video-to-transcript/releases/tag/worker-v1.1.0
[1.0.1]: https://github.com/mzakany23/video-to-transcript/releases/tag/worker-v1.0.1
[1.0.0]: https://github.com/mzakany23/video-to-transcript/releases/tag/worker-v1.0.0
