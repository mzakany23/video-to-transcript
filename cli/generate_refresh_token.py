#!/usr/bin/env python3
"""
Generate Dropbox refresh token for long-term authentication
"""

import sys
import os
import webbrowser
from urllib.parse import urlencode, parse_qs
import requests

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'worker', 'src'))
from transcripts.config import Config

def generate_refresh_token():
    """Generate a refresh token using OAuth2 authorization code flow"""
    
    app_key = Config.DROPBOX_APP_KEY
    app_secret = input("Enter your Dropbox App Secret: ").strip()
    
    if not app_key or not app_secret:
        print("❌ App key and secret are required")
        return
    
    # Step 1: Get authorization URL
    auth_url = "https://www.dropbox.com/oauth2/authorize"
    redirect_uri = "http://localhost:8080"  # You can use any valid URI for this script
    
    params = {
        'client_id': app_key,
        'response_type': 'code',
        'redirect_uri': redirect_uri,
        'token_access_type': 'offline'  # This requests a refresh token
    }
    
    authorization_url = f"{auth_url}?{urlencode(params)}"
    
    print("🚀 Opening browser for Dropbox authorization...")
    print(f"🔗 Authorization URL: {authorization_url}")
    
    webbrowser.open(authorization_url)
    
    # Step 2: Get authorization code from user
    print("\n📋 After authorizing, you'll be redirected to a URL like:")
    print(f"   {redirect_uri}?code=AUTHORIZATION_CODE&state=...")
    
    auth_code = input("\n📝 Enter the authorization code from the redirect URL: ").strip()
    
    if not auth_code:
        print("❌ Authorization code is required")
        return
    
    # Step 3: Exchange code for tokens
    token_url = "https://api.dropboxapi.com/oauth2/token"
    
    data = {
        'code': auth_code,
        'grant_type': 'authorization_code',
        'client_id': app_key,
        'client_secret': app_secret,
        'redirect_uri': redirect_uri
    }
    
    print("🔄 Exchanging authorization code for tokens...")
    
    response = requests.post(token_url, data=data)
    
    if response.status_code != 200:
        print(f"❌ Token exchange failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return
    
    tokens = response.json()
    
    if 'refresh_token' not in tokens:
        print("❌ No refresh token received. Make sure token_access_type=offline was included.")
        return
    
    print("\n✅ Tokens generated successfully!")
    print(f"🔑 Access Token: {tokens['access_token'][:20]}...")
    print(f"🔄 Refresh Token: {tokens['refresh_token'][:20]}...")
    
    print("\n📝 To use these tokens, set these environment variables:")
    print(f"export DROPBOX_ACCESS_TOKEN='{tokens['access_token']}'")
    print(f"export DROPBOX_REFRESH_TOKEN='{tokens['refresh_token']}'")
    print(f"export DROPBOX_APP_SECRET='{app_secret}'")
    
    print("\n🔐 Or store in Google Secrets:")
    print(f"gcloud secrets create dropbox-access-token --data-file=- --project='jos-transcripts' <<< '{tokens['access_token']}'")
    print(f"gcloud secrets create dropbox-refresh-token --data-file=- --project='jos-transcripts' <<< '{tokens['refresh_token']}'")
    print(f"gcloud secrets create dropbox-app-secret --data-file=- --project='jos-transcripts' <<< '{app_secret}'")

if __name__ == "__main__":
    generate_refresh_token()