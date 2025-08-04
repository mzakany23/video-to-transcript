"""
Automated Dropbox token management with refresh capability
"""

import os
import json
import requests
from typing import Dict, Optional
from datetime import datetime, timedelta
from google.cloud import secretmanager
import dropbox
from dropbox.exceptions import AuthError

from ..config import Config


class DropboxAuthManager:
    """Manages Dropbox authentication with automatic token refresh"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.secret_client = secretmanager.SecretManagerServiceClient()
        self._cached_client = None
        self._token_expires_at = None
        
    def get_dropbox_client(self) -> dropbox.Dropbox:
        """Get a valid Dropbox client, refreshing token if needed"""
        # Check if we have a valid cached client
        if self._cached_client and self._is_token_valid():
            return self._cached_client
            
        # Try to create client with refresh token first
        client = self._create_client_with_refresh_token()
        if client:
            self._cached_client = client
            return client
            
        # Fallback to access token
        client = self._create_client_with_access_token()
        if client:
            self._cached_client = client
            return client
            
        raise Exception("Failed to create valid Dropbox client with any method")
    
    def _is_token_valid(self) -> bool:
        """Check if current token is still valid"""
        if not self._token_expires_at:
            return False
        return datetime.now() < self._token_expires_at
    
    def _create_client_with_refresh_token(self) -> Optional[dropbox.Dropbox]:
        """Create Dropbox client using refresh token"""
        try:
            refresh_token = self._get_secret("dropbox-refresh-token")
            app_key = self._get_secret("dropbox-app-key") 
            app_secret = self._get_secret("dropbox-app-secret")
            
            if not all([refresh_token, app_key, app_secret]):
                print("🔑 Refresh token setup incomplete, missing secrets")
                return None
                
            print("🔄 Creating Dropbox client with refresh token...")
            client = dropbox.Dropbox(
                app_key=app_key,
                app_secret=app_secret,
                oauth2_refresh_token=refresh_token
            )
            
            # Test the connection
            account = client.users_get_current_account()
            print(f"✅ Connected to Dropbox with refresh token: {account.name.display_name}")
            
            # Set token expiry (refresh tokens are automatically handled by SDK)
            self._token_expires_at = datetime.now() + timedelta(hours=3)  # Conservative estimate
            
            return client
            
        except Exception as e:
            print(f"❌ Failed to create client with refresh token: {str(e)}")
            return None
    
    def _create_client_with_access_token(self) -> Optional[dropbox.Dropbox]:
        """Create Dropbox client using access token (fallback)"""
        try:
            access_token = self._get_secret("dropbox-access-token")
            if not access_token:
                print("❌ No access token available")
                return None
                
            print("🔑 Creating Dropbox client with access token...")
            client = dropbox.Dropbox(access_token)
            
            # Test the connection
            account = client.users_get_current_account()
            print(f"✅ Connected to Dropbox with access token: {account.name.display_name}")
            
            # Access tokens typically expire in 4 hours
            self._token_expires_at = datetime.now() + timedelta(hours=3)
            
            return client
            
        except AuthError as e:
            print(f"❌ Access token authentication failed: {str(e)}")
            if "expired_access_token" in str(e):
                print("🔄 Access token expired, attempting refresh...")
                return self._refresh_access_token()
            return None
        except Exception as e:
            print(f"❌ Failed to create client with access token: {str(e)}")
            return None
    
    def _refresh_access_token(self) -> Optional[dropbox.Dropbox]:
        """Refresh the access token using refresh token"""
        try:
            refresh_token = self._get_secret("dropbox-refresh-token")
            app_key = self._get_secret("dropbox-app-key")
            app_secret = self._get_secret("dropbox-app-secret")
            
            if not all([refresh_token, app_key, app_secret]):
                print("❌ Cannot refresh token: missing refresh token or app credentials")
                return None
            
            print("🔄 Refreshing access token...")
            
            # Make refresh token request
            response = requests.post(
                'https://api.dropboxapi.com/oauth2/token',
                data={
                    'grant_type': 'refresh_token',
                    'refresh_token': refresh_token
                },
                auth=(app_key, app_secret)
            )
            
            if response.status_code != 200:
                print(f"❌ Token refresh failed: {response.status_code} - {response.text}")
                return None
            
            token_data = response.json()
            new_access_token = token_data.get('access_token')
            
            if not new_access_token:
                print("❌ No access token in refresh response")
                return None
            
            # Save new access token to Secret Manager
            self._save_secret("dropbox-access-token", new_access_token)
            print("✅ Access token refreshed and saved")
            
            # Create client with new token
            client = dropbox.Dropbox(new_access_token)
            account = client.users_get_current_account()
            print(f"✅ Connected with refreshed token: {account.name.display_name}")
            
            self._token_expires_at = datetime.now() + timedelta(hours=3)
            return client
            
        except Exception as e:
            print(f"❌ Error refreshing access token: {str(e)}")
            return None
    
    def _get_secret(self, secret_name: str) -> Optional[str]:
        """Get secret from Google Secret Manager"""
        try:
            name = f"projects/{self.project_id}/secrets/{secret_name}/versions/latest"
            response = self.secret_client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8").strip()
        except Exception as e:
            print(f"⚠️ Could not get secret {secret_name}: {str(e)}")
            return None
    
    def _save_secret(self, secret_name: str, secret_value: str):
        """Save secret to Google Secret Manager"""
        try:
            secret_id = f"projects/{self.project_id}/secrets/{secret_name}"
            version = self.secret_client.add_secret_version(
                request={
                    "parent": secret_id,
                    "payload": {"data": secret_value.encode("UTF-8")}
                }
            )
            print(f"✅ Updated secret: {secret_name}")
        except Exception as e:
            print(f"❌ Failed to save secret {secret_name}: {str(e)}")
    
    def validate_and_refresh_if_needed(self) -> bool:
        """Validate current token and refresh if needed"""
        try:
            client = self.get_dropbox_client()
            # Test with a simple API call
            client.users_get_current_account()
            print("✅ Dropbox token is valid")
            return True
        except Exception as e:
            print(f"❌ Token validation failed: {str(e)}")
            return False