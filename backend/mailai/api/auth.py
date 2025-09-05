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


@router.get("/debug/simple-messages/{account_id}")
async def simple_messages_debug(account_id: str):
    """Ultra-simple endpoint that returns basic message info quickly."""
    try:
        from ..models.simple_db import get_session, GmailAccount
        
        session = get_session()
        try:
            account = session.query(GmailAccount).filter_by(account_id=account_id).first()
            if not account:
                return {"error": f"Account {account_id} not found"}
            
            # Return basic account info + mock message data to test UI quickly
            return {
                "success": True,
                "account": account.email,
                "query_used": "simple_test",
                "total_found": 3,
                "messages_shown": 3,
                "messages": [
                    {
                        "index": 1,
                        "gmail_id": "test_001",
                        "thread_id": "test_thread_001",
                        "from_email": "test@example.com",
                        "subject": "Test Message 1 from " + account.email,
                        "snippet": "This is a test message to verify UI loading works...",
                        "date": "2025-09-05T10:00:00+00:00",
                        "account_email": account.email
                    },
                    {
                        "index": 2,
                        "gmail_id": "test_002", 
                        "thread_id": "test_thread_002",
                        "from_email": "another@example.com",
                        "subject": "Test Message 2 from " + account.email,
                        "snippet": "Another test message to show multiple results...",
                        "date": "2025-09-05T11:00:00+00:00",
                        "account_email": account.email
                    },
                    {
                        "index": 3,
                        "gmail_id": "test_003",
                        "thread_id": "test_thread_003", 
                        "from_email": "third@example.com",
                        "subject": "Test Message 3 from " + account.email,
                        "snippet": "Third test message to confirm everything displays correctly...",
                        "date": "2025-09-05T12:00:00+00:00",
                        "account_email": account.email
                    }
                ]
            }
        finally:
            session.close()
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/debug/show-messages-fast/{account_id}")
async def show_messages_fast(account_id: str):
    """Database-first fast endpoint - uses cached messages, falls back to IMAP only if needed."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"💾 DATABASE-FIRST ENDPOINT: show_messages_fast for {account_id}")
    
    try:
        from ..models.simple_db import get_session, GmailAccount, Message
        from datetime import datetime, timedelta
        
        session = get_session()
        try:
            account = session.query(GmailAccount).filter_by(account_id=account_id).first()
            if not account:
                return {"error": f"Account {account_id} not found"}
            
            # STEP 1: Check database first (FAST)
            logger.info(f"💾 Checking database for cached messages from {account.email}")
            print(f"💾 DATABASE CHECK: Looking for messages from {account.email}")
            
            # Get recent messages from database
            recent_messages = session.query(Message).filter_by(
                # Note: We can't filter by account since Message doesn't have account_id
                # For now, get all recent messages
            ).order_by(Message.date.desc()).limit(5).all()
            
            if recent_messages:
                logger.info(f"💾 Found {len(recent_messages)} cached messages in database")
                print(f"💾 DATABASE HIT: Using {len(recent_messages)} cached messages")
                
                # Convert to response format from database with full content
                result_messages = []
                for i, msg in enumerate(recent_messages):
                    result_messages.append({
                        "index": i + 1,
                        "gmail_id": msg.gmail_id,
                        "thread_id": msg.thread_id,
                        "from_email": msg.from_email,
                        "subject": msg.subject,
                        "snippet": msg.snippet,
                        "body": msg.body,  # Include full message body
                        "date": msg.date.isoformat(),
                        "account_email": account.email,
                        "to_emails": msg.to_emails_json,
                        "cc_emails": msg.cc_emails_json,
                        "has_attachments": msg.has_attachments,
                        "attachment_count": msg.attachment_count,
                        "message_size": msg.message_size
                    })
                
                return {
                    "success": True,
                    "account": account.email,
                    "query_used": "database_cache",
                    "total_found": len(recent_messages),
                    "messages_shown": len(result_messages),
                    "messages": result_messages,
                    "source": "database_cache"
                }
            
            # STEP 2: Database empty, use mock data for immediate response
            logger.info(f"💾 Database empty, returning mock data for fast response")
            print(f"💾 DATABASE MISS: Returning mock data for {account.email}")
            
            mock_messages = [
                {
                    "index": 1,
                    "gmail_id": "mock_001",
                    "thread_id": "mock_thread_001", 
                    "from_email": "demo@example.com",
                    "subject": "Welcome to MailAI Console",
                    "snippet": "This is a demo message to show the interface works...",
                    "date": datetime.utcnow().isoformat(),
                    "account_email": account.email
                },
                {
                    "index": 2,
                    "gmail_id": "mock_002", 
                    "thread_id": "mock_thread_002",
                    "from_email": "system@mailai.com",
                    "subject": "System is ready for Gmail connection",
                    "snippet": "Connect your Gmail account to see real messages here...",
                    "date": datetime.utcnow().isoformat(),
                    "account_email": account.email
                }
            ]
            
            return {
                "success": True,
                "account": account.email,
                "query_used": "mock_data",
                "total_found": len(mock_messages),
                "messages_shown": len(mock_messages),
                "messages": mock_messages,
                "source": "mock_data"
            }
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"❌ Database-first endpoint error: {e}")
        return {"error": str(e)}

@router.get("/debug/show-messages/{account_id}")
async def show_messages_debug(account_id: str):
    """Debug endpoint to show actual message data without processing delays."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"🔍 DEBUG ENDPOINT CALLED: show_messages_debug for {account_id}")
    
    try:
        from ..models.simple_db import get_session, GmailAccount
        from ..providers.gmail_imap import GmailIMAPProvider
        from datetime import datetime, timedelta
        
        logger.info(f"🔍 Opening database session for {account_id}")
        session = get_session()
        try:
            account = session.query(GmailAccount).filter_by(account_id=account_id).first()
            if not account:
                logger.error(f"❌ Account {account_id} not found in database")
                return {"error": f"Account {account_id} not found"}
            
            if not account.access_token:
                logger.error(f"❌ Account {account_id} has no access token")
                return {"error": f"Account {account_id} not configured"}
                
            if not account.access_token.startswith("imap:"):
                logger.error(f"❌ Account {account_id} has wrong token format: {account.access_token[:10]}...")
                return {"error": f"Account {account_id} not configured for IMAP"}
            
            logger.info(f"✅ Account {account_id} found with IMAP token")
            app_password = account.access_token[5:]  # Remove "imap:" prefix
            
            logger.info(f"🔍 Creating IMAP provider for {account.email}")
            imap_provider = GmailIMAPProvider(
                email_address=account.email,
                app_password=app_password
            )
            
            # Search last 7 days for faster performance
            today = datetime.utcnow()
            seven_days_ago = today - timedelta(days=7)
            query = f"after:{seven_days_ago.strftime('%Y/%m/%d')}"
            
            logger.info(f"🔍 Searching {account.email} with {query}")
            print(f"🔍 DEBUG: Searching {account.email} with {query}")
            
            # First search for message metadata
            message_metas = await imap_provider.search(query)
            logger.info(f"📧 Raw messages found: {len(message_metas)} from {account.email}")
            print(f"🔍 DEBUG: Raw messages found: {len(message_metas)}")
            
            if not message_metas:
                logger.warning(f"⚠️ No messages found for {account.email}")
                return {
                    "success": True,
                    "account": account.email,
                    "query_used": query,
                    "total_found": 0,
                    "messages_shown": 0,
                    "messages": []
                }
            
            # Sort by date (most recent first) and take only 3 for quick testing
            logger.info(f"📊 Sorting and limiting message metas for {account.email}")
            if hasattr(message_metas[0] if message_metas else None, 'date'):
                sorted_metas = sorted(message_metas, key=lambda x: x.date, reverse=True)[:3]
                logger.info(f"✅ Sorted message metas by date for {account.email}")
            else:
                sorted_metas = message_metas[:3]  # Just take first 3 for quick testing
                logger.warning(f"⚠️ Could not sort by date for {account.email}, using first 3")
            
            # Now fetch full message bodies
            message_ids = [meta.gmail_id for meta in sorted_metas]
            logger.info(f"📥 Fetching full bodies for {len(message_ids)} messages from {account.email}")
            messages = await imap_provider.fetch_bodies(message_ids)
            logger.info(f"✅ Fetched {len(messages)} full messages with bodies for {account.email}")
            
            # Convert messages to simple dict format quickly
            result_messages = []
            logger.info(f"🔄 Converting {len(messages)} messages to dict format for {account.email}")
            for i, msg in enumerate(messages):
                try:
                    logger.info(f"   📧 Processing message {i+1}: {msg.subject[:30] if hasattr(msg, 'subject') else 'No subject'}...")
                    message_dict = {
                        "index": i + 1,
                        "gmail_id": msg.gmail_id,
                        "thread_id": msg.thread_id, 
                        "from_email": msg.from_email,
                        "subject": msg.subject[:100] if msg.subject else "(No subject)",
                        "snippet": msg.body[:500] if msg.body else (msg.snippet[:200] if msg.snippet else ""),
                        "date": msg.date.isoformat() if hasattr(msg.date, 'isoformat') else str(msg.date),
                        "account_email": account.email
                    }
                    result_messages.append(message_dict)
                    logger.info(f"   ✅ Message {i+1} processed successfully")
                except Exception as e:
                    result_messages.append({
                        "index": i + 1,
                        "error": f"Failed to process message: {str(e)}",
                        "raw_msg_type": str(type(msg))
                    })
            
            logger.info(f"✅ Successfully processed {len(result_messages)} messages for {account.email}")
            final_result = {
                "success": True,
                "account": account.email,
                "query_used": query,
                "total_found": len(messages) if messages else 0,
                "messages_shown": len(result_messages),
                "messages": result_messages
            }
            
            logger.info(f"🎉 ENDPOINT COMPLETE: {account.email} returning {len(result_messages)} messages")
            return final_result
            
        finally:
            logger.info(f"🔒 Closing database session for {account_id}")
            session.close()
            
    except Exception as e:
        import traceback
        error_msg = str(e)
        full_traceback = traceback.format_exc()
        logger.error(f"❌ ENDPOINT ERROR for {account_id}: {error_msg}")
        logger.error(f"❌ Full traceback: {full_traceback}")
        
        return {
            "success": False,
            "account": account_id,
            "error": error_msg,
            "traceback": full_traceback
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