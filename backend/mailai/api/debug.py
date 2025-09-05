"""Debug endpoints for testing IMAP functionality."""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..providers.gmail_imap import GmailIMAPProvider
from ..models.simple_db import get_session, GmailAccount

logger = logging.getLogger(__name__)
router = APIRouter()


class TestIMAPRequest(BaseModel):
    email: str
    app_password: str
    query: str = "from:no-reply"  # Simple test query
    limit: int = 5


class TestIMAPResponse(BaseModel):
    success: bool
    email: str
    messages_found: int
    messages: List[Dict[str, Any]] = []
    error: str = ""


@router.post("/debug/test-imap", response_model=TestIMAPResponse)
async def test_imap_directly(request: TestIMAPRequest):
    """Test IMAP connection directly with credentials."""
    logger.info(f"🔵 Testing IMAP for {request.email}")
    
    try:
        # Create IMAP provider
        imap_provider = GmailIMAPProvider(
            email_address=request.email,
            app_password=request.app_password
        )
        
        logger.info(f"🔵 Created IMAP provider, testing connection...")
        
        # Test authentication
        auth_result = await imap_provider.authenticate()
        if not auth_result:
            logger.error(f"❌ Authentication failed for {request.email}")
            return TestIMAPResponse(
                success=False,
                email=request.email,
                messages_found=0,
                error="Authentication failed - check email and app password"
            )
        
        logger.info(f"✅ Authentication successful for {request.email}")
        
        # Search for messages
        logger.info(f"🔍 Searching for messages with query: {request.query}")
        messages = await imap_provider.search(request.query)
        
        logger.info(f"✅ Found {len(messages)} messages")
        
        # Convert to dict for response
        message_list = []
        for msg in messages[:request.limit]:
            message_list.append({
                "gmail_id": msg.gmail_id,
                "date": msg.date.isoformat(),
                "from_email": msg.from_email,
                "subject": msg.subject,
                "snippet": msg.snippet[:100] + "..." if len(msg.snippet) > 100 else msg.snippet
            })
        
        return TestIMAPResponse(
            success=True,
            email=request.email,
            messages_found=len(messages),
            messages=message_list
        )
        
    except Exception as e:
        logger.error(f"❌ IMAP test failed for {request.email}: {e}")
        logger.exception("Full IMAP test error:")
        
        return TestIMAPResponse(
            success=False,
            email=request.email,
            messages_found=0,
            error=str(e)
        )


@router.get("/debug/account-tokens")
async def debug_account_tokens():
    """Debug endpoint to check account token storage."""
    session = get_session()
    try:
        accounts = session.query(GmailAccount).all()
        
        result = []
        for account in accounts:
            result.append({
                "email": account.email,
                "status": account.status,
                "has_access_token": bool(account.access_token),
                "token_preview": account.access_token[:20] + "..." if account.access_token else None,
                "token_format": "imap" if account.access_token and account.access_token.startswith("imap:") else "other"
            })
        
        return {
            "accounts": result,
            "total": len(result)
        }
        
    finally:
        session.close()


@router.post("/debug/fetch-and-store")
async def fetch_and_store_messages(days: int = 1, limit_per_account: int = 10):
    """Fetch messages from all accounts and store them in database."""
    logger.info(f"🔵 Starting fetch and store for last {days} days, {limit_per_account} per account")
    
    session = get_session()
    try:
        accounts = session.query(GmailAccount).filter_by(status="connected").all()
        logger.info(f"🔵 Found {len(accounts)} connected accounts")
        
        total_fetched = 0
        account_results = []
        
        for account in accounts:
            logger.info(f"🔵 Processing account: {account.email}")
            
            try:
                # Check token format
                if not account.access_token or not account.access_token.startswith("imap:"):
                    logger.warning(f"⚠️ Account {account.email} has old token format, skipping")
                    account_results.append({
                        "email": account.email,
                        "status": "skipped",
                        "error": "Old token format - needs reconnection",
                        "messages_fetched": 0
                    })
                    continue
                
                # Extract app password
                app_password = account.access_token[5:]
                
                # Create IMAP provider
                imap_provider = GmailIMAPProvider(
                    email_address=account.email,
                    app_password=app_password
                )
                
                # Search for recent messages
                today = datetime.utcnow().date()
                start_date = today - timedelta(days=days-1)
                query = f"after:{start_date.strftime('%Y/%m/%d')}"
                
                logger.info(f"🔍 Searching with query: {query}")
                messages = await imap_provider.search(query)
                
                # Limit messages
                messages = messages[:limit_per_account]
                
                logger.info(f"✅ Found {len(messages)} messages for {account.email}")
                
                # TODO: Store messages in database (will implement this next)
                # For now, just count them
                total_fetched += len(messages)
                
                account_results.append({
                    "email": account.email,
                    "status": "success",
                    "messages_fetched": len(messages),
                    "sample_subjects": [msg.subject[:50] + "..." if len(msg.subject) > 50 else msg.subject for msg in messages[:3]]
                })
                
            except Exception as e:
                logger.error(f"❌ Failed to fetch messages for {account.email}: {e}")
                account_results.append({
                    "email": account.email,
                    "status": "error",
                    "error": str(e),
                    "messages_fetched": 0
                })
        
        return {
            "success": True,
            "total_accounts_processed": len(accounts),
            "total_messages_fetched": total_fetched,
            "results": account_results
        }
        
    except Exception as e:
        logger.error(f"❌ Fetch and store failed: {e}")
        logger.exception("Full fetch and store error:")
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        session.close()


@router.post("/debug/update-account-credentials")
async def update_account_credentials(email: str, app_password: str):
    """Update account credentials to new IMAP format."""
    logger.info(f"🔵 Updating credentials for {email}")
    
    session = get_session()
    try:
        account = session.query(GmailAccount).filter_by(email=email).first()
        if not account:
            return {
                "success": False,
                "error": f"Account {email} not found"
            }
        
        # Test the new credentials first
        imap_provider = GmailIMAPProvider(
            email_address=email,
            app_password=app_password
        )
        
        if not await imap_provider.authenticate():
            return {
                "success": False,
                "error": "App password authentication failed"
            }
        
        # Update the account with new format
        old_token = account.access_token
        account.access_token = f"imap:{app_password}"
        account.status = "connected"
        account.connected_at = datetime.utcnow()
        session.commit()
        
        logger.info(f"✅ Updated {email} credentials from '{old_token[:20]}...' to 'imap:{app_password[:3]}...'")
        
        return {
            "success": True,
            "email": email,
            "message": f"Successfully updated credentials for {email}",
            "old_format": old_token[:20] + "...",
            "new_format": f"imap:{app_password[:3]}..."
        }
        
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Failed to update credentials for {email}: {e}")
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        session.close()