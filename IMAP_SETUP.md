# Gmail IMAP Setup with App Password

**Much simpler than OAuth!** No Google Cloud Console, no verification process, no videos required.

## Step 1: Enable 2-Factor Authentication

1. Go to your [Google Account settings](https://myaccount.google.com/security)
2. Under "Signing in to Google", click **2-Step Verification**
3. Follow the prompts to enable 2FA (if not already enabled)

## Step 2: Generate App Password

1. Still in [Google Account settings](https://myaccount.google.com/security)
2. Under "Signing in to Google", click **App passwords**
   - If you don't see this option, make sure 2FA is enabled first
3. Click **Select app** → **Mail**
4. Click **Select device** → **Other** (custom name)
5. Type: **MailAI Console**
6. Click **GENERATE**
7. **Copy the 16-character password** (something like `abcd efgh ijkl mnop`)

## Step 3: Configure MailAI

1. Open your `.env` file in the project root
2. Update these lines:
   ```bash
   # Option 2: IMAP (simple, uses app password)
   GMAIL_IMAP_EMAIL=tom@cienegaspa.com
   GMAIL_IMAP_APP_PASSWORD=your_16_char_app_password_here
   
   # Provider Mode: mock, oauth, or imap
   MAILAI_GMAIL_MODE=imap
   ```

3. **Replace `your_16_char_app_password_here` with the password from Step 2**

## Step 4: Restart and Test

1. **Restart MailAI servers:**
   ```bash
   # Press Ctrl+C to stop current servers, then:
   make dev
   ```

2. **Check the logs** - you should see:
   ```
   ✅ Gmail IMAP provider initialized for tom@cienegaspa.com
   ```

3. **Test connection:**
   ```bash
   curl -X POST http://127.0.0.1:5170/auth/connect-imap \
     -H "Content-Type: application/json" \
     -d '{"email": "tom@cienegaspa.com", "app_password": "your_app_password"}'
   ```

## Step 5: Use Real Gmail Data

Once connected, your MailAI queries will use **real Gmail data** instead of mock data!

- Navigate to http://127.0.0.1:5171
- Create a new run with a question
- Watch it search your actual Gmail messages

## Advantages of IMAP vs OAuth

✅ **No Google verification process**  
✅ **No privacy policy or videos required**  
✅ **Works immediately with any Gmail account**  
✅ **Perfect for local development tools**  
✅ **No redirect URI configuration**  
✅ **No test user limitations**  

## Security Notes

- App passwords are Gmail-specific and can be revoked anytime
- They only work with IMAP/SMTP, not full Google APIs
- Perfect security level for local tools
- Store the password in `.env` (already in `.gitignore`)

## Troubleshooting

**"Authentication failed"**
- Double-check the app password (16 characters, no spaces)
- Make sure 2FA is enabled on your Google account
- Try generating a new app password

**"Connection refused"**  
- Check your internet connection
- Gmail IMAP uses port 993 (SSL/TLS)

**"Can't find App passwords option"**
- Make sure 2-Step Verification is enabled first
- Wait a few minutes after enabling 2FA

---

**Ready to connect?** Follow the steps above and you'll be using real Gmail data in under 5 minutes!