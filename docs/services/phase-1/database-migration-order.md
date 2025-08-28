# Database Migration Order - Phase 1

## Single Database Architecture

**Database**: `nevermisscall` (single PostgreSQL database)
**Services**: All Phase 1 services use the same database
**Benefits**: 
- ✅ Foreign key constraints work properly
- ✅ Simpler deployment and management
- ✅ Better consistency and transactions
- ✅ Optimal for small project scale

## Migration Execution Order

### Step 1: Create Database
```sql
CREATE DATABASE nevermisscall;
```

### Step 2: Create Tables (Dependency Order)

#### Core Identity Tables (No Dependencies)
```sql
-- 1. Users table (foundation for authentication)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 2. Tenants table (foundation for business data)  
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_name VARCHAR(255) NOT NULL,
    business_address TEXT,
    business_latitude DECIMAL(10, 8),
    business_longitude DECIMAL(11, 8),
    trade_type VARCHAR(100),
    service_area_radius INTEGER DEFAULT 25,
    onboarding_completed BOOLEAN DEFAULT false,
    onboarding_step INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### User Management Tables (Depend on: users, tenants)
```sql
-- 3. User Profiles (depends on: users, tenants)
CREATE TABLE user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(255),
    phone_number VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_user_profiles_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_user_profiles_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

-- 4. User Preferences (depends on: users)
CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    notification_email BOOLEAN DEFAULT true,
    notification_sms BOOLEAN DEFAULT true,
    notification_push BOOLEAN DEFAULT true,
    ai_takeover_delay INTEGER DEFAULT 60,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_user_preferences_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 5. User Status (depends on: users)
CREATE TABLE user_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_online BOOLEAN DEFAULT false,
    status VARCHAR(50) DEFAULT 'available',
    last_seen_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_user_status_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 6. User Sessions (depends on: users)
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_sessions_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

#### Business Configuration Tables (Depend on: tenants)
```sql
-- 7. Business Settings (depends on: tenants)
CREATE TABLE business_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    business_hours JSONB DEFAULT '{"monday":{"open":"09:00","close":"17:00","enabled":true},"tuesday":{"open":"09:00","close":"17:00","enabled":true},"wednesday":{"open":"09:00","close":"17:00","enabled":true},"thursday":{"open":"09:00","close":"17:00","enabled":true},"friday":{"open":"09:00","close":"17:00","enabled":true},"saturday":{"open":"09:00","close":"17:00","enabled":false},"sunday":{"open":"09:00","close":"17:00","enabled":false}}',
    timezone VARCHAR(50) DEFAULT 'America/New_York',
    auto_response_enabled BOOLEAN DEFAULT true,
    auto_response_message TEXT DEFAULT 'Hi! Sorry we missed your call. How can we help?',
    ai_greeting_template TEXT DEFAULT 'Hello! I''m here to help with your [TRADE] needs. What can I assist you with today?',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_business_settings_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

-- 8. Phone Numbers (depends on: tenants)
CREATE TABLE phone_numbers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL UNIQUE, -- One number per tenant in Phase 1
    
    -- Twilio Information
    phone_number VARCHAR(20) NOT NULL UNIQUE, -- E.164 format
    phone_number_sid VARCHAR(100) UNIQUE NOT NULL,
    messaging_service_sid VARCHAR(100),
    
    -- Number Details
    friendly_name VARCHAR(255),
    area_code VARCHAR(5) NOT NULL,
    region VARCHAR(100),
    number_type VARCHAR(20) DEFAULT 'local',
    capabilities TEXT[] DEFAULT ARRAY['voice', 'sms'],
    
    -- Status and Lifecycle
    status VARCHAR(50) DEFAULT 'provisioning',
    status_reason TEXT,
    date_provisioned TIMESTAMP,
    date_released TIMESTAMP,
    
    -- Configuration
    webhooks_configured BOOLEAN DEFAULT false,
    voice_webhook_url TEXT NOT NULL,
    sms_webhook_url TEXT NOT NULL,
    status_callback_url TEXT,
    
    -- Billing
    monthly_price_cents INTEGER DEFAULT 100,
    setup_price_cents INTEGER DEFAULT 0,
    currency VARCHAR(3) DEFAULT 'USD',
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_phone_numbers_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

-- 9. Messaging Services (depends on: phone_numbers)
CREATE TABLE messaging_services (
    phone_number_id UUID PRIMARY KEY,
    messaging_service_sid VARCHAR(100) UNIQUE NOT NULL,
    friendly_name VARCHAR(255) NOT NULL,
    inbound_webhook_url TEXT NOT NULL,
    inbound_method VARCHAR(10) DEFAULT 'POST',
    fallback_url TEXT,
    status_callback TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_messaging_services_phone FOREIGN KEY (phone_number_id) REFERENCES phone_numbers(id) ON DELETE CASCADE
);
```

#### Call Processing Tables (Depend on: tenants)
```sql
-- 10. Calls (depends on: tenants)
CREATE TABLE calls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_sid VARCHAR(100) UNIQUE NOT NULL,
    tenant_id UUID NOT NULL,
    
    -- Call participants
    customer_phone VARCHAR(20) NOT NULL,
    business_phone VARCHAR(20) NOT NULL,
    
    -- Call details
    direction VARCHAR(20) DEFAULT 'inbound',
    status VARCHAR(50) DEFAULT 'ringing',
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    duration INTEGER DEFAULT 0,
    
    -- Processing status
    processed BOOLEAN DEFAULT false,
    sms_triggered BOOLEAN DEFAULT false,
    conversation_created BOOLEAN DEFAULT false,
    lead_created BOOLEAN DEFAULT false,
    
    -- Related entities
    conversation_id UUID,
    lead_id UUID,
    
    -- Geographic data
    caller_city VARCHAR(100),
    caller_state VARCHAR(50),
    caller_country VARCHAR(3) DEFAULT 'US',
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_calls_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);

-- 11. Conversations (depends on: calls, tenants)
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    call_id UUID NOT NULL,
    
    -- Participants
    customer_phone VARCHAR(20) NOT NULL,
    business_phone VARCHAR(20) NOT NULL,
    
    -- Conversation state
    status VARCHAR(50) DEFAULT 'active',
    ai_active BOOLEAN DEFAULT false,
    human_active BOOLEAN DEFAULT false,
    
    -- Timing
    ai_handoff_time TIMESTAMP,
    human_takeover_time TIMESTAMP,
    last_message_time TIMESTAMP DEFAULT NOW(),
    last_human_response_time TIMESTAMP,
    
    -- Metrics
    message_count INTEGER DEFAULT 0,
    ai_message_count INTEGER DEFAULT 0,
    human_message_count INTEGER DEFAULT 0,
    
    -- Outcomes
    outcome VARCHAR(50),
    appointment_scheduled BOOLEAN DEFAULT false,
    
    -- Related entities
    lead_id UUID,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_conversations_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id),
    CONSTRAINT fk_conversations_call FOREIGN KEY (call_id) REFERENCES calls(id)
);

-- 12. Messages (depends on: conversations, tenants)
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    
    -- Message details
    message_sid VARCHAR(100),
    direction VARCHAR(20) NOT NULL,
    sender VARCHAR(20) NOT NULL,
    body TEXT NOT NULL,
    
    -- Processing
    processed BOOLEAN DEFAULT false,
    ai_processed BOOLEAN DEFAULT false,
    confidence DECIMAL(3,2),
    intent VARCHAR(100),
    
    -- Delivery
    status VARCHAR(50) DEFAULT 'sent',
    error_code INTEGER,
    error_message TEXT,
    
    -- Timing
    sent_at TIMESTAMP DEFAULT NOW(),
    delivered_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_messages_conversation FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    CONSTRAINT fk_messages_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);

-- 13. Leads (depends on: calls, conversations, tenants)
CREATE TABLE leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    conversation_id UUID NOT NULL,
    call_id UUID NOT NULL,
    
    -- Customer information
    customer_phone VARCHAR(20) NOT NULL,
    customer_name VARCHAR(255),
    customer_email VARCHAR(255),
    customer_address TEXT,
    
    -- Lead details
    problem_description TEXT NOT NULL,
    job_type VARCHAR(100),
    urgency_level VARCHAR(20) DEFAULT 'normal',
    estimated_value DECIMAL(10,2),
    
    -- Lead status
    status VARCHAR(50) DEFAULT 'new',
    status_notes TEXT,
    
    -- AI analysis (stored as JSONB)
    ai_analysis JSONB,
    
    -- Outcomes
    appointment_id UUID,
    conversion_value DECIMAL(10,2),
    lost_reason TEXT,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_leads_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id),
    CONSTRAINT fk_leads_conversation FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    CONSTRAINT fk_leads_call FOREIGN KEY (call_id) REFERENCES calls(id)
);
```

#### Add Cross-Table Foreign Keys (After All Tables Created)
```sql
-- Update calls table with FK to conversations and leads
ALTER TABLE calls 
    ADD CONSTRAINT fk_calls_conversation FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    ADD CONSTRAINT fk_calls_lead FOREIGN KEY (lead_id) REFERENCES leads(id);

-- Update conversations table with FK to leads  
ALTER TABLE conversations
    ADD CONSTRAINT fk_conversations_lead FOREIGN KEY (lead_id) REFERENCES leads(id);
```

### Step 3: Create Indexes (Performance Optimization)

```sql
-- User and tenant indexes
CREATE INDEX idx_user_profiles_tenant ON user_profiles (tenant_id);
CREATE INDEX idx_user_profiles_email ON user_profiles (email);
CREATE INDEX idx_user_status_active ON user_status (is_active, is_online);
CREATE INDEX idx_user_status_last_seen ON user_status (last_seen_at);

-- Tenant and business indexes
CREATE INDEX idx_tenants_business_location ON tenants (business_latitude, business_longitude);
CREATE INDEX idx_tenants_trade_type ON tenants (trade_type);
CREATE INDEX idx_tenants_onboarding ON tenants (onboarding_completed, onboarding_step);
CREATE INDEX idx_business_settings_tenant ON business_settings (tenant_id);

-- Phone number indexes
CREATE UNIQUE INDEX idx_phone_numbers_tenant ON phone_numbers (tenant_id);
CREATE UNIQUE INDEX idx_phone_numbers_phone ON phone_numbers (phone_number);
CREATE UNIQUE INDEX idx_phone_numbers_sid ON phone_numbers (phone_number_sid);
CREATE INDEX idx_phone_numbers_status ON phone_numbers (status);
CREATE INDEX idx_phone_numbers_area_code ON phone_numbers (area_code, region);

-- Call processing indexes
CREATE INDEX idx_calls_tenant_status ON calls (tenant_id, status);
CREATE INDEX idx_calls_customer_phone ON calls (customer_phone);
CREATE INDEX idx_calls_start_time ON calls (start_time DESC);
CREATE INDEX idx_calls_call_sid ON calls (call_sid); -- Twilio webhook lookups

CREATE INDEX idx_conversations_tenant_status ON conversations (tenant_id, status);
CREATE INDEX idx_conversations_customer_phone ON conversations (customer_phone);
CREATE INDEX idx_conversations_ai_active ON conversations (ai_active, status);

CREATE INDEX idx_messages_conversation ON messages (conversation_id, created_at DESC);
CREATE INDEX idx_messages_tenant_direction ON messages (tenant_id, direction);
CREATE INDEX idx_messages_message_sid ON messages (message_sid); -- Twilio webhook lookups

CREATE INDEX idx_leads_tenant_status ON leads (tenant_id, status);
CREATE INDEX idx_leads_customer_phone ON leads (customer_phone);
CREATE INDEX idx_leads_created_at ON leads (created_at DESC);
```

## Database Connection Configuration

All Phase 1 services use the same database connection:

```bash
DATABASE_URL=postgresql://user:password@localhost:5432/nevermisscall
```

## Migration Script Execution

```bash
# Run migrations in this exact order
psql -h localhost -U postgres -f 01-create-database.sql
psql -h localhost -U postgres -d nevermisscall -f 02-create-core-tables.sql
psql -h localhost -U postgres -d nevermisscall -f 03-create-user-tables.sql
psql -h localhost -U postgres -d nevermisscall -f 04-create-business-tables.sql
psql -h localhost -U postgres -d nevermisscall -f 05-create-call-tables.sql
psql -h localhost -U postgres -d nevermisscall -f 06-add-foreign-keys.sql
psql -h localhost -U postgres -d nevermisscall -f 07-create-indexes.sql
```

This migration order ensures:
- ✅ No foreign key constraint failures
- ✅ All tables created in dependency order
- ✅ Optimal indexing for Phase 1 performance requirements
- ✅ Single database simplifies deployment and management