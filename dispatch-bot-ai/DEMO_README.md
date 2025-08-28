# Never Missed Call AI - Interactive Demo Console

## Quick Start

1. **Run the demo:**
   ```bash
   ./run_demo.sh
   ```

2. **Or manually:**
   ```bash
   PYTHONPATH=src ./venv/bin/python demo_console.py
   ```

## How It Works

The demo console simulates a real customer calling your plumbing business. You type messages as the customer would, and the AI processes them through the complete Never Missed Call system:

1. **Message Parsing** - AI understands the problem and extracts key information
2. **Address Validation** - Checks if the location is in your service area  
3. **Appointment Scheduling** - Offers available time slots with cost estimates
4. **Conversation Management** - Handles multi-turn dialogues naturally

## Example Conversations

### 🔧 Basic Faucet Repair
```
You: My kitchen faucet is leaking at 10027 Lurline Avenue, Chatsworth, CA 91311
AI:  I can help with your kitchen faucet leak! I have an appointment available 
     Friday, August 8 from 1:00 PM - 3:00 PM. The estimated cost is $100 - $250 
     for Faucet repair or replacement. Reply YES to confirm this appointment or NO 
     if you'd like different options.

You: YES
AI:  ✅ Appointment confirmed! Your plumber will arrive Friday, August 8 between 
     1:00 PM - 3:00 PM. Estimated cost: $100 - $250. Appointment ID: PLB-A1B2C3
```

### 🚨 Emergency Situation
```
You: EMERGENCY! Pipe burst in basement flooding everywhere! 22005 Devonshire Street, Chatsworth
AI:  I understand this is an emergency! A burst pipe with flooding requires immediate 
     attention. I have an emergency plumber available today at 3:00 PM - 5:00 PM. 
     Emergency rate: $375 - $900. Reply YES for immediate service or CALL for phone support.
```

### 🔄 Multi-Turn Conversation (Missing Info)
```
You: My toilet won't flush properly
AI:  I can help with your toilet issue! To schedule an appointment, I'll need your 
     complete address (street number, street name, city, and state). What's your address?

You: I'm at 10100 Variel Avenue, Chatsworth, CA 91311
AI:  Perfect! I can fix your toilet flush problem. I have an appointment available 
     Friday, August 8 from 1:00 PM - 3:00 PM. The estimated cost is $150 - $350 
     for toilet repair or replacement. Reply YES to confirm or NO for other options.
```

## Test Scenarios to Try

### ✅ Complete Information
- `"Leaky faucet at 10027 Lurline Avenue, Chatsworth, CA 91311"`
- `"Toilet clogged, need help at 10100 Variel Avenue, Chatsworth, CA"`
- `"Kitchen sink drain backing up, 22005 Devonshire Street, Chatsworth 91311"`

### ❓ Missing Information  
- `"My toilet is broken"` (missing address)
- `"Need a plumber at my house"` (missing problem details)
- `"Pipe problem"` (missing both address and details)

### 🚨 Emergency Keywords
- `"EMERGENCY pipe burst flooding basement 21050 Plummer Street, Chatsworth"`
- `"Urgent! Water everywhere! 20801 Rinaldi Street, Chatsworth"` 
- `"Help! Sewage backup in bathroom 10027 Lurline Avenue, Chatsworth"`

### 🏠 Different Job Types
- `"Faucet dripping constantly"` → Faucet repair
- `"Toilet overflowing"` → Toilet repair  
- `"Drain completely clogged"` → Drain cleaning
- `"Pipe leaking under sink"` → Pipe repair

## Console Commands

- **`quit`** - Exit the demo
- **`reset`** - Start a new conversation with different random data
- **Ctrl+C** - Force exit

## What You'll See

### 📋 AI Understanding
- **Job Type**: What kind of plumbing work is needed
- **Address**: Extracted and validated location  
- **Urgency**: Normal, urgent, or emergency priority
- **Service Area**: Whether location is within coverage area

### 📅 Appointment Details  
- **Available Slots**: Next available appointment times
- **Cost Estimates**: Price ranges for the specific job type
- **Confirmation Process**: YES/NO response handling

### 📞 Conversation Flow
- **Current Stage**: Information gathering, confirming, complete, etc.
- **Next Steps**: What the customer should do next
- **Timeout Handling**: How long the conversation stays active

## Behind the Scenes

The demo uses **mock services** that simulate:
- **OpenAI GPT-4** message parsing and understanding
- **Google Maps** address validation and geocoding  
- **Scheduling Engine** appointment slot generation
- **Real-time** conversation state management

The actual system integrates with real APIs for production use.

## Business Scenarios

Each demo session randomly generates:
- **Business Name**: Chatsworth Plumbing Pro, West Valley Plumbing, etc.
- **Business Location**: Real Chatsworth, CA addresses 
- **Service Area**: 20-30 mile radius around business
- **Phone Numbers**: Realistic customer phone numbers
- **Conversation IDs**: Unique identifiers for tracking

## Realistic Schedule (Based on real_addresses.md)

The demo uses a realistic schedule where:
- **8:00 AM - 10:00 AM**: Booked (Chatsworth Transportation Center)
- **10:00 AM - 12:00 PM**: Booked (Oakwood Memorial Park Cemetery)  
- **12:00 PM - 1:00 PM**: Lunch break
- **1:00 PM - 3:00 PM**: ✅ **Available**
- **3:00 PM - 5:00 PM**: ✅ **Available**
- **5:00 PM - 7:00 PM**: ✅ **Available** (emergency/after hours)

This shows how the AI handles realistic scheduling constraints where only afternoon slots are available.

Perfect for testing different customer interaction patterns and seeing how the AI handles various scenarios!