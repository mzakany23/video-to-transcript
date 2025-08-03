# Phase 2 Infrastructure Deployment Guide

## Overview
This Phase 2 infrastructure sets up serverless transcription processing using:
- **Cloud Functions** for event-driven processing
- **Cloud Storage** for temporary file handling
- **Pub/Sub** for event messaging
- **Secret Manager** for secure API key storage

## Prerequisites
- ✅ Phase 1 completed (service account created)
- ✅ Google Cloud CLI authenticated
- ✅ Terraform initialized
- ✅ OpenAI API key available

## Infrastructure Components

### Core Services (20 resources):
1. **APIs Enabled** (8 total):
   - Cloud Functions, Cloud Build, Pub/Sub, Storage, Secret Manager, Eventarc

2. **Cloud Storage Buckets** (2):
   - `jos-transcripts-transcription-temp` - Temporary file processing (auto-delete after 1 day)
   - `jos-transcripts-function-source` - Cloud Function source code

3. **Pub/Sub** (3 resources):
   - `transcription-events` topic - Main event stream
   - `transcription-processor` subscription - Function trigger
   - `transcription-dead-letter` topic - Failed message handling

4. **Cloud Function**:
   - `transcription-processor` - Python 3.11 function
   - Triggered by Pub/Sub messages
   - 9-minute timeout, 1GB memory
   - Auto-scaling (0-10 instances)

5. **Secret Manager**:
   - `openai-api-key` secret (value set separately)

6. **IAM Roles** (5 additional):
   - Cloud Functions invoker
   - Pub/Sub publisher/subscriber  
   - Secret Manager accessor
   - Storage admin

## Deployment Steps

### 1. Deploy Infrastructure
```bash
cd terraform
terraform apply
```

### 2. Set OpenAI API Key in Secret Manager
```bash
# Replace YOUR_OPENAI_API_KEY with your actual key
echo -n "YOUR_OPENAI_API_KEY" | gcloud secrets versions add openai-api-key --data-file=-
```

### 3. Verify Deployment
```bash
# Check Cloud Function status
gcloud functions list --gen2

# Check Pub/Sub topics
gcloud pubsub topics list

# Check storage buckets
gcloud storage buckets list

# Verify secret
gcloud secrets versions list openai-api-key
```

## Testing the Infrastructure

### Send Test Message to Pub/Sub
```bash
# Test message with file metadata
gcloud pubsub topics publish transcription-events --message='{
  "id": "test_file_123",
  "name": "test_audio.mp3", 
  "size": "1048576"
}'
```

### Monitor Function Logs
```bash
gcloud functions logs read transcription-processor --gen2 --limit=50
```

## Architecture Flow

```
Google Drive File Upload
         ↓
    [Your Code] → Pub/Sub Topic (transcription-events)
         ↓
  Cloud Function (transcription-processor)
         ↓
1. Download from Drive → Cloud Storage (temp)
2. Get OpenAI key → Secret Manager  
3. Transcribe → OpenAI Whisper API
4. Upload results → Google Drive (processed)
         ↓
    Job Complete ✅
```

## Cost Considerations

- **Cloud Functions**: Pay per invocation (~$0.40/million invocations)
- **Cloud Storage**: Minimal (files deleted after 1 day)
- **Pub/Sub**: ~$0.40/million messages
- **Secret Manager**: ~$0.06/month per secret

## Security Features

- ✅ Service account with minimal required permissions
- ✅ API keys stored in Secret Manager (not in code)
- ✅ Automatic cleanup of temporary files
- ✅ Dead letter queue for failed processing
- ✅ VPC-native networking (default)

## Next Steps (Phase 3)

1. Connect Google Drive events to Pub/Sub
2. Implement Google Drive webhook/push notifications
3. Test end-to-end flow
4. Add monitoring and alerting

## Troubleshooting

### Function Not Triggering
```bash
# Check Pub/Sub subscription
gcloud pubsub subscriptions describe transcription-processor

# Check function event trigger
gcloud functions describe transcription-processor --gen2 --region=us-east2
```

### Permission Issues
```bash
# Verify service account permissions
gcloud projects get-iam-policy jos-transcripts --flatten="bindings[].members" --filter="bindings.members:transcription-service@*"
```

### Secret Access Issues
```bash
# Test secret access
gcloud secrets versions access latest --secret="openai-api-key"
```