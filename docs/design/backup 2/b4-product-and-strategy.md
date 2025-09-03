# NeverMissCall — Product Description

## Product Overview

**NeverMissCall** is a specialized call management platform designed exclusively for blue-collar service businesses whose workers are physically unable to answer phones during work hours. The platform automatically converts missed calls into SMS conversations with AI assistance, capturing revenue that would otherwise be completely lost to competitors who happen to be available when customers call.

### Core Value Proposition

* **Capture Revenue While Working**: Never lose jobs because your hands are dirty, you're in a crawl space, or using loud tools
* **Instant Customer Response**: Customers get immediate SMS replies when you physically can't answer the phone
* **AI Handles Initial Screening**: Qualify leads, assess urgency, and book appointments automatically
* **Work-Focused Design**: Built specifically for trades where physical work prevents phone access

---

## Key Features

### 📞 **Automated Missed Call Recovery**

* Instant SMS response to missed calls (≤5 seconds)
* Intelligent call detection and customer identification
* Customizable greeting templates per business

### 🤖 **AI Conversation Management**

* Context-aware AI responses using business-specific information
* Lead qualification and customer needs assessment
* 60-second response timer with human override capability
* Natural conversation flow with appointment scheduling capabilities

### 👥 **Human-AI Collaboration**

* One-click takeover from AI to human agents
* Conversation history preserved during handoffs
* Real-time conversation monitoring and intervention
* Role-based access for different team members

### 📅 **Job Catalog & Scheduling**

* **Catalog (service items & pricing)**: Business-specific list of services with custom pricing and duration
* **Instant Price Quotes**: AI provides immediate cost estimates during customer conversations
* **Scheduling module**: Books appointments with correct time blocks based on job complexity (**No Double-Booking**, see ADR-0006)
* **Calendar Integration**: Direct sync with Jobber and Google Calendar
* **Fast Availability:** uses a local projection refreshed within ~1s; avoids double-booking.

### 📊 **Business Intelligence**

* Lead tracking and conversion analytics
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

* **Business Owner**: Full platform access, job catalog setup, billing, compliance management
* **Worker/Technician**: View appointments, basic conversation access (optional for larger teams)

*Note: Most small businesses will use only the Owner role initially*

---

## Use Cases

### 1. **Emergency Service Provider**
**Scenario**: A plumbing company receives calls outside business hours for emergency repairs.

**User Journey**:
1. Customer calls after hours with a burst pipe emergency
2. Call ends or goes to voicemail, triggers NeverMissCall. AI responds with SMS, no voice.
3. Immediate SMS sent: "Hi! Thanks for calling [Business]. We received your call about plumbing services. Is this an emergency?"
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
5. AI checks job catalog and calendar: "Cabinet door repair takes 2 hours and costs $95. I have availability Tuesday at 10 AM or Wednesday at 1 PM - both slots have the full 2 hours available. Which works better for you?"
6. Customer chooses Tuesday morning and accepts the price range
7. AI books a 2-hour appointment in NeverMissCall, then syncs it to Google Calendar; if sync is delayed or fails, the booking still stands.
8. Handyman receives notification with customer details and repair description
9. Customer gets confirmation SMS with Mike's photo and arrival time

**Outcome**: Job booked automatically while handyman stays focused on current work, no calls missed.

### 3. **HVAC Contractor During Peak Season**
**Scenario**: LA HVAC company gets overwhelmed with AC repair calls during summer heat waves.

**User Journey**:
1. Customer calls about broken AC on 95-degree day when all technicians are booked
2. Call ends or goes to voicemail, triggers NeverMissCall. AI responds with SMS, no voice.
3. AI responds: "Thanks for calling Cool Air HVAC! I understand you need AC service. Is this an emergency or can we schedule for tomorrow?"
4. Customer: "It's 90 degrees in my house! This is definitely an emergency"
5. AI escalates: "I'm connecting you with our emergency dispatcher right now. Please hold."
6. Business owner receives priority notification and responds within minutes
7. Emergency service scheduled for same day with premium pricing
8. Customer receives tech details, arrival window, and service cost upfront

**Outcome**: Emergency captured at premium rates, customer expectations managed, revenue maximized during peak season.

### 4. **Electrician with Google Ads**
**Scenario**: SF electrician runs Google Ads for "emergency electrical repairs" but misses calls while working in basements/attics with poor cell service.

**User Journey**:
1. Customer clicks Google Ad and calls about flickering lights (potential fire hazard)
2. Call ends or goes to voicemail, triggers NeverMissCall. AI responds with SMS, no voice.
3. Call goes straight to AI: "Thanks for calling Bay Area Electric! I see you're calling about electrical issues. Can you describe what's happening?"
4. Customer: "My living room lights keep flickering and I smell something burning"
5. AI recognizes safety keywords and immediately flags for human takeover
6. Business owner gets urgent SMS alert and calls back within 10 minutes
7. Emergency service visit scheduled for same day
8. Customer receives safety tips via SMS while waiting

**Outcome**: High-value emergency lead captured from paid advertising, safety issue addressed immediately, ad spend ROI maximized.

### 5. **Husband-Wife Cleaning Service**
**Scenario**: Two-person cleaning service in LA wants to grow but can't answer phones while cleaning clients' homes.

**User Journey**:
1. Potential customer calls for weekly house cleaning quote during active cleaning job
2. Call ends or goes to voicemail, triggers NeverMissCall. AI responds with SMS, no voice.
3. AI responds: "Hello! Thanks for calling Sparkle Clean Services. I'd love to help you get a cleaning quote. What size is your home?"
4. Customer: "It's a 3-bedroom, 2-bathroom house in Venice"
5. AI checks job catalog and availability: "For a 3-bedroom home, our weekly cleaning takes 3 hours and costs $120. I have two 3-hour slots available: Friday at 10 AM-1 PM or Monday at 2 PM-5 PM. Which works better?"
6. Customer books Friday at 10 AM
7. AI automatically blocks the calendar time and sends customer onboarding checklist
8. Cleaning team receives new client notification with home details and special instructions

**Outcome**: New recurring client acquired automatically, service priced correctly from catalog, no interruption to current work.

### 6. **Mobile Auto Mechanic**
**Scenario**: Mobile mechanic serves LA/SF markets but needs to stay focused on repairs while customers call for service.

**User Journey**:
1. Driver calls about car breakdown while mechanic is under another car
2. Call ends or goes to voicemail, triggers NeverMissCall. AI responds with SMS, no voice.
3. AI responds: "Thanks for calling Mobile Mech LA! I can help you with your car trouble. Where are you located and what's the problem?"
4. Customer: "I'm in Santa Monica, my car won't start after I got groceries"
5. AI checks service radius: "I can get a mechanic to you today. It sounds like a battery or starter issue. Are you in a safe location?"
6. Customer confirms safety, AI schedules emergency visit
7. AI provides arrival estimate and sends customer prep checklist (keys ready, hood access, etc.)
8. Mechanic gets full briefing between current job and pickup

**Outcome**: Roadside emergency captured, customer kept safe with clear communication, mechanic arrives prepared with proper tools.

---

## Business Benefits

### Revenue Impact

* **Recover 100% Lost Revenue**: Capture calls that currently go to zero because you can't physically answer
* **Premium Pricing Opportunities**: Book urgent jobs same-day when available
* **Maximize Marketing ROI**: Every Google Ad click and referral gets immediate response
* **No Staffing Overhead**: Grow revenue without hiring office staff or answering services

### Operational Efficiency

* **Stay Focused on Work**: No interruptions from phone calls during jobs
* **Automatic Job Qualification**: AI screens serious inquiries from price shoppers with upfront pricing
* **Work-Safe Communication**: No need to handle phone with dirty/gloved hands

### Customer Experience

* **No More Voicemail**: Customers get instant, helpful responses instead of "leave a message"
* **Immediate Scheduling**: Book appointments without waiting for callbacks
* **Professional Image**: Consistent, reliable communication even when you're unavailable

---

## Technical Requirements

### Job Catalog & Pricing Engine

* **Business-Specific Job Catalog**: Each business configures their own services with custom pricing and duration
* **Duration-Based Scheduling**: AI matches job duration with available calendar slots before making offers
* **Smart Availability Matching**: Only offers appointment slots that can accommodate the full job duration
* **Custom Rate Setting**: Business owners set their own prices - AI never invents pricing
* **Time Block Validation**: Enforced with Postgres `tstzrange` and GiST exclusion constraints to guarantee **No Double-Booking** (ADR-0006).


**How It Works:**

1. Business pre-configures job catalog (e.g., "Sink Clog: 1 hour, \$175")
2. Customer describes problem: "My kitchen sink is completely clogged"
3. AI matches description to catalog entry and checks calendar availability
4. AI only offers slots with 1+ hour availability: "I can fix that sink clog today at 2 PM or tomorrow at 9 AM. It typically takes 1 hour and costs \$175."
5. AI books appointment with correct time block reserved

**Example Business-Specific Catalogs:**

*Joe's Plumbing (Premium Service):*

* Sink Clog: 1 hour, \$175
* Shower Leak Repair: 2 hours, \$285
* Toilet Installation: 3 hours, \$420

*Budget Plumbing Co:*

* Sink Clog: 1 hour, \$125
* Shower Leak Repair: 2 hours, \$210
* Toilet Installation: 3 hours, \$315

### Integration Capabilities

* **Existing Phone Systems**: Works with current business phone numbers
* **Calendar Systems**: Direct integration with Jobber and Google Calendar (Microsoft Office planned for Phase 2)
* **CRM Systems**: Lead data export and integration capabilities
* **Payment Processing**: Stripe integration for subscription billing

### Compliance & Security

* **10DLC Compliance**: Manual brand/campaign registration in Phase 1, automated compliance gates for message sending
* **Data Privacy**: GDPR/CCPA compliant data handling
* **Data Retention**: Messages retained 180 days, metadata 13 months, webhook dedupe 90 days, outbox events 30 days after dispatch (per Glossary + ADRs).
* **Message Security**: Encrypted at-rest and TLS-in-transit (no field-level crypto in MVP, ADR-0002).
* **Audit Trail**: Complete conversation and action logging

### Scalability

* **Low Volume Processing**: 5,000 users max total, less than 100 simultaneous connections at max.
* **Multi-Tenant Architecture**: Modular Monolith with `tenant_id` column model (single Postgres cluster, tenant-scoped tables per ADR-0001).
* **Performance SLOs**: Auto-SMS ≤5s P95, Booking API responses ≤500ms P95 (excluding 3rd party latency), UI freshness ≤2.5s P95
* **Reliability**: 99.9% uptime target with managed cloud services

---

## Getting Started

### Onboarding Process

1. **Account Setup**: Business registration via Clerk and user authentication
2. **Billing Setup**: Stripe subscription activation and billing shadow creation
3. **Job Catalog Setup**: Configure your services with custom pricing and durations
4. **Phone Integration**: Connect existing business phone number  
5. **Calendar Connection**: Link scheduling system (Jobber or Google)
6. **AI Configuration**: Customize greeting templates and response flows
7. **Compliance Registration**: Complete KYC form, ops registers 10DLC brand/campaign manually
8. **Go Live**: SMS enabled after compliance approval, begin capturing missed calls

### Pricing Model

* **Subscription-based only**: Monthly recurring revenue model
* **Compliance Included**: 10DLC registration and maintenance included
* **Transparent Billing**: Clear pricing with no hidden fees

---

## Success Metrics

### Key Performance Indicators

* **Missed Call Capture Rate**: Percentage of missed calls converted to conversations
* **Response Time**: Time from missed call to first customer interaction
* **Conversation Conversion Rate**: Percentage of conversations resulting in appointments/sales
* **Customer Satisfaction**: Rating of AI and human interaction quality
* **Revenue Attribution**: Tracked revenue from NeverMissCall-generated leads

### Expected Outcomes for Blue-Collar Businesses

* **Recover \$2,000-\$5,000/month** in previously lost revenue from missed calls
* **3-5 additional jobs per week** booked automatically during work hours
* **Eliminate customer frustration** with instant SMS responses vs. voicemail
* **5-10x ROI** within first 3 months (typical service call value \$200-\$500)

---

## Development & Deployment Constraints

### Design Philosophy

* **SaaS Service**: Use existing services like Clerk.dev or Stripe (with customer and billing services).
* **AI Development**: Modules divided by domain (conversation, scheduling, compliance), keeping the **modular monolith** simple and maintainable.

### Deployment & Infrastructure

* **Hosting Model**: Managed cloud services (Heroku/Netlify) preferred to minimize operational burden
* **Geographic Scope**: Los Angeles first, San Francisco second (10DLC compliance complexity)
* **Database Strategy**: Modular Monolith with single Postgres cluster, tenant-scoped tables via `tenant_id` column (ADR-0001). Modules are isolated in code, but share one schema for MVP.


### Development Constraints

* **Technology Stack**: Python/FastAPI backend, Next.js frontend (tailwind/shadcn) - no polyglot complexity
* **Integration Approach**: API-first design, avoid deep integrations that create maintenance burden
* **Third-party Dependencies**: Minimize vendor lock-in, prefer services with clear migration paths

### Business Model Constraints

* **Target Market**: SMBs (1-5 employees) - no enterprise features that complicate the product
* **Pricing Simplicity**: Transparent subscription model only; MVP ships a single paid plan `standard`
* **Support Model**: Self-service onboarding with email support, not white-glove service

### Risk Management

* **Compliance-First**: No SMS without 10DLC approval - hard gates prevent legal issues
* **Data Retention**: Clear policies (180 days for messages, 13 months metadata) to limit liability
* **Vendor Dependencies**: Twilio (messaging), Clerk (auth), Stripe (billing) - establish fallback plans

### Quality Gates

* **AI Code Generation**: All services must follow documentation-first development from `/docs/services/phase-1/`
* **Testing Philosophy**: Three-tier testing (unit/integration/e2e) with real business scenario validation
* **Performance Budgets**: Auto-SMS ≤5s P95, Booking API responses ≤500ms P95 (excluding 3rd party latency), UI freshness ≤2.5s P95, zero double-bookings

### Things that are complete

* **Twilio Server** Already complete.
* **Conversation AI** Already complete.
* **Scheduling** This is done, but getting and setting data from calendar is not complete.
* **10DLC Compliance** Manual in Phase 1.


# NeverMissCall — Product Description

*(Full specification preserved as before)*

---


## Addendum 1: Domain-Driven Design & Architectural Approach

### Architectural Style

NeverMissCall is a **DDD-driven Modular Monolith** with clear bounded contexts (ADR-0001..0010). Modules are strongly isolated in code and schema (tenant_id enforced), but run in a single deployable unit. This gives us low operational overhead for MVP scale (≤5,000 tenants) while preserving future **service extraction paths** if growth demands.

### Bounded Contexts (Modules)

1. **Telephony** – Handles Twilio webhooks, missed-call detection, caller identity, message forwarding.
2. **Conversation** – AI-driven SMS threads, human takeover, 60s timers, conversation state machines.
3. **Scheduling** – Job catalog, appointment booking, calendar integration (Jobber/Google), conflict prevention with Postgres `tstzrange` + GiST.
4. **Catalog** – Service item catalog, pricing, duration, and availability data.
5. **Compliance** – 10DLC brand/campaign, opt-outs, outbound message gates.
6. **Billing** – Stripe subscription mirror, subscription state events.
7. **Identity** – Tenant accounts, roles (OWNER/TECH), Clerk JWT enforcement.
8. **Reporting** – Cross-domain **read-model/projection** module for analytics and SLO tracking (not a transactional bounded context).

### Data & Consistency

* **Single PostgreSQL instance**, single schema, all tables tenant-scoped by `tenant_id` (ADR-0001).
* ACID transactions within modules (especially Scheduling to prevent double-booking).
* **Outbox pattern** used for domain events → projections and async flows.
* CQRS-lite: transactional writes, denormalized read models for performance.

### Integration Patterns

* **Idempotency keys** for Twilio/Stripe/Jobber/Google integrations.
* **Adapters** abstract external services to keep the core domain independent.
* **Contract tests** between modules enforce boundaries.

### Scalability & Growth Path

* Modular Monolith sufficient for target scale (≤5,000 users, ≤100 concurrent).
* If future scale demands, likely extractions are: Telephony Ingestion, Compliance workflows, Analytics pipeline.

---

**Summary:** This project is a **DDD-driven Modular Monolith**, optimized for SMB-focused MVP delivery. Modules enforce strong domain boundaries, enabling rapid development today and optional microservice extraction tomorrow.
