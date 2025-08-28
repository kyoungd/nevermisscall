DISPATCH AI BOT
Input parameters
Business Hours
Business Address
Job Estimate List (job, description, estimated hours, estimated cost)
Caller number
Called number



🛠️ Product Specification: Smart Scheduling App for Field Service Pros (Plumber)

🚀 Purpose
An AI-powered scheduling and response platform that helps local service pros (plumbers, electricians, handymen) manage incoming leads, automate scheduling, and intelligently route jobs based on real-world constraints like job duration, drive time, and urgency.

👥 Target Users
Solo or small-team service providers


Trades: Plumbing, Electrical, Handyman


Operating in metro areas with dense scheduling demands



📅 Core Scheduling Features
✅ Smart Appointment Booking
AI books jobs based on:


Job type


Job duration (from time library)


Travel time with traffic


Padding/buffer between jobs


Work hours / availability


Next-day tentative jobs can be moved to accommodate emergencies


📍 Location-Aware Routing
Schedules jobs based on current and next location, not just home base


Calculates real-world travel time using traffic data


Respects user-defined service radius (e.g., 20–25 miles)


📆 Time Blocking Logic
Job block = (Estimated Job Time + Travel Time + Buffer)


Avoids back-to-back jobs with tight transitions


Allows manual overrides and calendar editing


🔧 Job Time Library (Customizable)
Preloaded average durations by job type (e.g., Faucet Install = 1.5 hrs)


User can edit durations based on their experience


Used for auto-scheduling and quoting


💵 Default Pricing Library (Editable)
Pre-set flat rates based on job type & local market (e.g., LA plumbing rates)


Pricing visible to AI for quoting/text-back purposes


Supports tiered rates (e.g., after-hours or emergency pricing)



📞 Lead Handling Rules
💬 Instant Text-Back
Sends an SMS within seconds of missed call:


“Hi, this is [Biz Name]! We missed your call—how can we help?”


Keeps lead engaged while pro is on the job


🤖 DispatchBot AI Flow
Waits 60 secs for the owner to respond


If no reply, AI:


Answers FAQs


Provides ballpark pricing (from price library)


Offers available appointment windows


Screens for emergencies


🚨 Emergency Handling Rules
AI determines urgency from keywords and intent


Only books emergencies if:


There’s a suitable time slot (open, with travel/buffer)


Owner has toggled “Accept Emergencies = ON”


Within defined emergency service area


Emergency jobs may override tentative ones (with notification)


🛑 Owner Controls
“Accept Emergencies” ON/OFF toggle


“Out of Office” mode blocks AI from booking new jobs


“Set Max Jobs Per Day” and “Min Buffer Between Jobs” settings





Below is a field-tested “decision ladder” the AI climbs every time a call is missed and the text-back starts.
 Think of it as two similar funnels—one for Same-Day dispatch and one for Next-Day tentative holds.

0. Inbound Trigger (Same day & Next day)
Auto-reply (< 10 s) – “What’s the issue and the service address (street + ZIP)?”


NLP pass – detect ➜ trade, job-type, urgency, keyword red-flags.


Collect missing essential (max one follow-up): ZIP or brief issue if still unknown.



A. Same-Day Booking Funnel (“Can we go today?”)
Step
What the AI Checks
Why it Matters
1. Service-area gate
• ZIP within service radius?• “Accept Emergencies” toggle?
Don’t waste time on jobs you can’t reach or don’t take.
2. Job validity gate
• Trade supported?• Job-type in library?• Owner max-jobs/day not exceeded?
Avoid over-committing or unsupported work.
3. Rough duration & cost
• Library lookup ➜ duration & flat-rate range.• If confidence < 0.75 → default to “diagnostic 60 min, $150-$200”.
You promised ≤2 questions—quote now or fallback.
4. Address verification & geo-locate
• Geocode street to lat/lng.• Flag address_verified if success.• If geocode fails → ask to confirm landmark.
Needed for live travel-time.
5. Travel-time calc
• Last booked job location ➜ customer address (live traffic API).• Add buffer (owner setting, e.g., 20 min).
Ensures tech really can arrive in window.
6. Business-hours window fit
• Candidate start = earliest now + travel + buffer.• End = start + duration.• Must finish ≤ business closing OR overtime-allowed toggle.
Respects owner’s hours.
7. Calendar gap check
• Scan AI calendar for an open block ≥ travel+duration+buffer.• No overlap with existing holds.• Respect “min buffer between jobs”.
Prevents double-booking.
8. Parts / equipment sanity
• Does job require special part in stock?• If not: can tech stop at supplier en-route (adds pickup buffer)?
Stops impossible “today” promises.
9. Build offer
• Window (e.g., 2-4 pm), price range, duration.• Attach emergency premium if flag.
Clear, concise ask for confirmation.
10. Customer confirmation
• Wait configurable period (e.g., 3 min).


11. Calendar write
• booking_type = confirmed.• Store compact JSON in event + full record in DB.


12. Notifications
• Text customer + push owner (“Job booked 2-4 pm, water-heater leak”).• Optional map link.




B. Next-Day Funnel (Booking for tomorrow or +2 days, ≤ AI window limit)
Step
What the AI Does Differently
1–3 Same as steps 1–3 above (service-area, job validity, quote).


4. Day-level capacity scan
• Count existing confirmed & tentative events for that day.• Respect max-jobs/day & job-type mix (e.g., 1 big install + 3 small).
5. Earliest feasible slot
• Ignore real-time traffic; use average travel times between tentative route clusters.• Insert job into “logical gap” (morning / afternoon).
6. Offer time window, not exact start
• “We can take you tomorrow between 1-3 pm.”• Explain that exact ETA is texted morning-of.
7. Tentative hold
• booking_type = tentative in calendar.• Color-code as “soft hold”.
8. Overnight re-optimization
• Nightly cron / AI run:
– Pull traffic forecasts, cluster jobs, minimize drive-time, re-order route.


– Convert tentative ➜ confirmed & push exact ETAs.


9. Morning text
• “Tech arriving ~2:15 pm. Reply YES to confirm.”
10. Final confirm / fallback
• No-reply rules: one reminder ➜ owner alert ➜ soft hold cleared if unconfirmed by specified cut-off.


Extra Checks Both Funnels Share
Owner “Out of Office” toggle overrides booking.


Skill or equipment constraints (e.g., electrician requires ladder > 20 ft).


Payment policy (deposit needed?); AI adds note if so.


Weather & hazard (storm blocks roof work; extreme heat auto-escalates AC calls).


Compliance flags (permits required? gas shut-off?).



Summary of Data Points Verified before placing any calendar hold
Data Point
Same-Day
Next-Day
Service area & trade supported
✅
✅
Job-type duration & cost
✅
✅
Full street address verified
✅ (must)
✅ (must)
Live travel-time & buffer
✅ (live API)
Ø (avg est.)
Fits inside business hours
✅
✅
Calendar gap ≥ duration+buffer
✅ (exact)
✅ (day-level)
Parts/equipment feasibility
✅ (today)
✅ (order if needed)
Owner toggles (accept emergencies, max jobs/day)
✅
✅
Tentative vs. confirmed flag
Confirmed
Tentative first
Create / update calendar event with metadata
✅
✅
Notify customer & owner
✅
✅

Follow this checklist and you’ll never promise a slot you can’t keep—whether it’s in two hours or tomorrow afternoon.
📋 Minimum Data Needed to Lock-In a Service Appointment
#
Field
Why It’s Required
How You Capture It (fast, ≤ 2 questions)
1
Caller phone (phone)
Contact, SMS thread key
Auto-known from inbound call/SMS
2
Trade (trade)
Picks the right job library & tech
NLP on the first message (plumbing / electrical / HVAC / locksmith / garage door)
3
Job type / issue (job_type or diagnostic)
Maps to duration + price
Ask “What’s the issue?” if NLP confidence < 0.75
4
Full service address (address.line1 … postal_code)
Travel-time, routing, service-area check
Ask for street + ZIP in same question as issue
5
Urgency level (urgency)
Normal vs. emergency workflow & pricing
Detect keywords; if unclear, ask “Is this urgent or can it wait?”
6
Preferred day (date_pref)
Same-day vs. next-day logic
Infer from urgency; otherwise accept the first available day
7
Time-window fit (window_start / window_end)
Holds exact or tentative slot
AI finds gap that satisfies: travel + buffer + duration within business hours
8
Duration estimate (duration_min)
Ensures slot length is valid
Pulled from job library after job_type is known
9
Price range (price_min / price_max)
Sets customer expectation & confirmation
Pulled from job library; adjust for emergency or after-hours
10
Booking status (booking_type)
Tentative vs. confirmed flag
Tentative for next-day, confirmed for same-day after customer “YES”
11
Consent / confirmation (customer_ok)
Compliance & no-show reduction
Customer replies YES (text) or taps confirm link
12
Internal job ID (job_id)
Tie calendar event ⇄ CRM/DB
Generated UUID at booking time


🚀 One-Shot Prompt That Collects Essentials
“Hi, this is [Biz]. We missed your call — what’s the issue and the service address (street + ZIP)? I’ll check the next available window right now.”
If either issue or address is missing, ask one follow-up. Then offer the window and quote. Total questions: ≤ 2.
Use those twelve required fields and you can reliably schedule, price, and route any same-day or next-day job without bogging the caller down.







Do we recommend a one-shot prompt as the default opening move?
Yes — with guard-rails.
 Sending one well-crafted SMS that requests the two critical facts you need keeps friction low, honors your “≤ 2 questions” rule, and out-converts multi-step interrogations. The AI should fall back to one clarifying follow-up only when the first reply is missing something essential.

Why one-shot usually wins
Benefit
Impact
Speed
Caller answers once → AI can quote & offer a slot immediately.
Cognitive load
Fewer notifications = less abandonment; especially important when the customer is stressed (leak, lock-out, no A/C).
Inbound SMS limits
Some VOIP lines throttle; fewer messages = higher deliverability.
Matches real conversation
Humans naturally dump the whole problem in one reply when asked the right way.

Field tests with urgent-service bots show 10–20 % better conversion when you open with a single “issue + address” ask versus a two-step (issue → address).

Designing the one-shot prompt
“Hi, this is [Biz Name]. We missed your call — can you tell me what’s wrong and the service address (street + ZIP)? I’ll check our next available window right now.”
Why it works
Polite apology / identity – builds trust.


Two requests, no jargon – callers know what “street + ZIP” means.


Immediate benefit – “I’ll check our next window” explains why they should answer.



Guard-rails to keep accuracy high
Parse the first reply


If it contains both an issue keyword and a 5-digit ZIP or clear street, proceed.


Single follow-up if missing data


“Got it — what’s the service address?” or


“Thanks! And what seems to be the problem?”
 Ask only the missing piece.


Confidence threshold


If intent_confidence < 0.70, default to diagnostic visit estimate and keep moving.


Timeout rule


If no reply in X minutes, send one reminder then alert owner.


Language detection


Auto-switch to Spanish if first reply is Spanish (keeps one-shot effective in bilingual markets).



Variations you can A/B test
Scenario
Prompt tweak
High emergency trades (locksmith, burst pipe)
“Is this an emergency? If so, add “YES” so I prioritize.”
VOIP / low-trust number
End with “Reply YES after your address to confirm booking.”
Known repeat customer (phone in CRM)
“Hi Jane, same address as last time? Tell me the issue and I’ll slot you in.”


When multi-step beats one-shot
Complex installs (full HVAC replacement) where you truly must know make/model or photos.


Insurance/permit jobs requiring extra legal language.


Very low NLP confidence on the opening problem description.


In those edge cases, start with a soft one-shot, then branch into a guided form or hand off to the owner.

Bottom line
Default: one-shot prompt → single follow-up if needed.


Measure: track incomplete-info rate; if > 15 %, iterate wording, not question count.


Automate: code the fall-backs above so the bot never stalls the lead.


That balance keeps the booking flow fast and reliable for plumbing, electrical, HVAC, locksmith, and garage-door calls.







Should you run one AI or five trade-specific AIs?
Use one core “DispatchBot” with plug-in trade profiles — not five completely separate bots.

1 | Why a single core with modular trade profiles is best
Factor
Separate AI per trade
Single AI + trade profile
Setup & maintenance
5× prompt tuning, 5× webhooks, 5× logs
One codebase, swap-in JSON/YAML profiles
Consistency of UX
Risk of different tone & logic
Same greeting, confirmation flow, reminders
Cross-sell / multi-trade contractors
Can’t share calendar or CRM easily
One calendar, dynamic questions
Analytics
Fragmented KPIs
Unified conversion & no-show metrics
Adding a new trade
New bot from scratch
Copy a profile file, add job library
Compute / API cost
5x parallel calls
Single model call with trade context token

The only real advantage of fully separate bots is isolation (e.g., a franchise wanting its own branding & datastore). For five trades you own, modular prompts are far easier.

2 | How to architect the modular approach
Incoming SMS / Call
        │
 (1) Fast classifier
        │   → returns {trade:"plumbing", intent:"water_heater"}
        │
 (2) Core DispatchBot
        ├─ loads trade profile "plumbing.json"
        ├─ injects job library, urgency keywords, price table
        ├─ runs slot-filling dialogue
        └─ writes event with metadata JSON

Trade-profile file (plumbing.json example)
{
  "trade": "plumbing",
  "library_file": "plumbing_jobs.csv",
  "urgent_keywords": ["leak","flood","no hot water"],
  "first_prompt": "Hi, this is Prime Plumbing. What’s the issue and service address?",
  "ask_flow": ["issue", "address", "Urgent?"],
  "price_rules": { "emergency_multiplier": 1.5 },
  "duration_rules": { "buffer_min": 30 }
}

Switch to locksmith.json and the core engine automatically:
Greets as locksmith


Uses lock-specific job library


Looks for “locked out”, “lost key”, etc.


Applies 30-min default duration, 2× emergency multiplier



3 | What actually changes by trade?
Always the same
Trade-specific
Phone capture, address capture, YES-to-confirm, reminder cadence
Job-type vocabulary, duration & price tables, urgent keywords, parts flags
Calendar write & metadata schema
Part-stock rules (springs for garage door, capacitors for HVAC)
No-show workflow
Regulatory disclaimers (e.g., gas permits for plumbers)

So you get one conversation skeleton and swap out only the parts that matter.

4 | When you might split into separate bots
Different brands or legal entities that cannot share data


Franchises with fully custom tone, pricing, or CRM


Heavy regulatory divergence (e.g., medical vs. locksmith)


If those don’t apply, keep the single-bot architecture.

5 | Implementation checklist
Intent classifier: fine-tune or rules to map raw text → {trade, job_type, confidence}.


Profile loader: JSON/YAML per trade with libraries & prompts.


Prompt templating: {{greeting}}, {{issue_ask}}, injected from profile.


Shared fallback logic: if intent confidence low → diagnostic visit.


Central job-library registry: CSV or DB keyed by trade, job_type.


Unit tests: run same regression suite across all five profiles.


Add a sixth profile tomorrow (e.g., Appliance Repair) without touching core code.

Bottom line
Run one core AI engine that dynamically loads a trade profile.
 It keeps your stack lean, your brand consistent, and scaling to new verticals is just adding a file — not a new bot.







Got it — if each phone number is already dedicated to a single trade, you can drop the “what trade is this?” step entirely and just inject the correct profile based on the DID the call or SMS arrived on.

🔧 Minimal routing logic
// inbound webhook
switch (called_number) {
  case "+1-555-PLUMB":
      profile = loadProfile("plumbing.json");
      break;
  case "+1-555-ELECT":
      profile = loadProfile("electrical.json");
      break;
  case "+1-555-HVACT":Do t
      profile = loadProfile("hvac.json");
      break;
  case "+1-555-LOCKS":
      profile = loadProfile("locksmith.json");
      break;
  case "+1-555-GARAGE":
      profile = loadProfile("garage_door.json");
      break;
}
coreAgent(profile, conversation);

No trade classifier needed; the core LLM receives the profile and runs the same slot-filling flow you already sketched out (issue + address + YES confirm).

What still needs NLP
Still detected by LLM
Why
Job type / issue
Map to duration & price in the profile’s library.
Urgency keywords
Decide emergency rules, pricing multiplier, calendar override.
(Optional) Follow-up intents
Reschedule, cancel, ETA, etc.

Everything else (trade, greeting, price table, business hours) is locked-in by phone-number routing.

Future-proofing for multi-discipline numbers
If you later advertise one number that covers Electrician + HVAC:
Primary inference – keep the single question:


 “What’s the issue and the address?”



Intent classifier – only needs to choose between two trades (much simpler than five).


Tie-breaker prompt – if confidence < 0.7:


 “Got it—just to confirm, is this an electrical issue or your AC/heat?”



Plumbing ≠ HVAC, so you can safely keep those on distinct numbers.

Config mapping suggestion
numbers:
  "+1555PLUMB":      plumbing
  "+1555ELECT":      electrical
  "+1555HVACT":      hvac
  "+1555LOCKS":      locksmith
  "+1555GARAGE":     garage_door
profiles_dir: "./trade_profiles/"

Your webhook reads the YAML, sets trade in the metadata blob, and drops it into the LLM call—zero guesswork.

Key takeaway
Today: Use the DID → profile lookup and skip trade classification entirely.


Later (multi-discipline numbers): add a light intent check only between the trades that share that number.


All other LLM logic (issue, address, urgency, quoting, calendar) stays exactly the same.


This keeps your architecture simple now and flexible for the combos you might add later.

