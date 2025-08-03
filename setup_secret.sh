#!/bin/bash
# Script to set up OpenAI API key in Google Secret Manager
# Run this script with your actual OpenAI API key

echo "🔐 Setting up OpenAI API key in Google Secret Manager..."

if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ Error: OPENAI_API_KEY environment variable not set"
    echo "Usage: OPENAI_API_KEY='your-key-here' ./setup_secret.sh"
    exit 1
fi

echo "Adding OpenAI API key to Secret Manager..."
echo -n "$OPENAI_API_KEY" | gcloud secrets versions add openai-api-key --data-file=-

if [ $? -eq 0 ]; then
    echo "✅ OpenAI API key successfully stored in Secret Manager"
    echo "🔍 Verifying secret..."
    gcloud secrets versions list openai-api-key
else
    echo "❌ Failed to store API key"
    exit 1
fi

echo "🎉 Secret setup complete!"