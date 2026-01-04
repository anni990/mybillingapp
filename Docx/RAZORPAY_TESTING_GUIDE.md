# Razorpay Testing Setup Guide

## 🔧 Environment Variables (.env file)

Add these variables to your `.env` file:

```env
# Razorpay Test Configuration (for development)
RAZORPAY_KEY_ID_TEST=rzp_test_your_key_id_here
RAZORPAY_SECRET_KEY_TEST=your_test_secret_key_here
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret_here

# Flask Environment (set to 'development' for testing)
FLASK_ENV=development

# Optional: Razorpay Live Configuration (for production later)
RAZORPAY_KEY_ID_LIVE=rzp_live_your_key_id_here
RAZORPAY_SECRET_KEY_LIVE=your_live_secret_key_here
```

## 🌐 Getting Webhook Secret for Localhost Testing

### Method 1: Using ngrok (Recommended)

1. **Install ngrok**:
   ```powershell
   winget install ngrok
   ```

2. **Start your Flask app**:
   ```powershell
   python run.py
   ```

3. **In another terminal, expose localhost**:
   ```powershell
   ngrok http 5000
   ```

4. **Copy the ngrok URL** (e.g., `https://abc123.ngrok.io`)

5. **Configure webhook in Razorpay Dashboard**:
   - Go to https://dashboard.razorpay.com/
   - Switch to **Test Mode**
   - Navigate to **Settings** → **Webhooks**
   - Click **Create Webhook**
   - URL: `https://abc123.ngrok.io/shopkeeper/payment-webhook`
   - Events: Select `payment.captured`, `payment.failed`
   - Copy the webhook secret and add to `.env`

### Method 2: Using localtunnel (Alternative)

1. **Install localtunnel**:
   ```powershell
   npm install -g localtunnel
   ```

2. **Expose localhost**:
   ```powershell
   lt --port 5000 --subdomain myapp-test
   ```

3. **Use the URL**: `https://myapp-test.loca.lt/shopkeeper/payment-webhook`

## 🧪 Razorpay Test Cards

Use these test card numbers for testing:

### Success Cards
- **Visa**: `4111 1111 1111 1111`
- **Mastercard**: `5555 5555 5555 4444`
- **Rupay**: `6522 5285 0000 0008`

### Failure Cards
- **Insufficient Funds**: `4000 0000 0000 0002`
- **Invalid Card**: `4000 0000 0000 0010`

**Details for all cards**:
- CVV: Any 3 digits (e.g., `123`)
- Expiry: Any future date (e.g., `12/25`)
- Cardholder Name: Any name

## 📋 Testing Checklist

- [ ] Add Razorpay test credentials to `.env` file
- [ ] Run database migration: `mysql -u username -p database_name < razorpay_payment_schema.sql`
- [ ] Install dependencies: `pip install razorpay==1.3.0`
- [ ] Start Flask app: `python run.py`
- [ ] Set up ngrok tunnel
- [ ] Configure webhook in Razorpay Dashboard
- [ ] Test payment flow with test cards
- [ ] Verify webhook receives notifications
- [ ] Check payment history in subscription page

## 🐛 Debugging Tips

1. **Check browser console** for JavaScript errors
2. **Monitor Flask logs** for backend errors
3. **Check ngrok web interface** at `http://127.0.0.1:4040` for webhook requests
4. **Verify webhook signature** in Razorpay Dashboard logs

## 🔒 Security Notes for Testing

- Never commit real API keys to version control
- Use test mode for all development
- Test webhook signature validation
- Verify payment amount validation
- Test with different payment scenarios (success/failure)

## 🚀 Go Live Checklist (For Later)

- [ ] Get live API keys from Razorpay
- [ ] Update production webhook URL
- [ ] Set `FLASK_ENV=production` in production
- [ ] Enable SSL/HTTPS for webhook endpoint
- [ ] Test with small real amounts
- [ ] Monitor payment success rates