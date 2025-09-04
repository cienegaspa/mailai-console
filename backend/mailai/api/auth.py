"""Authentication and OAuth endpoints."""

import os
import secrets
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from ..providers.gmail_oauth import GmailOAuthProvider
from ..models.simple_db import get_session, GmailAccount

router = APIRouter()

# Initialize OAuth provider
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')
REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', 'http://127.0.0.1:5170/auth/callback')

gmail_provider = GmailOAuthProvider(
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    redirect_uri=REDIRECT_URI
)


class ConnectAccountResponse(BaseModel):
    auth_url: str
    state: str


class AccountInfo(BaseModel):
    account_id: str
    email: str
    display_name: Optional[str] = None
    status: str
    connected_at: Optional[str] = None
    last_sync: Optional[str] = None
    total_messages: int = 0
    sync_error: Optional[str] = None


@router.post("/auth/connect", response_model=ConnectAccountResponse)
async def connect_account():
    """Start OAuth flow for connecting Gmail account."""
    # Check if we're in mock mode
    import os
    use_mocks = os.getenv("MAILAI_MOCKS", "true").lower() == "true"
    
    if use_mocks:
        # Return mock OAuth URL for testing
        return ConnectAccountResponse(
            auth_url="http://127.0.0.1:5170/auth/callback?code=mock_auth_code&state=mock_state",
            state="mock_state"
        )
    
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables."
        )
    
    # Generate state parameter for CSRF protection
    state = secrets.token_urlsafe(32)
    
    # Create authorization URL
    auth_url = gmail_provider.create_auth_url(state=state)
    
    return ConnectAccountResponse(
        auth_url=auth_url,
        state=state
    )


@router.get("/auth/callback")
async def oauth_callback(request: Request):
    """Handle OAuth callback from Google."""
    try:
        # Check if we're in mock mode
        import os
        use_mocks = os.getenv("MAILAI_MOCKS", "true").lower() == "true"
        
        if use_mocks:
            # Mock successful OAuth callback
            query_params = dict(request.query_params)
            if query_params.get("code") == "mock_auth_code":
                # Create a mock account
                from datetime import datetime
                session = get_session()
                try:
                    mock_email = "tom@cienegaspa.com"
                    account = session.query(GmailAccount).filter_by(email=mock_email).first()
                    if not account:
                        account = GmailAccount(
                            account_id=mock_email,
                            email=mock_email,
                            display_name="Tom Werz",
                            access_token="mock_access_token",
                            refresh_token="mock_refresh_token",
                            status="connected",
                            connected_at=datetime.utcnow(),
                            total_messages=1247
                        )
                        session.add(account)
                        session.commit()
                
                    return RedirectResponse(
                        url=f"http://127.0.0.1:5171/accounts?connected={mock_email}"
                    )
                finally:
                    session.close()
            else:
                return RedirectResponse(
                    url=f"http://127.0.0.1:5171/accounts?error=Mock OAuth failed"
                )
        
        # Get the full callback URL
        authorization_response = str(request.url)
        
        # Handle the OAuth callback
        result = await gmail_provider.handle_oauth_callback(authorization_response)
        
        if result["success"]:
            # Redirect to frontend with success
            return RedirectResponse(
                url=f"http://127.0.0.1:5171/accounts?connected={result['email']}"
            )
        else:
            # Redirect to frontend with error
            return RedirectResponse(
                url=f"http://127.0.0.1:5171/accounts?error={result['error']}"
            )
            
    except Exception as e:
        return RedirectResponse(
            url=f"http://127.0.0.1:5171/accounts?error=OAuth callback failed: {str(e)}"
        )


@router.get("/accounts", response_model=List[AccountInfo])
async def list_accounts():
    """List all Gmail accounts."""
    try:
        accounts = await gmail_provider.list_accounts()
        return [AccountInfo(**account) for account in accounts]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accounts/{account_id}", response_model=AccountInfo)
async def get_account(account_id: str):
    """Get specific account information."""
    try:
        account = await gmail_provider.get_account_info(account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        return AccountInfo(**account)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/accounts/{account_id}/disconnect")
async def disconnect_account(account_id: str):
    """Disconnect a Gmail account."""
    try:
        success = await gmail_provider.disconnect_account(account_id)
        if not success:
            raise HTTPException(status_code=404, detail="Account not found")
        return {"success": True, "message": "Account disconnected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/accounts/{account_id}/sync")
async def sync_account(account_id: str):
    """Trigger manual sync for an account."""
    try:
        account = await gmail_provider.get_account_info(account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        if account["status"] != "connected":
            raise HTTPException(status_code=400, detail="Account is not connected")
        
        # TODO: Implement sync logic
        return {"success": True, "message": "Sync started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auth/status")
async def auth_status():
    """Check OAuth configuration status."""
    return {
        "oauth_configured": bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET),
        "client_id_set": bool(GOOGLE_CLIENT_ID),
        "client_secret_set": bool(GOOGLE_CLIENT_SECRET),
        "redirect_uri": REDIRECT_URI
    }


@router.get("/auth/test/{account_id}")
async def test_auth(account_id: str):
    """Test authentication by getting user profile info."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from ..models.simple_db import get_session, GmailAccount
        
        session = get_session()
        try:
            account = session.query(GmailAccount).filter_by(account_id=account_id).first()
            if not account or not account.access_token:
                return {"success": False, "error": "No valid credentials found"}
            
            credentials = Credentials(
                token=account.access_token,
                refresh_token=account.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=GOOGLE_CLIENT_ID,
                client_secret=GOOGLE_CLIENT_SECRET
            )
            
            # Test 1: Get user profile info (basic auth test)
            oauth_service = build('oauth2', 'v2', credentials=credentials)
            profile = oauth_service.userinfo().get().execute()
            
            # Test 2: Try Gmail API access
            gmail_service = build('gmail', 'v1', credentials=credentials)
            gmail_profile = gmail_service.users().getProfile(userId='me').execute()
            
            return {
                "success": True,
                "auth_working": True,
                "gmail_api_working": True,
                "user_email": profile.get("email"),
                "gmail_address": gmail_profile.get("emailAddress"),
                "total_messages": gmail_profile.get("messagesTotal", 0),
                "scopes_granted": "Available in token"
            }
            
        finally:
            session.close()
            
    except Exception as e:
        return {
            "success": False,
            "auth_working": False,
            "gmail_api_working": False,
            "error": str(e)
        }