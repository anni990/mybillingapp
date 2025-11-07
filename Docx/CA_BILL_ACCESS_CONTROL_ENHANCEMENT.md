# CA Bill Access Control Enhancement

## Issue Description
The CA's view bill route (`@bp.route('/bill/<int:bill_id>')`) was missing proper access control constraints. Any CA could potentially view bills from any shopkeeper, even if they weren't connected to that CA. This was a security vulnerability that needed to be addressed.

## Security Enhancement Implemented

### Access Control Logic Added
Added comprehensive access control checks to ensure users can only view bills they have legitimate access to:

#### For CA Users:
1. **CA Profile Verification**: Check if CA profile exists
2. **Connection Validation**: Verify the bill's shopkeeper is connected to the CA
3. **Status Check**: Ensure the connection status is 'approved'

#### For Employee Users:
1. **Employee Profile Verification**: Check if employee profile exists  
2. **Assignment Validation**: Verify the bill's shopkeeper is assigned to the employee
3. **Client Relationship Check**: Ensure valid EmployeeClient relationship exists

#### For Shopkeeper Users:
1. **Ownership Validation**: Shopkeepers can only view their own bills
2. **User ID Verification**: Check bill.shopkeeper.user_id matches current_user.user_id

#### For Other Roles:
1. **Role Validation**: Reject access for any other roles
2. **Proper Redirection**: Redirect to appropriate login page

## Files Modified

### app/ca/views/bills.py
**Location:** `view_bill()` function around line 105
**Enhancement:** Added comprehensive access control after `bill = Bill.query.get_or_404(bill_id)`

**Code Added:**
```python
# Access control: Check if current user can access this bill
if current_user.role == 'CA':
    ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
    if not ca:
        flash('Access denied: CA profile not found.', 'danger')
        return redirect(url_for('ca.bills_panel'))
    
    # Check if the bill's shopkeeper is connected to this CA
    ca_connection = CAConnection.query.filter_by(
        shopkeeper_id=bill.shopkeeper_id,
        ca_id=ca.ca_id,
        status='approved'
    ).first()
    
    if not ca_connection:
        flash('Access denied: You can only view bills from connected shopkeepers.', 'danger')
        return redirect(url_for('ca.bills_panel'))
        
elif current_user.role == 'employee':
    employee = CAEmployee.query.filter_by(user_id=current_user.user_id).first()
    if not employee:
        flash('Access denied: Employee profile not found.', 'danger')
        return redirect(url_for('ca.bills_panel'))
    
    # Check if the bill's shopkeeper is assigned to this employee
    employee_client = EmployeeClient.query.filter_by(
        shopkeeper_id=bill.shopkeeper_id,
        employee_id=employee.employee_id
    ).first()
    
    if not employee_client:
        flash('Access denied: You can only view bills from assigned shopkeepers.', 'danger')
        return redirect(url_for('ca.bills_panel'))
        
elif current_user.role == 'shopkeeper':
    # Shopkeepers can only view their own bills
    if bill.shopkeeper.user_id != current_user.user_id:
        flash('Access denied: You can only view your own bills.', 'danger')
        return redirect(url_for('shopkeeper.manage_bills'))
else:
    flash('Access denied: Invalid role.', 'danger')
    return redirect(url_for('auth.login'))
```

## Security Benefits

### 1. Data Privacy Protection
- CAs can only access bills from shopkeepers who have explicitly connected to them
- Employees can only access bills from shopkeepers assigned to them by the CA
- Shopkeepers can only access their own bills
- No unauthorized cross-tenant data access

### 2. Multi-Tenant Security
- Proper tenant isolation between different CAs
- Employee access is properly scoped to their assigned clients
- Prevents data leakage between unrelated business entities

### 3. Role-Based Access Control (RBAC)
- Each role has clearly defined access permissions
- Proper validation of role-specific relationships
- Graceful handling of invalid or missing profiles

### 4. User Experience
- Clear, informative error messages for access denied scenarios
- Proper redirection to appropriate pages based on user role
- Maintains application flow while enforcing security

## Database Relationships Validated

### CAConnection Table
- **Purpose**: Links CAs to Shopkeepers
- **Validation**: `shopkeeper_id`, `ca_id`, `status='approved'`
- **Security**: Ensures only approved connections grant access

### EmployeeClient Table  
- **Purpose**: Links CA Employees to assigned Shopkeepers
- **Validation**: `shopkeeper_id`, `employee_id`
- **Security**: Ensures employees only access assigned clients

### User-Bill Relationship
- **Purpose**: Links Bills to Shopkeeper owners
- **Validation**: `bill.shopkeeper.user_id` vs `current_user.user_id`
- **Security**: Ensures shopkeepers only access their own data

## Error Handling

### Flash Messages
- **CA Profile Missing**: "Access denied: CA profile not found."
- **No Connection**: "You can only view bills from connected shopkeepers."
- **Employee Profile Missing**: "Access denied: Employee profile not found."
- **No Assignment**: "You can only view bills from assigned shopkeepers."
- **Not Bill Owner**: "You can only view your own bills."
- **Invalid Role**: "Access denied: Invalid role."

### Redirection Logic
- **CA/Employee**: Redirect to `ca.bills_panel`
- **Shopkeeper**: Redirect to `shopkeeper.manage_bills`  
- **Invalid Role**: Redirect to `auth.login`

## Testing Recommendations

### Security Test Cases
1. **CA Access Test**: CA tries to access bill from non-connected shopkeeper → Should be denied
2. **Employee Access Test**: Employee tries to access bill from non-assigned shopkeeper → Should be denied
3. **Cross-Tenant Test**: CA tries to access bill from shopkeeper connected to different CA → Should be denied
4. **Shopkeeper Cross-Access**: Shopkeeper tries to access another shopkeeper's bill → Should be denied
5. **Invalid Role Test**: User with unknown role tries to access bill → Should be denied

### Functional Test Cases
1. **Valid CA Access**: CA accesses bill from connected, approved shopkeeper → Should succeed
2. **Valid Employee Access**: Employee accesses bill from assigned shopkeeper → Should succeed  
3. **Valid Shopkeeper Access**: Shopkeeper accesses their own bill → Should succeed
4. **Connection Status**: Test with pending/rejected connections → Should be denied
5. **Profile Existence**: Test with missing CA/Employee profiles → Should be denied

## Performance Considerations

### Database Queries Added
- **CA Route**: 2 additional queries (CharteredAccountant lookup + CAConnection check)
- **Employee Route**: 2 additional queries (CAEmployee lookup + EmployeeClient check)
- **Shopkeeper Route**: No additional queries (existing relationship used)

### Query Optimization
- All validation queries use indexed foreign keys
- Simple lookups with no complex joins
- Minimal performance impact due to security criticality

## Future Enhancements

### Potential Improvements
1. **Caching**: Cache user profiles and connections to reduce database queries
2. **Middleware**: Move access control to middleware for consistent application across routes
3. **Audit Logging**: Log access attempts for security monitoring
4. **Permission Levels**: Add more granular permissions (view-only, edit, etc.)

## Compliance Notes
- Implements proper multi-tenant data isolation
- Follows principle of least privilege access
- Provides clear audit trail through flash messages
- Maintains data integrity while ensuring security