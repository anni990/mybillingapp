# Google OAuth "Blocked" Error - Solutions

## Issue: Google OAuth shows "This app is blocked"

This happens because Google requires proper OAuth consent screen configuration for production apps.

## Solutions:

### 1. **OAuth Consent Screen Configuration**
Go to Google Cloud Console → APIs & Services → OAuth consent screen:

**User Type**: Choose "External" (for testing with any Google account)

**App Information**:
- App name: `MyBillingApp`
- User support email: `your-email@gmail.com`
- Developer contact information: `your-email@gmail.com`

**Scopes**: Add these scopes:
- `openid`
- `email` 
- `profile`

**Test Users**: Add your Gmail addresses for testing

### 2. **Verification Status**
For development/testing, you don't need full verification. But ensure:
- OAuth consent screen is configured
- App is in "Testing" mode (allows up to 100 test users)
- Your email is added as a test user

### 3. **Redirect URI Exact Match**
Ensure your Google Cloud Console redirect URI **exactly** matches:
```
http://localhost:5000/auth/google/callback
```

### 4. **Environment Variables**
Verify your `.env` file has correct values:
```
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
```

### 5. **Quick Fix for Testing**

If still blocked, try these steps in order:

1. **Go to Google Cloud Console**
2. **APIs & Services → OAuth consent screen**
3. **Set User Type to "External"**
4. **Fill required fields (app name, emails)**
5. **Save and Continue**
6. **Add Scopes: openid, email, profile**
7. **Add Test Users → Add your Gmail**
8. **Credentials → OAuth 2.0 Client IDs → Edit**
9. **Verify redirect URI: `http://localhost:5000/auth/google/callback`**

### 6. **Alternative for Immediate Testing**

If Google blocks your app, you can temporarily test OAuth flow by:
1. Using Google's OAuth Playground: https://developers.google.com/oauthplayground/
2. Or creating a new Google Cloud Project with fresh OAuth credentials

## Common Errors and Fixes:

- **"redirect_uri_mismatch"**: Update redirect URI in Google Console
- **"access_blocked"**: Configure OAuth consent screen properly  
- **"invalid_client"**: Check client ID and secret in `.env`
- **"unauthorized_client"**: Ensure your domain is authorized

## Production Checklist:

For production deployment:
1. Complete OAuth consent screen verification
2. Update redirect URIs for production domain
3. Set proper scopes and privacy policy
4. Remove test user restrictions

## Need Help?

If you're still getting blocked:
1. Share your Google Cloud Console screenshots (OAuth consent screen)
2. Check if your app is in "Testing" vs "Production" mode
3. Verify test users are added correctly