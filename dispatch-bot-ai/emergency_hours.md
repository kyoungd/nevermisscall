# Emergency Phone Call & Working Hours Logic

## Core Operating Hours Structure

### Working Hours vs Phone Hours
- **Working Hours:** 7:00 AM - 6:00 PM (when contractor physically does jobs)
- **Phone Hours:** 24/7 (AI always answers for emergencies)

## Time-Based Emergency Logic

### During Working Hours (7 AM - 6 PM)
- **Regular calls:** Normal scheduling at standard rates
- **Emergency calls:** Immediate dispatch possible at 1.5x-2x rates
- **Response:** "We can have someone there in 1-2 hours"

### Evening Window (6 PM - 7:30 PM) 
- **Emergency calls:** Still accept for same-day service
- **Rate:** 2x-2.5x emergency rates
- **Response:** "We can have someone out tonight for emergency rates ($450 vs normal $200)"
- **Non-emergency:** Schedule for next morning

### Late Evening (7:30 PM - 6 AM)
- **True Emergency Only:** AI filters for genuine emergencies
- **Customer Choice Required:** Must accept emergency rates to proceed
- **Emergency Rate:** 2.5x-3x normal rates + potential call-out fee

## AI Emergency Decision Tree

### Step 1: Emergency Detection
```
AI Keywords Detection:
- Plumbing: "flooding", "burst pipe", "no hot water", "sewage backup"
- Electrical: "sparks", "smoke", "power out", "exposed wires"  
- HVAC: "no heat", "no cooling", "gas smell", "carbon monoxide"
- Locksmith: "locked out", "break-in", "security"
- Garage Door: "won't close", "stuck open", "spring broken"
```

### Step 2: Time-Based Response Logic

#### 7:30 PM - 6:00 AM Emergency Flow:
```
1. Emergency detected → Quote emergency rate
   "This sounds like an emergency. We can dispatch someone 
   immediately for emergency service ($600 vs normal $200). 
   Confirm emergency rate?"

2a. Customer ACCEPTS → Alert contractor + dispatch
    "Confirmed - tech will be there within 90 minutes"

2b. Customer DECLINES → Schedule priority morning slot  
    "We can get you the first appointment at 7 AM tomorrow 
    for regular rates ($200). Here's what to do until then..."
```

#### Non-Emergency After Hours:
```
"We can schedule you first thing tomorrow:
- 6:00 AM priority slot: $300 (1.5x rate)  
- 7:00 AM early slot: $250 (1.25x rate)
- 8:00 AM regular slot: $200 (normal rate)"
```

## Pricing Structure

### Emergency Rate Multipliers
| Time Period | Emergency Rate | Notes |
|-------------|---------------|--------|
| 7 AM - 6 PM | 1.5x-2x | During work hours emergency |
| 6 PM - 7:30 PM | 2x-2.5x | Evening emergency window |  
| 7:30 PM - 6 AM | 2.5x-3x | Night emergency premium |
| Holidays/Weekends | +50% additional | On top of time-based rate |

### Early Morning Premium
- **6:00 AM start:** 1.5x normal rate
- **6:30 AM start:** 1.25x normal rate  
- **7:00 AM start:** Normal rate

## Customer Communication Templates

### Emergency Response (After Hours):
```
"Hi [Customer], this is [Business Name]. Emergency detected.
We can dispatch a technician immediately for emergency service:

Tonight: $[emergency_price] (emergency rate)
Tomorrow 7 AM: $[normal_price] (regular rate)

Temporary fix instructions: [relevant safety steps]
Which option works for you?"
```

### Non-Emergency Response (After Hours):
```
"Hi [Customer], thanks for reaching out to [Business Name].
We can schedule you for:

- Tomorrow 6 AM: $[premium_price] (priority rate)
- Tomorrow 8 AM: $[normal_price] (regular rate)  

Which time works better?"
```

## Business Rules

### Emergency Acceptance Criteria
✅ **Will dispatch immediately if:**
- True emergency detected (safety/property damage risk)
- Customer accepts emergency rate  
- Within service area
- Contractor has emergency service enabled

❌ **Will not dispatch immediately if:**
- Non-emergency issue (can wait until morning)
- Customer declines emergency rate
- Outside defined service radius
- Contractor has emergency service disabled

### Contractor Controls
- **Emergency Service Toggle:** ON/OFF
- **Emergency Rate Multiplier:** 1.5x to 3x (contractor sets)
- **Service Cutoff Time:** Optional hard stop time
- **Maximum Emergency Jobs Per Night:** Limit setting
- **Emergency Service Radius:** May be smaller than regular service area

## AI Logic Summary

1. **Always answer calls 24/7**
2. **Detect emergency vs non-emergency**
3. **Apply time-based rate logic**
4. **Require customer confirmation for premium rates**
5. **Only wake contractor for accepted emergency jobs**
6. **Provide temporary guidance while help is coming**
7. **Confirm all details via SMS**

This system maximizes emergency revenue while protecting contractor work-life balance and ensuring only genuine emergencies interrupt sleep.


## 8 PM vs 6 AM

### 8 PM Emergency (Same Night Service)

Rate: 2.5x-3x normal pricing
Logic: Contractor goes back out that night, works until 10-11 PM
Example: $200 job → $500-600 emergency rate

### 6 AM Emergency (Next Morning Priority)

Rate: 1.5x normal pricing
Logic: Early start premium, but contractor gets full night's sleep
Example: $200 job → $300 early priority rate

