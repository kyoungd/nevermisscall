# Never Missed Call AI - Production Demo Guide

## 🚀 Quick Start - Production Testing

The production demo uses **real OpenAI GPT-4 and Google Maps APIs** to test the complete system functionality.

### 1. Set Up API Keys

**Get Your API Keys:**
- **OpenAI**: https://platform.openai.com/api-keys
- **Google Maps**: https://console.cloud.google.com/apis/credentials

**Configure Environment Variables:**
```bash
# Option 1: Export directly
export OPENAI_API_KEY="your_openai_api_key_here" 
export GOOGLE_MAPS_API_KEY="your_google_maps_api_key_here"

# Option 2: Create .env file
cp .env.example .env
# Edit .env with your actual API keys
```

### 2. Install Dependencies

```bash
# Ensure production dependencies are installed
./venv/bin/python -m pip install -r requirements.txt
```

### 3. Run Production Demo

```bash
# Run with real APIs
./run_production_demo.sh

# Or manually
PYTHONPATH=src ./venv/bin/python demo_console_production.py
```

## ⚠️ Important Notes

### API Costs
- **OpenAI GPT-4**: ~$0.03 per 1K tokens (typical conversation: $0.01-$0.05)
- **Google Maps**: $5 per 1K geocoding requests (free tier: 200/day)
- Budget approximately **$0.10-$0.50 per test session**

### Rate Limits
- **OpenAI**: 3,500 requests/min (Tier 1), 20,000/min (higher tiers)
- **Google Maps**: 50 requests/sec standard

### Security
- Never commit your API keys to git
- Use environment variables or .env files
- API keys are shown partially (first 8 chars) in logs

## 🧪 Testing Scenarios

### ✅ Complete Information Test
```
You: My kitchen faucet is leaking at 10027 Lurline Avenue, Chatsworth, CA 91311
AI: [Real GPT-4 analyzes the message and generates natural response]
    [Real Google Maps validates the address]
    [AI provides appointment options based on real scheduling]
```

### 🚨 Emergency Test
```
You: EMERGENCY! Pipe burst flooding basement, 22005 Devonshire Street, Chatsworth
AI: [AI detects emergency keywords and escalates priority]
    [Offers immediate/after-hours service options]
```

### 🔄 Multi-Turn Conversation
```
You: My toilet is broken
AI: [Asks for complete address naturally]

You: I'm at 10100 Variel Avenue, Chatsworth, CA 91311
AI: [Validates address and provides appointment options]

You: YES
AI: [Confirms appointment and provides details]
```

## 📊 What You'll See

### Real API Responses
- **GPT-4 Analysis**: Natural conversation responses, job type detection, urgency assessment
- **Google Maps**: Address validation, formatted addresses, geocoding confidence
- **Combined Intelligence**: AI-driven appointment scheduling with real availability

### Performance Metrics  
- **Response Times**: Real API latency (typically 1-3 seconds)
- **API Success/Failure**: Actual service availability
- **Conversation Flow**: Multi-turn dialogue management

### Error Scenarios
The demo handles real API failures gracefully:
- **Authentication errors** → Check API keys
- **Rate limit errors** → Wait and retry
- **Network errors** → Fallback to human support simulation

## 🔧 Differences from Mock Demo

| Feature | Mock Demo | Production Demo |
|---------|-----------|-----------------|
| **AI Responses** | Pre-programmed patterns | Real GPT-4 intelligence |
| **Address Validation** | Simulated success | Real Google Maps geocoding |
| **Conversation** | Template-based | Fully conversational AI |
| **Costs** | Free | Real API costs |
| **Internet Required** | No | Yes |
| **Accuracy** | Simulated | Production-level |

## 📁 File Structure

```
nmc-ai/
├── demo_console.py              # Mock demo (free)
├── demo_console_production.py   # Production demo (real APIs)
├── run_demo.sh                  # Mock demo launcher
├── run_production_demo.sh       # Production demo launcher
├── .env.example                 # Environment variables template
├── DEMO_README.md              # Mock demo documentation
└── PRODUCTION_DEMO_README.md   # This file
```

## 🎯 Use Cases

### For Development
- **Mock Demo**: Fast iteration, no costs, offline development
- **Production Demo**: End-to-end testing, API integration validation

### For Client Demos
- **Mock Demo**: Show functionality without API dependencies
- **Production Demo**: Show real AI intelligence and accuracy

### For Quality Assurance
- **Both**: Comprehensive testing of conversation flows
- **Production**: Validate real-world performance and reliability

## 🚨 Troubleshooting

### API Key Errors
```
❌ OPENAI_API_KEY environment variable is required
```
**Solution**: Set your environment variables properly

### Rate Limit Errors
```
❌ Rate limit exceeded for requests per minute
```
**Solution**: Wait 60 seconds and try again, or upgrade API plan

### Geocoding Failures  
```
❌ Google Maps API error: Invalid request
```
**Solution**: Check address format and API key permissions

### Network Issues
```
❌ Connection timeout
```
**Solution**: Check internet connection and API service status

## 💡 Best Practices

1. **Start Small**: Test with 2-3 messages first
2. **Monitor Costs**: Check API usage dashboards regularly  
3. **Use Both Demos**: Mock for development, production for validation
4. **Error Testing**: Try invalid addresses and edge cases
5. **Performance Testing**: Test during different times for latency variation

Perfect for validating that your Never Missed Call AI system works with real-world APIs and provides genuine AI intelligence!