"""Authentication and OAuth endpoints."""

import os
import secrets
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from ..providers.gmail_oauth import GmailOAuthProvider
from ..providers.gmail_imap import GmailIMAPProvider
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


class ConnectIMAPRequest(BaseModel):
    email: str
    app_password: str


class ConnectIMAPResponse(BaseModel):
    success: bool
    message: str
    email: Optional[str] = None
    error: Optional[str] = None


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


@router.post("/auth/connect-imap", response_model=ConnectIMAPResponse)
async def connect_imap_account(request: ConnectIMAPRequest):
    """Connect Gmail account using IMAP with app password."""
    try:
        # Create IMAP provider
        imap_provider = GmailIMAPProvider(
            email_address=request.email,
            app_password=request.app_password
        )
        
        # Test connection and store account
        result = await imap_provider.connect_account()
        
        if result["success"]:
            return ConnectIMAPResponse(
                success=True,
                message=f"Successfully connected {request.email} via IMAP",
                email=request.email
            )
        else:
            return ConnectIMAPResponse(
                success=False,
                message="IMAP connection failed",
                error=result["error"]
            )
            
    except Exception as e:
        return ConnectIMAPResponse(
            success=False,
            message="IMAP connection failed", 
            error=str(e)
        )


@router.get("/auth/callback")
async def oauth_callback(request: Request):
    """Handle OAuth callback from Google."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"🔵 OAuth callback received with URL: {request.url}")
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
        logger.info(f"🔵 Processing OAuth callback with authorization_response: {authorization_response}")
        
        # Handle the OAuth callback
        logger.info("🔵 Calling gmail_provider.handle_oauth_callback...")
        result = await gmail_provider.handle_oauth_callback(authorization_response)
        logger.info(f"🔵 OAuth callback result: {result}")
        
        if result["success"]:
            # Redirect to frontend with success
            logger.info(f"✅ OAuth successful for {result['email']}, redirecting to frontend")
            return RedirectResponse(
                url=f"http://127.0.0.1:5171/accounts?connected={result['email']}"
            )
        else:
            # Redirect to frontend with error
            logger.error(f"❌ OAuth failed: {result['error']}, redirecting to frontend with error")
            return RedirectResponse(
                url=f"http://127.0.0.1:5171/accounts?error={result['error']}"
            )
            
    except Exception as e:
        logger.error(f"❌ OAuth callback exception: {e}")
        logger.exception("Full OAuth callback exception traceback:")
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


@router.get("/accounts/recent-messages")
async def get_all_recent_messages(days: int = 1, limit_per_account: int = 10):
    """Get recent messages from all connected accounts."""
    print(f"🔵 get_all_recent_messages called with days={days}, limit_per_account={limit_per_account}")
    print("🔵 Entered get_all_recent_messages function")
    try:
        # Get accounts directly from database instead of using OAuth provider
        from ..models.simple_db import get_session, GmailAccount
        
        session = get_session()
        try:
            accounts = session.query(GmailAccount).filter_by(status="connected").all()
            all_messages = []
            
            for account in accounts:
                try:
                    print(f"🔵 Fetching messages from {account.email}...")
                    
                    # Extract app password from stored token
                    if not account.access_token or not account.access_token.startswith("imap:"):
                        print(f"⚠️ Account {account.email} not configured for IMAP access")
                        continue
                    
                    app_password = account.access_token[5:]  # Remove "imap:" prefix
                    
                    # Create IMAP provider for this account
                    from ..providers.gmail_imap import GmailIMAPProvider
                    from datetime import datetime, timedelta
                    
                    imap_provider = GmailIMAPProvider(
                        email_address=account.email,
                        app_password=app_password
                    )
                    
                    # Use Gmail format that works: after:YYYY/MM/DD (from logs showing success)
                    from datetime import datetime, timedelta
                    today = datetime.utcnow()
                    start_date = today - timedelta(days=days)
                    
                    # Use proven Gmail format: after:YYYY/MM/DD (logs show this finds messages)
                    query = f"after:{start_date.strftime('%Y/%m/%d')}"
                    print(f"🔵 Searching {account.email} with Gmail query: {query}")
                    print(f"🔵 Date range: after {start_date.strftime('%Y/%m/%d')} (last {days} days)")
                    
                    messages = await imap_provider.search(query)
                    
                    # Limit and sort by date (most recent first)
                    messages = sorted(messages, key=lambda x: x.date, reverse=True)[:limit_per_account]
                    print(f"🔵 Found {len(messages)} messages from {account.email}")
                    
                    # Convert to dict for JSON response
                    for msg in messages:
                        all_messages.append({
                            "gmail_id": msg.gmail_id,
                            "thread_id": msg.thread_id,
                            "date": msg.date.isoformat(),
                            "from_email": msg.from_email,
                            "subject": msg.subject,
                            "snippet": msg.snippet,
                            "account_email": account.email
                        })
                    
                except Exception as e:
                    # Continue with other accounts if one fails
                    print(f"Failed to fetch messages from {account.email}: {e}")
                    continue
            
            # Sort all messages by date (most recent first)
            all_messages = sorted(all_messages, key=lambda x: x["date"], reverse=True)
            
            return {
                "total_accounts": len(accounts),
                "total_messages": len(all_messages),
                "messages": all_messages
            }
            
        finally:
            session.close()
        
    except Exception as e:
        import traceback
        error_details = f"Failed to fetch all messages: {str(e)}"
        full_traceback = traceback.format_exc()
        print(f"❌ Full error in get_all_recent_messages: {error_details}")
        print(f"❌ Traceback: {full_traceback}")
        raise HTTPException(status_code=500, detail=error_details)


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


@router.get("/accounts/{account_id}/recent-messages")
async def get_recent_messages(account_id: str, days: int = 1, limit: int = 20):
    """Get recent messages from a specific account."""
    try:
        from datetime import datetime, timedelta
        from ..providers.gmail_imap import GmailIMAPProvider
        from ..models.simple_db import get_session, GmailAccount
        
        # Get account credentials
        session = get_session()
        try:
            account = session.query(GmailAccount).filter_by(account_id=account_id).first()
            if not account or account.status != "connected":
                raise HTTPException(status_code=404, detail="Account not found or not connected")
            
            # Extract app password from stored token
            if not account.access_token or not account.access_token.startswith("imap:"):
                raise HTTPException(status_code=400, detail="Account not configured for IMAP access")
            
            app_password = account.access_token[5:]  # Remove "imap:" prefix
            
            # Create IMAP provider for this account
            imap_provider = GmailIMAPProvider(
                email_address=account.email,
                app_password=app_password
            )
            
            # Search for messages from recent days
            today = datetime.utcnow().date()
            start_date = today - timedelta(days=days-1)
            
            # Gmail IMAP search for recent messages (since includes the date itself)
            query = f"since:{start_date.strftime('%Y-%m-%d')}"
            
            messages = await imap_provider.search(query)
            
            # Limit and sort by date (most recent first)
            messages = sorted(messages, key=lambda x: x.date, reverse=True)[:limit]
            
            # Convert to dict for JSON response
            result = []
            for msg in messages:
                result.append({
                    "gmail_id": msg.gmail_id,
                    "thread_id": msg.thread_id,
                    "date": msg.date.isoformat(),
                    "from_email": msg.from_email,
                    "subject": msg.subject,
                    "snippet": msg.snippet,
                    "account_email": account.email
                })
            
            return {
                "account_id": account_id,
                "account_email": account.email, 
                "messages_count": len(result),
                "messages": result
            }
            
        finally:
            session.close()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch messages: {str(e)}")


@router.get("/auth/status")
async def auth_status():
    """Check OAuth configuration status."""
    return {
        "oauth_configured": bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET),
        "client_id_set": bool(GOOGLE_CLIENT_ID),
        "client_secret_set": bool(GOOGLE_CLIENT_SECRET),
        "redirect_uri": REDIRECT_URI
    }


@router.get("/debug/show-messages/{account_id}")
async def show_messages_debug(account_id: str):
    """Debug endpoint to show actual message data without processing delays."""
    try:
        from ..models.simple_db import get_session, GmailAccount
        from ..providers.gmail_imap import GmailIMAPProvider
        from datetime import datetime, timedelta
        
        session = get_session()
        try:
            account = session.query(GmailAccount).filter_by(account_id=account_id).first()
            if not account or not account.access_token or not account.access_token.startswith("imap:"):
                return {"error": f"Account {account_id} not found or not configured for IMAP"}
            
            app_password = account.access_token[5:]  # Remove "imap:" prefix
            
            imap_provider = GmailIMAPProvider(
                email_address=account.email,
                app_password=app_password
            )
            
            # Simple search for last 7 days to ensure we get results
            today = datetime.utcnow()
            week_ago = today - timedelta(days=7)
            query = f"after:{week_ago.strftime('%Y/%m/%d')}"
            
            print(f"🔍 DEBUG: Searching {account.email} with {query}")
            messages = await imap_provider.search(query)
            print(f"🔍 DEBUG: Raw messages found: {len(messages)}")
            
            # Convert first few messages to simple dict format
            result_messages = []
            for i, msg in enumerate(messages[:3]):  # Just first 3 messages
                try:
                    result_messages.append({
                        "index": i + 1,
                        "gmail_id": msg.gmail_id,
                        "thread_id": msg.thread_id, 
                        "from_email": msg.from_email,
                        "subject": msg.subject[:100] if msg.subject else "(No subject)",
                        "snippet": msg.snippet[:200] if msg.snippet else "",
                        "date": msg.date.isoformat() if hasattr(msg.date, 'isoformat') else str(msg.date),
                        "account_email": account.email
                    })
                except Exception as e:
                    result_messages.append({
                        "index": i + 1,
                        "error": f"Failed to process message: {str(e)}",
                        "raw_msg_type": str(type(msg))
                    })
            
            return {
                "success": True,
                "account": account.email,
                "query_used": query,
                "total_found": len(messages),
                "messages_shown": len(result_messages),
                "messages": result_messages
            }
            
        finally:
            session.close()
            
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
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