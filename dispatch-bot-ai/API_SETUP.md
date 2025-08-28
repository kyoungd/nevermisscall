# API Setup Guide

This guide will help you get the required API keys for Never Missed Call AI Phase 1.

## Required API Keys

### 1. Google Maps API Key 🗺️

**What it's used for**: Address geocoding and service area validation

**How to get it**:
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the following APIs:
   - **Geocoding API** (for address validation)
   - **Distance Matrix API** (for future travel time calculations)
4. Go to "Credentials" → "Create Credentials" → "API Key"
5. Copy your API key

**Security**: Restrict your API key to only the APIs you need and your domain/IP.

### 2. OpenAI API Key 🤖

**What it's used for**: Natural language processing to extract customer intent and address information

**How to get it**:
1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign up for an account or sign in
3. Go to [API Keys](https://platform.openai.com/api-keys)
4. Click "Create new secret key"
5. Copy your API key (starts with `sk-`)

**Note**: OpenAI API requires payment. You'll need to add a payment method to your account.

## Configuration

### Step 1: Add Keys to Environment File

1. Open the `.env` file in your project root
2. Add your API keys:

```bash
# API Keys - REPLACE WITH YOUR ACTUAL KEYS
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here
OPENAI_API_KEY=sk-your_openai_api_key_here
```

3. Save the file

### Step 2: Verify Configuration

Run the environment checker:

```bash
./venv/bin/python check_environment.py
```

You should see:
```
✅ All required API keys are configured!
   - Google Maps API Key: ✅ Set
   - OpenAI API Key: ✅ Set
```

## Security Best Practices

1. **Never commit API keys to git** - The `.env` file is already in `.gitignore`
2. **Use environment-specific keys** - Different keys for development/production
3. **Set up API key restrictions** in Google Cloud Console
4. **Monitor API usage** to avoid unexpected charges
5. **Rotate keys regularly** for production systems

## Troubleshooting

### Google Maps API Issues
- Make sure you've enabled the Geocoding API
- Check that your API key isn't restricted to other domains
- Verify you have billing enabled (required for most Google APIs)

### OpenAI API Issues
- Ensure your API key starts with `sk-`
- Check that you have sufficient credits/billing set up
- Verify you're using a valid model (we use `gpt-4` by default)

### Environment Issues
- Make sure there are no spaces around the `=` in your `.env` file
- Check that the `.env` file is in the project root directory
- Restart any running services after changing environment variables

## Testing Without API Keys

For development without API keys, some tests will be skipped, but the core validation logic will still work. However, you'll need the actual keys for:

- Address geocoding and validation
- AI-powered message parsing
- Full end-to-end conversation flows

## Cost Estimates (Phase 1)

**Google Maps API**:
- Geocoding: $5 per 1,000 requests
- Phase 1 usage: ~1-2 requests per conversation

**OpenAI API**:
- GPT-4: ~$0.03-0.06 per conversation
- Phase 1 usage: 1-2 API calls per conversation

For development and testing, costs should be minimal (under $10/month for moderate usage).