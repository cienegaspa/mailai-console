# Google OAuth Setup for MailAI Console

To enable Gmail account connections, you need to set up Google OAuth credentials. Follow these steps:

## 1. Create a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Note your project ID

## 2. Enable Gmail API

1. In the Google Cloud Console, navigate to **APIs & Services > Library**
2. Search for "Gmail API" 
3. Click on it and press **Enable**

## 3. Configure OAuth Consent Screen

1. Go to **APIs & Services > OAuth consent screen**
2. Choose **External** user type (unless you have a Google Workspace)
3. Fill in the required information:
   - App name: `MailAI Console`
   - User support email: Your email
   - Developer contact information: Your email
4. Add scopes:
   - `https://www.googleapis.com/auth/gmail.readonly`
5. Add test users if in development mode:
   - `tom@cienegaspa.com`
   - `rose@cienegaspa.com` 
   - `tbwerz@gmail.com`

## 4. Create OAuth Credentials

1. Go to **APIs & Services > Credentials**
2. Click **Create Credentials > OAuth client ID**
3. Choose **Web application**
4. Configure:
   - Name: `MailAI Console`
   - Authorized redirect URIs: `http://127.0.0.1:5170/auth/callback`
5. Copy the **Client ID** and **Client Secret**

## 5. Set Environment Variables

Create a `.env` file in the project root with:

```bash
# Google OAuth Configuration
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
GOOGLE_REDIRECT_URI=http://127.0.0.1:5170/auth/callback

# Optional: Custom database path
MAILAI_DB_PATH=./db/mailai.sqlite

# Set to false to use real providers (requires OAuth setup)
MAILAI_MOCKS=false
```

## 6. Restart the Application

After setting up the environment variables:

```bash
# Stop the current development servers
# Then restart with:
make dev
```

## 7. Test the Connection

1. Navigate to the Accounts page at http://127.0.0.1:5171/accounts
2. Click **Connect Account**
3. You should be redirected to Google's OAuth consent screen
4. Grant permissions and you'll be redirected back to the application

## Troubleshooting

### Common Issues

**Error: "redirect_uri_mismatch"**
- Ensure the redirect URI in Google Cloud Console exactly matches `http://127.0.0.1:5170/auth/callback`
- Check for trailing slashes or http vs https

**Error: "access_blocked"**
- Add your email addresses as test users in the OAuth consent screen
- Ensure the Gmail API is enabled for your project

**Error: "invalid_client"**
- Double-check your Client ID and Client Secret in the `.env` file
- Ensure there are no extra spaces or characters

### Development vs Production

For development, you can use `localhost` or `127.0.0.1`. For production deployment:

1. Update the redirect URI to your production domain
2. Add the production domain to authorized origins
3. Update the `GOOGLE_REDIRECT_URI` environment variable

### Security Notes

- Never commit your `.env` file to version control
- Rotate your OAuth credentials periodically
- Use different credentials for development and production environments
- Consider using Google Cloud Secret Manager for production deployments