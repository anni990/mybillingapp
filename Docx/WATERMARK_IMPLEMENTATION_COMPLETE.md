# Subscription-Based Watermark Logic Implementation - Complete Guide

## Overview
Implemented comprehensive watermark system with subscription-tier based controls for MyBillingApp. Users can now manage watermark settings through their profile, with different permissions based on their subscription plan.

## Database Schema Changes

### New Fields Added to `shopkeepers` Table
```sql
-- Add watermark settings to shopkeepers table
ALTER TABLE shopkeepers ADD COLUMN watermark_enabled BOOLEAN DEFAULT TRUE COMMENT 'Whether watermark is enabled on bills';
ALTER TABLE shopkeepers ADD COLUMN watermark_type VARCHAR(20) DEFAULT 'diagonal' COMMENT 'Type of watermark: diagonal, bottom, centered';

-- Set watermark defaults based on subscription plan
UPDATE shopkeepers SET 
    watermark_enabled = CASE 
        WHEN subscription_plan = 'free' THEN TRUE 
        ELSE FALSE 
    END,
    watermark_type = 'diagonal'
WHERE watermark_enabled IS NULL OR watermark_type IS NULL;
```

## Business Logic Implementation

### Subscription Tier Rules
- **Free Users**: 
  - Watermark is mandatory (watermark_enabled = TRUE)
  - Cannot disable watermark from profile
  - Can choose watermark style (diagonal, bottom, centered)
  - Purpose: Brand visibility for free service

- **Lite/Gold Users**:
  - Watermark is optional (watermark_enabled defaults to FALSE)
  - Can toggle watermark on/off from profile
  - Can choose watermark style
  - Purpose: Premium experience without forced branding

### Watermark Types Available
1. **Diagonal Pattern** - Repeated "MyBillingApp" text diagonally across bill
2. **Bottom Logo** - Small "MyBillingApp" logo at bottom of bill
3. **Centered Background** - Large "MYBILLINGAPP" text as background

## Implementation Components

### 1. Database Model Updates
**File**: `app/models.py`
```python
# Added to Shopkeeper model:
watermark_enabled = db.Column(db.Boolean, default=True)  # Whether watermark is enabled
watermark_type = db.Column(db.String(20), default='diagonal')  # Type: diagonal, bottom, centered
```

### 2. Watermark Service Layer
**File**: `app/shopkeeper/services/watermark_service.py`

**Key Functions**:
- `get_watermark_rules()` - Returns subscription-based watermark rules
- `can_change_watermark_setting()` - Checks if user can modify watermark settings
- `validate_watermark_update()` - Validates watermark changes against business rules
- `get_watermark_display_info()` - Returns complete watermark info for templates
- `initialize_watermark_for_new_shopkeeper()` - Sets default watermark settings for new users

### 3. Bill Receipt Template Updates  
**File**: `app/templates/shopkeeper/bill_receipt.html`

**Key Changes**:
- Database-driven watermark display using `{% if shopkeeper.watermark_enabled %}`
- Conditional watermark type rendering based on `shopkeeper.watermark_type`
- JavaScript watermark generation only for enabled diagonal watermarks
- Fixed watermark positioning inside bill container (not behind it)

### 4. Profile Management Interface
**File**: `app/templates/shopkeeper/new_edit_profile.html`

**New Section Added**: "Watermark Settings"
- Subscription plan information display
- Enable/Disable watermark toggle (disabled for free users)
- Watermark style selection (radio buttons)
- Visual feedback and descriptions

### 5. Backend Profile Route Updates
**File**: `app/shopkeeper/views/profile.py`

**Key Updates**:
- Added watermark form handling in `profile_edit()` route
- Validation using `WatermarkService.validate_watermark_update()`
- Template context includes watermark display info and available types

### 6. Registration Process Updates
**File**: `app/auth/routes.py`

**Key Changes**:
- Added `WatermarkService.initialize_watermark_for_new_shopkeeper()` for both registration flows
- New shopkeepers get correct default watermark settings based on their subscription plan

### 7. Subscription Plan Updates
**File**: `app/shopkeeper/services/subscription_service.py`

**Key Updates**:
- Added automatic watermark adjustment when subscription plan changes
- Free → Paid: Disables watermark by default
- Paid → Free: Forces watermark to be enabled

## User Experience Flow

### For Free Users
1. **Registration**: Watermark enabled by default (diagonal style)
2. **Profile Management**: Cannot disable watermark, shows warning message
3. **Bill Generation**: Always shows selected watermark style
4. **Subscription Upgrade**: Watermark automatically disabled when upgrading to Lite/Gold

### For Lite/Gold Users
1. **Registration**: Watermark disabled by default
2. **Profile Management**: Full control over watermark on/off and style selection
3. **Bill Generation**: Shows watermark only if enabled by user
4. **Subscription Downgrade**: Watermark automatically enabled if downgraded to Free

## File Structure
```
app/
├── models.py (updated)
├── auth/routes.py (updated)
├── shopkeeper/
│   ├── services/
│   │   ├── watermark_service.py (new)
│   │   └── subscription_service.py (updated)
│   └── views/profile.py (updated)
└── templates/shopkeeper/
    ├── bill_receipt.html (updated)
    └── new_edit_profile.html (updated)

watermark_database_update.sql (new)
```

## Database Migration Required
Run the SQL commands in `watermark_database_update.sql` to add the new columns and set default values.

## Testing Checklist

### 1. Database Setup
- [ ] Run database migration SQL
- [ ] Verify new columns exist in shopkeepers table
- [ ] Check default values are set correctly

### 2. Free User Testing
- [ ] Register new free user - watermark should be enabled
- [ ] Try to disable watermark in profile - should show error message
- [ ] Change watermark style - should work
- [ ] Generate bill - watermark should appear
- [ ] Upgrade to Lite/Gold - watermark should be disabled

### 3. Lite/Gold User Testing
- [ ] New Lite/Gold user - watermark should be disabled by default
- [ ] Enable/disable watermark in profile - should work
- [ ] Change watermark style - should work
- [ ] Generate bill with watermark enabled - should appear
- [ ] Generate bill with watermark disabled - should not appear
- [ ] Downgrade to Free - watermark should be forced on

### 4. Bill Receipt Testing
- [ ] Diagonal watermark displays correctly
- [ ] Bottom watermark displays correctly  
- [ ] Centered watermark displays correctly
- [ ] Watermark appears inside bill container, not behind
- [ ] Print preview shows/hides watermark correctly

## Security Considerations
- Validation prevents free users from disabling watermark through direct API calls
- Subscription tier changes automatically adjust watermark settings
- Form validation ensures only valid watermark types are accepted

## Performance Notes
- Watermark generation is client-side JavaScript for diagonal pattern
- Database queries include watermark fields in existing shopkeeper lookups
- No additional database calls required for watermark display

## Future Enhancements
- Custom watermark text for premium users
- Watermark opacity/transparency controls
- Image-based watermarks for Gold users
- Position customization options