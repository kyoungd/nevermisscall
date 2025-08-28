# Database Migrations

This directory contains database migration files for the NeverMissCall shared database.

## Migration Naming Convention

Migration files should follow this pattern:
```
YYYYMMDDHHMMSS_description.sql
```

For example:
- `20240101120000_create_users_table.sql`
- `20240101130000_create_tenants_table.sql`

## Running Migrations

From any service directory:

```python
from shared.database import SimpleMigrationManager

# Initialize migration manager
manager = SimpleMigrationManager()

# Check migration status
status = await manager.get_status()
print(f"Executed: {status['total_executed']}, Pending: {status['total_pending']}")

# Run pending migrations
executed = await manager.run_migrations()
print(f"Executed {len(executed)} migrations")
```

## Migration Order

Migrations should follow the dependency order defined in `database-migration-order.md`:

1. Core tables (users, tenants)
2. User management tables
3. Business configuration tables  
4. Call processing tables
5. Cross-table foreign keys
6. Indexes for performance

## Creating New Migrations

```python
# Create a new migration file
filename = await manager.create_migration("add user preferences table")
print(f"Created: {filename}")
```

This will create a template migration file with proper structure and comments.

## Migration File Structure

Each migration should include:
- Descriptive comment header
- SQL commands following database architecture patterns
- Proper foreign key constraints
- Appropriate indexes

Example:
```sql
-- Migration: Add user preferences table
-- Created: 2024-01-01T12:00:00
-- Version: 20240101120000

CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    notification_email BOOLEAN DEFAULT true,
    notification_sms BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_user_preferences_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_user_preferences_user ON user_preferences (user_id);
```