# NeverMissCall — Product Description

## Product Overview

**NeverMissCall** is a specialized call management platform designed exclusively for blue-collar service businesses whose workers are physically unable to answer phones during work hours. The platform automatically converts missed calls into SMS conversations with AI assistance, capturing revenue that would otherwise be completely lost to competitors who happen to be available when customers call.

### Core Value Proposition

* **Capture Revenue While Working**: Never lose appointments because your hands are dirty, you're in a crawl space, or using loud tools
* **Instant Customer Response**: Customers get immediate SMS replies when you physically can't answer the phone
* **AI Handles Initial Screening**: Qualify callers, assess urgency, and book appointments automatically
* **Work-Focused Design**: Built specifically for trades where physical work prevents phone access

---

## Key Features

### 📞 **Automated Missed Call Recovery**

* Instant SMS response to missed calls (≤5 seconds)
* Intelligent call detection and customer identification
* Customizable greeting templates per business

### 🤖 **AI Conversation Management**

* Context-aware AI responses using business-specific information
* Caller qualification and customer needs assessment
* 60-second response timer with human override capability
* Natural conversation flow with appointment scheduling capabilities

### 👥 **Human-AI Collaboration**

* One-click takeover from AI to human agents
* Conversation history preserved during handoffs
* Real-time conversation monitoring and intervention
* Role-based access for different team members

### 📅 **Service Catalog & Scheduling**

* **Catalog (service items & pricing)**: Business-specific list of services with custom pricing and duration
* **Instant Price Quotes**: AI provides immediate quotes during customer conversations
* **Scheduling module**: Books appointments with correct time blocks based on service duration (**No Double-Booking**, see ADR-0002)
* **Calendar Integration**: Direct sync with Jobber and Google Calendar
* **Fast Availability:** uses a local projection refreshed within ~1s; avoids double-booking.

### 📊 **Business Intelligence**

* Caller/Customer funnel metrics
* Conversation performance metrics
* Revenue attribution from missed calls
* Basic reporting and insights (advanced analytics deferred)

### 🛡️ **Compliance & Security**

* Full 10DLC compliance for business messaging
* STOP/HELP keyword handling
* Data retention policies and privacy controls
* Encryption at rest and in transit (TLS); no field-level encryption in MVP

---

## Target Users

### Primary Users - Blue-Collar Service Businesses

**The Problem**: These professionals are physically unable to answer phones during work hours when most customers call:

* **Plumbers**: Hands dirty, under sinks, in crawl spaces, using loud pipe tools
* **Electricians**: In attics/basements, working with live wires, safety requires focus
* **HVAC Technicians**: On rooftops, in tight spaces, handling heavy equipment
* **Handymen**: On ladders, both hands occupied, working with power tools
* **Auto Mechanics**: Under cars, hands covered in grease, using pneumatic tools
* **Cleaning Services**: Wearing gloves, using chemicals, focused on detail work

**Business Profile**: 1-5 employees, local service area (LA/SF metro), immediate-need customer base

### User Roles (for 1-5 employee businesses)

* **Business Owner**: Full platform access, service catalog setup, billing, compliance management
* **Worker/Technician**: View appointments, basic conversation access (optional for larger teams)

*Note: Most small businesses will use only the Owner role initially*

---

## Use Cases

### 1. **Emergency Service Provider**

**Scenario**: A plumbing company receives calls outside business hours for emergency repairs.

**User Journey**:

1. Customer calls after hours with a burst pipe emergency
2. Call ends or goes to voicemail, triggers NeverMissCall. AI responds with SMS, no voice.
3. Immediate SMS sent: "Hi! Thanks for calling \[Business]. We received your call about plumbing services. Is this an emergency?"
4. Customer responds: "Yes! Burst pipe flooding my kitchen!"
5. AI escalates to human agent immediately due to emergency keywords
6. Agent responds within minutes, schedules emergency visit
7. Customer receives confirmation with technician details and arrival time

**Outcome**: Emergency captured, customer served, revenue generated instead of lost to competitor.

### 2. **Solo Handyman Business**

**Scenario**: A one-person handyman operation in LA handles home repairs but is often on job sites during peak call times.

**User Journey**:

1. Homeowner calls about kitchen cabinet repair while handyman is installing flooring at another job
2. Call ends or goes to voicemail, triggers NeverMissCall. AI responds with SMS, no voice.
3. AI responds: "Hi! Thanks for calling Mike's Handyman Services. I see you called about home repair. What kind of work do you need done?"
4. Customer: "My kitchen cabinet door fell off and I need it fixed this week"
5. AI checks service catalog and calendar: "Cabinet door repair takes 2 hours and costs \$95. I have availability Tuesday at 10 AM or Wednesday at 1 PM - both slots have the full 2 hours available. Which works better for you?"
6. Customer chooses Tuesday morning and accepts the quote
7. AI books a 2-hour appointment in NeverMissCall, then syncs it to Google Calendar; if sync is delayed or fails, the booking still stands.
8. Handyman receives notification with customer details and repair description
9. Customer gets confirmation SMS with Mike's photo and arrival time

**Outcome**: Job booked automatically while handyman stays focused on current work, no calls missed.

---

## Key Stakeholders and their goals

### Revenue Impact

* **Recover 100% Lost Revenue**: Capture calls that currently go to zero because you can't physically answer
* **No Staffing Overhead**: Grow revenue without hiring office staff or answering services

### Operational Efficiency

* **Stay Focused on Work**: No interruptions from phone calls during jobs
* **Automatic Service Qualification**: AI screens serious inquiries from price shoppers with upfront pricing
* **Work-Safe Communication**: No need to handle phone with dirty/gloved hands

### Customer Experience

* **Immediate Scheduling**: Book appointments without waiting for callbacks
