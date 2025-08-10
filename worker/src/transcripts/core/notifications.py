"""
Email notification service for job completion alerts
"""

import json
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from google.cloud import secretmanager

from ..config import Config


class EmailNotificationService:
    """Handles email notifications via Gmail SMTP"""

    def __init__(self, project_id: str):
        """Initialize email notification service with Gmail credentials from Secret Manager"""
        self.project_id = project_id
        self.enabled = Config.ENABLE_EMAIL_NOTIFICATIONS
        self.recipient_email = Config.NOTIFICATION_EMAIL

        if not self.enabled:
            print("📧 Email notifications disabled")
            return

        # Initialize Secret Manager client
        self.secret_client = secretmanager.SecretManagerServiceClient()

        # Get Gmail credentials from Secret Manager
        try:
            gmail_creds = self._get_gmail_credentials()
            self.sender_email = gmail_creds["email"]
            self.app_password = gmail_creds["app_password"]
            self.smtp_server = gmail_creds.get("smtp_server", "smtp.gmail.com")
            self.smtp_port = int(gmail_creds.get("smtp_port", 587))

            print("📧 Email notifications enabled")

        except Exception as e:
            print(f"⚠️ Failed to initialize email notifications: {str(e)}")
            self.enabled = False

    def _get_gmail_credentials(self) -> dict[str, str]:
        """Retrieve Gmail credentials from Google Secret Manager"""
        secret_name = (
            f"projects/{self.project_id}/secrets/{Config.GMAIL_SECRET_NAME}/versions/latest"
        )

        try:
            response = self.secret_client.access_secret_version(request={"name": secret_name})
            secret_data = response.payload.data.decode("UTF-8")

            # Parse JSON credentials
            creds = json.loads(secret_data)

            # Validate required fields
            required_fields = ["email", "app_password"]
            for field in required_fields:
                if field not in creds:
                    raise ValueError(f"Missing required field in Gmail credentials: {field}")

            return creds

        except Exception as e:
            raise Exception(f"Failed to retrieve Gmail credentials: {str(e)}")

    def _create_job_completion_email(self, job_summary: dict[str, Any]) -> MIMEMultipart:
        """Create a professional job completion email"""
        message = MIMEMultipart("alternative")
        message["Subject"] = "🎬 Transcription Job Complete"
        message["From"] = self.sender_email
        message["To"] = self.recipient_email

        # Extract job details
        processed = job_summary.get("processed_count", 0)
        total = job_summary.get("total_count", 0)
        duration = job_summary.get("duration", 0)
        failed_files = job_summary.get("failed_files", [])

        # Convert duration to human readable format
        if duration > 3600:
            duration_str = f"{duration / 3600:.1f} hours"
        elif duration > 60:
            duration_str = f"{duration / 60:.1f} minutes"
        else:
            duration_str = f"{duration:.0f} seconds"

        # Create HTML content
        failed_section = ""
        if failed_files:
            failed_list = failed_files[:5]  # Show up to 5 failed files
            failed_items = "".join([f"<li>{file}</li>" for file in failed_list])
            if len(failed_files) > 5:
                failed_items += f"<li><em>... and {len(failed_files) - 5} more files</em></li>"

            failed_section = f"""
            <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 4px; padding: 15px; margin: 20px 0;">
                <h3 style="color: #856404; margin: 0 0 10px 0;">❌ Failed Files:</h3>
                <ul style="margin: 0; padding-left: 20px;">
                    {failed_items}
                </ul>
            </div>
            """

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                .container {{ max-width: 600px; margin: 0 auto; font-family: Arial, sans-serif; }}
                .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background-color: #f9f9f9; padding: 20px; border-radius: 0 0 8px 8px; }}
                .stats {{ background-color: white; padding: 15px; border-radius: 4px; margin: 20px 0; }}
                .stat-item {{ display: flex; justify-content: space-between; margin: 10px 0; }}
                .footer {{ color: #666; font-size: 12px; margin-top: 20px; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎬 Transcription Job Complete</h1>
                </div>
                <div class="content">
                    <div class="stats">
                        <div class="stat-item">
                            <strong>Files Processed:</strong>
                            <span>{processed}/{total}</span>
                        </div>
                        <div class="stat-item">
                            <strong>Duration:</strong>
                            <span>{duration_str}</span>
                        </div>
                        <div class="stat-item">
                            <strong>Success Rate:</strong>
                            <span>{(processed / total * 100):.1f}%</span>
                        </div>
                        <div class="stat-item">
                            <strong>Timestamp:</strong>
                            <span>{datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}</span>
                        </div>
                    </div>

                    {failed_section}

                    <div class="footer">
                        <p>This is an automated notification from your transcription pipeline.</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        # Create plain text version
        failed_text = ""
        if failed_files:
            failed_text = "\n\n❌ Failed Files:\n" + "\n".join(
                [f"  • {file}" for file in failed_files[:5]]
            )
            if len(failed_files) > 5:
                failed_text += f"\n  • ... and {len(failed_files) - 5} more files"

        text_content = f"""
🎬 Transcription Job Complete

✅ Files Processed: {processed}/{total}
⏱️ Duration: {duration_str}
📊 Success Rate: {(processed / total * 100):.1f}%
🕐 Timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}
{failed_text}

This is an automated notification from your transcription pipeline.
        """

        # Attach both HTML and text versions
        html_part = MIMEText(html_content, "html")
        text_part = MIMEText(text_content, "plain")
        message.attach(text_part)
        message.attach(html_part)

        return message

    def _create_job_error_email(self, error_message: str) -> MIMEMultipart:
        """Create a professional job error email"""
        message = MIMEMultipart("alternative")
        message["Subject"] = "🚨 Transcription Job Error"
        message["From"] = self.sender_email
        message["To"] = self.recipient_email

        # Create HTML content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                .container {{ max-width: 600px; margin: 0 auto; font-family: Arial, sans-serif; }}
                .header {{ background-color: #dc3545; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background-color: #f9f9f9; padding: 20px; border-radius: 0 0 8px 8px; }}
                .error-box {{ background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 4px; padding: 15px; margin: 20px 0; }}
                .footer {{ color: #666; font-size: 12px; margin-top: 20px; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚨 Transcription Job Error</h1>
                </div>
                <div class="content">
                    <div class="error-box">
                        <h3 style="color: #721c24; margin: 0 0 10px 0;">Error Details:</h3>
                        <p style="margin: 0; color: #721c24; font-family: monospace; word-break: break-word;">{error_message}</p>
                    </div>

                    <p><strong>Timestamp:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}</p>

                    <div class="footer">
                        <p>This is an automated error notification from your transcription pipeline.</p>
                        <p>Please check the system logs for more details.</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        # Create plain text version
        text_content = f"""
🚨 Transcription Job Error

Error Details:
{error_message}

Timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}

This is an automated error notification from your transcription pipeline.
Please check the system logs for more details.
        """

        # Attach both HTML and text versions
        html_part = MIMEText(html_content, "html")
        text_part = MIMEText(text_content, "plain")
        message.attach(text_part)
        message.attach(html_part)

        return message

    def send_job_completion(self, job_summary: dict[str, Any]) -> bool:
        """
        Send email notification for job completion

        Args:
            job_summary: Dictionary containing job completion details
                - processed_count: Number of files processed successfully
                - total_count: Total number of files attempted
                - duration: Job duration in seconds
                - failed_files: List of failed file names (optional)

        Returns:
            bool: True if notification sent successfully
        """
        if not self.enabled:
            return False

        try:
            message = self._create_job_completion_email(job_summary)

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # Enable TLS encryption
                server.login(self.sender_email, self.app_password)
                server.sendmail(self.sender_email, self.recipient_email, message.as_string())

            print(f"📧 Email notification sent to {self.recipient_email}")
            return True

        except smtplib.SMTPAuthenticationError:
            print("❌ Gmail authentication failed. Check your app password.")
            return False
        except smtplib.SMTPRecipientsRefused:
            print(f"❌ Recipient email {self.recipient_email} was refused by the server.")
            return False
        except smtplib.SMTPException as e:
            print(f"❌ SMTP error occurred: {e}")
            return False
        except Exception as e:
            print(f"❌ Failed to send email notification: {str(e)}")
            return False

    def send_job_error(self, error_message: str) -> bool:
        """
        Send email notification for job errors

        Args:
            error_message: Error description

        Returns:
            bool: True if notification sent successfully
        """
        if not self.enabled:
            return False

        try:
            message = self._create_job_error_email(error_message)

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # Enable TLS encryption
                server.login(self.sender_email, self.app_password)
                server.sendmail(self.sender_email, self.recipient_email, message.as_string())

            print(f"📧 Error email notification sent to {self.recipient_email}")
            return True

        except smtplib.SMTPAuthenticationError:
            print("❌ Gmail authentication failed. Check your app password.")
            return False
        except smtplib.SMTPRecipientsRefused:
            print(f"❌ Recipient email {self.recipient_email} was refused by the server.")
            return False
        except smtplib.SMTPException as e:
            print(f"❌ SMTP error occurred: {e}")
            return False
        except Exception as e:
            print(f"❌ Failed to send error email notification: {str(e)}")
            return False
