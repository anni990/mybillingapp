# MyBillingApp Changelog

## [2025-10-12] - CA Connection Request Fix

### Fixed
- **404 Error on Connection Requests**: Fixed shopkeeper CA connection request functionality
  - **Issue**: JavaScript was calling non-existent route `/shopkeeper/send_connection_request`
  - **Root Cause**: Route mismatch between frontend and backend
  - **Solution**: Updated JavaScript to use correct route `/shopkeeper/request_connection/{ca_id}`

### Technical Changes

#### Frontend Changes (`app/templates/shopkeeper/ca_marketplace.html`)
- Fixed AJAX endpoint URL from `/shopkeeper/send_connection_request` to `/shopkeeper/request_connection/${currentCAId}`
- Updated request headers to include `X-Requested-With: XMLHttpRequest` for AJAX detection
- Removed JSON body payload (ca_id now passed as URL parameter)

#### Backend Changes (`app/shopkeeper/views/ca_connections.py`)
- Added AJAX request detection using `X-Requested-With` header
- Enhanced `request_connection` route to return JSON responses for AJAX calls
- Fixed model field usage: removed invalid `request_date` parameter (uses existing `created_at`)
- Added proper error handling for both AJAX and regular form submissions

#### Database
- **No database changes required**
- Schema was already correct with `created_at` and `updated_at` fields
- Issue was code using wrong field name, not missing database fields

### Route Details
- **Correct Route**: `POST /shopkeeper/request_connection/<int:ca_id>`
- **Parameters**: `ca_id` passed as URL parameter
- **Response**: JSON for AJAX requests, redirect for form submissions
- **Authentication**: Requires `@login_required` and `@shopkeeper_required`

### Error Messages Fixed
- `404 NOT FOUND` on connection requests
- `500 INTERNAL SERVER ERROR` due to invalid model field
- `TypeError: 'request_date' is an invalid keyword argument for ShopConnection`

### Files Modified
1. `app/templates/shopkeeper/ca_marketplace.html` - JavaScript fetch URL and headers
2. `app/shopkeeper/views/ca_connections.py` - Route logic and model usage
3. `update_schema.sql` - Documentation (new file)
4. `CHANGELOG.md` - This file (new)

### Testing
- Connection requests now work without 404/500 errors
- AJAX requests return proper JSON responses
- Form submissions still work with redirects
- Error cases handled with appropriate user feedback