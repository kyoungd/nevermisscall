# Dispatch Bot AI Conversations

## Happy Path Scenarios

### 1. Simple Plumbing Emergency (Same Day)

**Customer calls at 2:15 PM, no answer**

**Bot:** Hi, this is Prime Plumbing! We missed your call - what's the issue and the service address (street + ZIP)? I'll check our next available window right now.

**Customer:** Water heater burst in basement! 789 Sunset Blvd, 90210

**Bot:** 🚨 Water heater emergency - I can get our tech to you today 5:30-8:00 PM. Emergency rate $375-$900 (1.75x). Reply YES to confirm this appointment.

**Customer:** YES

**Bot:** ✅ Confirmed! Tech will arrive 5:30-8:00 PM today for your water heater emergency. You'll get an ETA text 30 mins before arrival. Total: $375-$900 (emergency rate). Job #EMR-001.

---

### 2. Regular HVAC Appointment (Next Day)

**Customer calls at 7:45 PM (after business hours)**

**Bot:** Hi, this is CoolTech HVAC! We missed your call - what's the issue and the service address (street + ZIP)? Since it's after hours, I'll check tomorrow's availability.

**Customer:** AC not cooling well, 456 Oak Ave 90210

**Bot:** I can schedule AC service tomorrow:
- 6:00 AM priority slot: $225 (1.5x rate)
- 8:00 AM regular slot: $150 (normal rate)
Which time works better?

**Customer:** 8 AM is fine

**Bot:** Perfect! AC service scheduled tomorrow 8:00-10:00 AM for $150-$200. You'll get a confirmation text tonight. Job #REG-002.

---

### 3. Locksmith Emergency (Late Night)

**Customer calls at 10:30 PM**

**Bot:** Hi, this is SecureLock Services! What's your lockout emergency and location?

**Customer:** Locked out of my house! 123 Elm St 90210

**Bot:** 🔐 Lockout emergency detected. We can dispatch a locksmith immediately:

Tonight: $450 (2.75x emergency rate)
Tomorrow 7 AM: $150 (regular rate)

Temporary options: Check if any windows unlocked, look for hidden key, call family for spare.
Which option works for you?

**Customer:** I need help tonight

**Bot:** Confirmed emergency lockout service! Our locksmith will be there within 60 minutes. Total: $450. You'll get an ETA text shortly. Job #LCK-003.

---

### 4. Electrical Issue (Evening Window)

**Customer calls at 6:15 PM**

**Bot:** Hi, this is ElectriPro! What's your electrical issue and service address?

**Customer:** Power out in half my house, circuit breaker won't reset. 789 Pine St 90210

**Bot:** ⚡ Electrical emergency - partial power outage detected. I can get our electrician there tonight 7:00-9:00 PM. Evening emergency rate $337-$675 (2.25x). Reply YES to confirm.

**Customer:** How much would it be tomorrow?

**Bot:** Tomorrow options:
- 6:00 AM priority: $225 (1.5x rate)  
- 8:00 AM regular: $150 (normal rate)

Tonight ensures your power is restored before bedtime. Which do you prefer?

**Customer:** Tonight please

**Bot:** ✅ Emergency electrical service confirmed! Tech arriving 7:00-9:00 PM tonight. Total: $337-$675 (evening emergency). Safety reminder: Don't use extension cords as permanent solution. Job #ELE-004.

---

## Challenging Scenarios

### 5. Unclear Description

**Customer calls at 3:00 PM**

**Bot:** Hi, this is Prime Plumbing! We missed your call - what's the issue and the service address (street + ZIP)?

**Customer:** Something's broken, help!

**Bot:** I'd love to help! Can you tell me specifically what plumbing issue you're having and your street address + ZIP code? (For example: 'leaky toilet, 123 Main St 90210')

**Customer:** Stuff is wet

**Bot:** Water issue understood. Where is the water coming from? (sink, toilet, pipe, ceiling?) And what's your service address? We'll send someone for a diagnostic visit to assess and fix the problem.

**Customer:** Kitchen sink area, water under cabinet. 555 Oak Ave 90210

**Bot:** Kitchen leak detected - could be serious! I can get our plumber there today 4:30-6:00 PM for $225-$350 to diagnose and repair. Reply YES to confirm this appointment.

---

### 6. Price Objection

**Customer calls at 9:00 PM**

**Bot:** Hi, this is Prime Plumbing! What's your plumbing emergency and location?

**Customer:** Toilet overflowing! 456 Maple Dr 90210

**Bot:** 🚨 Toilet overflow emergency! We can dispatch immediately:

Tonight: $412 (2.75x night emergency)
Tomorrow 7 AM: $150 (regular rate)

Temporary fix: Turn off water valve behind toilet, use plunger if safe.
Which option works?

**Customer:** $400 is way too much!

**Bot:** I understand the concern. Night emergency rates are higher due to after-hours service. Your options:

1. Tonight: $412 (immediate response, prevents water damage)
2. Tomorrow 6 AM: $225 (priority rate) 
3. Tomorrow 8 AM: $150 (regular rate)

Water damage can cost thousands - would earlier tomorrow work instead?

**Customer:** Fine, 6 AM tomorrow

**Bot:** ✅ Toilet repair scheduled tomorrow 6:00-8:00 AM for $225. Turn off water valve tonight to prevent further overflow. You'll get confirmation text. Job #PLB-005.

---

### 7. Out of Service Area

**Customer calls at 1:00 PM**

**Bot:** Hi, this is Prime Plumbing! We missed your call - what's the issue and the service address (street + ZIP)?

**Customer:** Leaky faucet at 456 Remote Rd, 93555

**Bot:** Sorry, Ridgecrest (93555) is outside our 25-mile service area from LA. Try searching 'plumber near Ridgecrest CA' for local options. Thanks for thinking of Prime Plumbing!

**Customer:** How about 200 extra for the drive?

**Bot:** I appreciate the offer, but our techs can't travel that far safely in one day. Local Ridgecrest plumbers will serve you better and faster. Good luck!

---

### 8. Capacity Full

**Customer calls at 11:00 AM**

**Bot:** Hi, this is Prime Plumbing! We missed your call - what's the issue and the service address (street + ZIP)?

**Customer:** Bathroom faucet dripping, 789 Oak St 90210

**Bot:** Today is fully booked, but I can schedule your faucet repair:

- Tomorrow 7:00 AM: $150-$200 (regular rate)
- Tomorrow 6:00 AM: $225-$300 (priority rate)

The drip won't cause damage overnight. Which time works better?

**Customer:** Is there anything today?

**Bot:** Let me check for cancellations... Unfortunately nothing available today. Tomorrow 7 AM is our earliest opening. Shall I hold that slot for you?

**Customer:** Yes please

**Bot:** ✅ Faucet repair scheduled tomorrow 7:00-9:00 AM for $150-$200. Turn off faucet tightly to minimize dripping. You'll get confirmation text. Job #PLB-006.

---

### 9. Non-Emergency After Hours

**Customer calls at 8:30 PM**

**Bot:** Hi, this is ElectriPro! What's your electrical issue and service address?

**Customer:** Need new outlet installed in garage, 123 Main St 90210

**Bot:** Outlet installation isn't an emergency, but I can schedule you:

- Tomorrow 6:00 AM: $225 (priority rate)
- Tomorrow 8:00 AM: $150 (regular rate)  
- Tomorrow 10:00 AM: $150 (regular rate)

Which time works better for your schedule?

**Customer:** Can't you do it tonight for extra money?

**Bot:** Our techs only work emergency calls after 7:30 PM (sparks, smoke, power outages). New outlet installation can safely wait until morning. The 8 AM or 10 AM slot would be perfect!

---

### 10. Customer Never Confirms

**Bot:** I can schedule your plumbing repair today 2:00-4:00 PM for $150-$250. Reply YES to confirm, or let me know if you need a different time.

**Customer:** [No response for 3 minutes]

**Bot:** Still need that plumbing repair? Reply YES to confirm your 2-4 PM slot today, or let me know if you need a different time.

**Customer:** [No response for 5 more minutes]

**Bot:** No worries! Feel free to call us again when you're ready to schedule. Thanks for contacting Prime Plumbing!

---

### 11. Wrong Trade Type

**Customer calls plumber at 2:00 PM**

**Bot:** Hi, this is Prime Plumbing! We missed your call - what's the issue and the service address (street + ZIP)?

**Customer:** Garage door won't open, remote not working. 456 Oak Ave 90210

**Bot:** That's a garage door issue - we're plumbers! For garage door service, try searching 'garage door repair near me' or check your door company's sticker for their number. Good luck!

**Customer:** Can't you just take a look?

**Bot:** We specialize in plumbing only (pipes, water heaters, toilets, sinks). Garage doors need specific parts and expertise we don't have. A garage door company will fix it faster and cheaper!

---

## Edge Cases

### 12. Multiple Issues

**Customer calls at 10:00 AM**

**Bot:** Hi, this is Prime Plumbing! We missed your call - what's the issue and the service address (street + ZIP)?

**Customer:** Toilet running constantly AND kitchen sink clogged, 789 Pine St 90210

**Bot:** Two plumbing issues - running toilet and clogged kitchen sink. I can schedule a service call today 1:00-3:00 PM to fix both issues. Estimated $200-$400 total. Reply YES to confirm.

**Customer:** Which one first?

**Bot:** Our plumber will assess both and handle the most urgent first, usually the one causing more inconvenience. Both will be fixed in the same visit for maximum efficiency!

---

### 13. Vague Location

**Customer calls at 4:00 PM**

**Bot:** Hi, this is Prime Plumbing! We missed your call - what's the issue and the service address (street + ZIP)?

**Customer:** Broken pipe, corner of that big street near the mall

**Bot:** I need a specific street address to dispatch our tech. Can you provide the street number and name + ZIP? (Example: '123 Main St, 90210')

**Customer:** I don't know the exact address

**Bot:** Try checking:
- Mail/packages for the address
- Google Maps with your location
- Ask neighbors or nearby businesses
- Property management if it's an apartment

I'll need the full address to send help your way!

---

### 14. Safety Concern

**Customer calls at 11:00 PM**

**Bot:** Hi, this is ElectriPro! What's your electrical emergency and location?

**Customer:** Outlet sparking and smell of burning plastic! 456 Elm St 90210

**Bot:** ⚡ ELECTRICAL FIRE HAZARD - Turn off power at main breaker NOW if safe to reach. If you smell smoke or see flames, evacuate and call 911 immediately.

Do you have the main breaker off? Are you safe?

**Customer:** Yes breaker is off, no flames

**Bot:** Good! Emergency electrician dispatched - arriving within 45 minutes. Stay away from that outlet area. Total: $550 night emergency rate. Your safety is priority! Job #ELE-007.

---

### 15. Repeat Customer

**Customer calls at 9:00 AM**

**Bot:** Hi, this is Prime Plumbing! We missed your call - what's the issue and the service address (street + ZIP)?

**Customer:** Hey it's John from 123 Oak St, same water heater acting up again

**Bot:** Hi John! Sorry to hear the water heater is giving trouble again. Since we were just there last month, I can priority schedule you today 11:00 AM-1:00 PM. If it's the same issue, we'll honor our warranty. Sound good?

**Customer:** Perfect, thanks for remembering!

**Bot:** ✅ Priority service scheduled 11:00 AM-1:00 PM today. Our tech will bring the previous job notes. See you soon, John! Job #PLB-008.
