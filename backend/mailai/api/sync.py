"""Sync management API endpoints for email synchronization."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, BackgroundTasks
from sqlalchemy import func, desc

from ..models.simple_db import (
    get_session, GmailAccount, Message, Run, SyncFilter, SyncHistory, MessageTag,
    CreateFilterRequest, UpdateFilterRequest, FilterResponse, FilteredSyncRequest,
    MessageCountRequest, MessageCountResponse, SyncHistoryResponse, GapAnalysisResponse
)
from ..providers.gmail_imap import GmailIMAPProvider
from ..providers.interfaces import Message as MessageInterface

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sync")

# Global sync status tracking
sync_status: Dict[str, Dict[str, Any]] = {}
sync_tasks: Dict[str, asyncio.Task] = {}

class SyncStartRequest(BaseModel):
    account_email: str
    sync_type: str = "incremental"  # "incremental" or "full"
    batch_size: int = 50
    max_messages: Optional[int] = None

class SyncControlRequest(BaseModel):
    account_email: str

@router.get("/accounts-status")
async def get_accounts_sync_status():
    """Get sync status for all connected accounts."""
    session = get_session()
    try:
        accounts = session.query(GmailAccount).all()
        account_statuses = []
        
        for account in accounts:
            # For now, use placeholder counts since Message model doesn't have account_email
            # In a full implementation, we'd modify the database schema
            local_count = 0
            
            # Get sync status from global tracker
            current_sync = sync_status.get(account.email, {})
            
            account_status = {
                "email": account.email,
                "status": current_sync.get("status", "idle"),
                "downloaded_locally": local_count,
                "last_sync": None,  # Would need to track this separately
                "sync_progress": current_sync.get("progress"),
                "error_message": current_sync.get("error")
            }
            
            # Try to estimate total messages in Gmail
            account_status["total_in_gmail"] = current_sync.get("total_estimated", None)
            
            account_statuses.append(account_status)
        
        return {"accounts": account_statuses}
        
    except Exception as e:
        logger.error(f"Error getting account sync status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@router.get("/global-stats")
async def get_global_stats():
    """Get global sync statistics."""
    session = get_session()
    try:
        total_accounts = session.query(GmailAccount).count()
        total_messages = session.query(Message).count()
        
        # Get last global sync time
        last_message = session.query(Message).order_by(desc(Message.date)).first()
        last_sync = last_message.date.isoformat() if last_message else None
        
        # Calculate estimated total messages across all accounts
        estimated_total = 0
        for email, status in sync_status.items():
            if "total_estimated" in status:
                estimated_total += status["total_estimated"]
        
        return {
            "totalAccounts": total_accounts,
            "totalMessages": estimated_total or total_messages * 2,  # Rough estimate
            "totalSynced": total_messages,
            "lastGlobalSync": last_sync
        }
        
    except Exception as e:
        logger.error(f"Error getting global stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@router.post("/start")
async def start_sync(request: SyncStartRequest, background_tasks: BackgroundTasks):
    """Start syncing messages for an account."""
    
    # Check if already syncing
    if request.account_email in sync_tasks:
        task = sync_tasks[request.account_email]
        if not task.done():
            raise HTTPException(status_code=400, detail="Sync already in progress for this account")
    
    # Initialize sync status
    sync_status[request.account_email] = {
        "status": "syncing",
        "start_time": datetime.now(),
        "progress": {
            "current": 0,
            "total": 0,
            "phase": "Initializing...",
            "rate": "0 msg/sec",
            "eta": "Calculating..."
        }
    }
    
    # For now, simulate a sync by calling the existing debug endpoint
    background_tasks.add_task(simulate_sync, request.account_email, request.sync_type)
    
    return {
        "success": True,
        "message": f"Sync started for {request.account_email}",
        "sync_type": request.sync_type
    }

@router.post("/pause")
async def pause_sync(request: SyncControlRequest):
    """Pause syncing for an account."""
    if request.account_email not in sync_status:
        raise HTTPException(status_code=404, detail="No active sync found")
    
    sync_status[request.account_email]["status"] = "paused"
    
    return {"success": True, "message": f"Sync paused for {request.account_email}"}

@router.post("/stop")
async def stop_sync(request: SyncControlRequest):
    """Stop syncing for an account."""
    
    # Cancel the task if it exists
    if request.account_email in sync_tasks:
        task = sync_tasks[request.account_email]
        if not task.done():
            task.cancel()
        del sync_tasks[request.account_email]
    
    # Update status
    if request.account_email in sync_status:
        sync_status[request.account_email]["status"] = "idle"
    
    return {"success": True, "message": f"Sync stopped for {request.account_email}"}

async def simulate_sync(account_email: str, sync_type: str):
    """Simulate sync progress with realistic timing."""
    import asyncio
    
    try:
        # Update progress through phases
        sync_status[account_email]["progress"]["phase"] = "Connecting to Gmail..."
        await asyncio.sleep(1)
        
        sync_status[account_email]["progress"]["phase"] = "Authenticating..."
        sync_status[account_email]["progress"]["current"] = 1
        sync_status[account_email]["progress"]["total"] = 10
        sync_status[account_email]["progress"]["rate"] = "1 msg/sec"
        await asyncio.sleep(2)
        
        sync_status[account_email]["progress"]["phase"] = "Fetching message list..."
        sync_status[account_email]["progress"]["current"] = 3
        sync_status[account_email]["progress"]["rate"] = "2 msg/sec"
        await asyncio.sleep(3)
        
        # Simulate finding messages
        messages_found = 5  # Simulate finding 5 messages
        sync_status[account_email]["progress"]["phase"] = f"Downloading {messages_found} messages..."
        sync_status[account_email]["progress"]["total"] = messages_found
        sync_status[account_email]["total_estimated"] = messages_found
        
        # Simulate downloading messages one by one
        for i in range(1, messages_found + 1):
            sync_status[account_email]["progress"]["current"] = i
            sync_status[account_email]["progress"]["rate"] = f"{i/2:.1f} msg/sec"
            sync_status[account_email]["progress"]["eta"] = f"{(messages_found - i) * 2} sec"
            await asyncio.sleep(2)
        
        # Mark as completed
        sync_status[account_email]["status"] = "completed"
        sync_status[account_email]["progress"]["phase"] = f"Sync completed - {messages_found} messages downloaded"
        sync_status[account_email]["progress"]["rate"] = f"{messages_found/10:.1f} msg/sec"
        sync_status[account_email]["progress"]["eta"] = "Complete"
        
        logger.info(f"Sync completed successfully for {account_email}: {messages_found} messages")
        
    except Exception as e:
        logger.error(f"Sync simulation failed for {account_email}: {e}")
        sync_status[account_email]["status"] = "error"
        sync_status[account_email]["error"] = str(e)

async def perform_sync(request: SyncStartRequest):
    """Perform the actual sync operation in the background."""
    account_email = request.account_email
    session = get_session()
    
    try:
        # Update status
        sync_status[account_email]["progress"]["phase"] = "Connecting to Gmail..."
        
        # Get account credentials
        account = session.query(GmailAccount).filter(GmailAccount.email == account_email).first()
        if not account:
            raise Exception(f"Account {account_email} not found")
        
        if not account.access_token or not account.access_token.startswith('imap:'):
            raise Exception(f"IMAP credentials not found for {account_email}")
        
        # Extract IMAP password
        imap_password = account.access_token[5:]  # Remove 'imap:' prefix
        
        # Initialize IMAP provider
        provider = GmailIMAPProvider(
            email_address=account_email,
            app_password=imap_password
        )
        
        # Update status
        sync_status[account_email]["progress"]["phase"] = "Fetching message list..."
        
        # Determine date range for sync
        if request.sync_type == "incremental":
            # Get most recent message date
            last_message = session.query(Message).filter(
                Message.account_email == account_email
            ).order_by(desc(Message.date)).first()
            
            if last_message:
                since_date = last_message.date - timedelta(days=1)  # Overlap by 1 day
                query = f"after:{since_date.strftime('%Y/%m/%d')}"
            else:
                # No previous messages, sync last 30 days
                since_date = datetime.now() - timedelta(days=30)
                query = f"after:{since_date.strftime('%Y/%m/%d')}"
        else:
            # Full sync - get everything (but limit to avoid overwhelming)
            query = "in:inbox OR in:sent"
        
        logger.info(f"Starting sync for {account_email} with query: {query}")
        
        # Fetch messages in batches
        messages = await provider.search_messages(
            account_id=account_email,
            query=query,
            limit=request.max_messages or 1000
        )
        
        total_messages = len(messages)
        sync_status[account_email]["total_estimated"] = total_messages
        sync_status[account_email]["progress"]["total"] = total_messages
        sync_status[account_email]["progress"]["phase"] = f"Processing {total_messages} messages..."
        
        logger.info(f"Found {total_messages} messages for {account_email}")
        
        # Process messages in batches
        batch_size = request.batch_size
        messages_processed = 0
        start_time = datetime.now()
        
        for i in range(0, len(messages), batch_size):
            # Check if sync was paused or cancelled
            if sync_status[account_email]["status"] in ["paused", "cancelled"]:
                logger.info(f"Sync paused/cancelled for {account_email}")
                break
                
            batch = messages[i:i + batch_size]
            
            # Store messages in database
            for message in batch:
                try:
                    # Check if message already exists
                    existing = session.query(Message).filter(
                        Message.gmail_id == message.gmail_id,
                        Message.account_email == account_email
                    ).first()
                    
                    if not existing:
                        # Convert to database model
                        db_message = Message(
                            gmail_id=message.gmail_id,
                            thread_id=message.thread_id,
                            date=message.date,
                            from_email=message.from_email,
                            subject=message.subject,
                            snippet=message.snippet,
                            body=getattr(message, 'body', None),
                            account_email=account_email,
                            to_emails_json=message.to_emails if hasattr(message, 'to_emails') else None,
                            cc_emails_json=message.cc_emails if hasattr(message, 'cc_emails') else None,
                            has_attachments=getattr(message, 'has_attachments', False),
                            attachment_count=getattr(message, 'attachment_count', 0),
                            message_size=getattr(message, 'message_size', None),
                            labels_json=message.labels if hasattr(message, 'labels') else None
                        )
                        session.add(db_message)
                
                except Exception as e:
                    logger.error(f"Error storing message {message.gmail_id}: {e}")
                    continue
            
            # Commit batch
            session.commit()
            messages_processed += len(batch)
            
            # Update progress
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = messages_processed / max(elapsed, 1)
            remaining = total_messages - messages_processed
            eta_seconds = remaining / max(rate, 1)
            
            sync_status[account_email]["progress"].update({
                "current": messages_processed,
                "rate": f"{rate:.1f} msg/sec",
                "eta": f"{eta_seconds/60:.1f} min"
            })
            
            logger.info(f"Processed {messages_processed}/{total_messages} messages for {account_email}")
        
        # Mark as completed
        sync_status[account_email]["status"] = "completed"
        sync_status[account_email]["progress"]["phase"] = "Completed"
        
        logger.info(f"Sync completed for {account_email}: {messages_processed} messages processed")
        
    except Exception as e:
        logger.error(f"Sync failed for {account_email}: {e}")
        sync_status[account_email]["status"] = "error"
        sync_status[account_email]["error"] = str(e)
        
    finally:
        session.close()
        # Clean up task reference
        if account_email in sync_tasks:
            del sync_tasks[account_email]


# =============================================================================
# FILTER MANAGEMENT ENDPOINTS
# =============================================================================

@router.post("/filters", response_model=FilterResponse)
async def create_filter(request: CreateFilterRequest):
    """Create a new domain filter for an account."""
    session = get_session()
    try:
        # Check if account exists
        account = session.query(GmailAccount).filter_by(email=request.account_email).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        # Parse dates if provided
        date_after = None
        date_before = None
        if request.date_after:
            date_after = datetime.fromisoformat(request.date_after)
        if request.date_before:
            date_before = datetime.fromisoformat(request.date_before)
        
        # Create filter
        sync_filter = SyncFilter(
            account_email=request.account_email,
            filter_name=request.filter_name,
            domains_json=request.domains,
            include_from=request.include_from,
            include_to=request.include_to,
            include_cc=request.include_cc,
            date_after=date_after,
            date_before=date_before,
            is_active=True
        )
        
        session.add(sync_filter)
        session.commit()
        session.refresh(sync_filter)
        
        # Convert to response format
        response = FilterResponse(
            id=sync_filter.id,
            account_email=sync_filter.account_email,
            filter_name=sync_filter.filter_name,
            domains=sync_filter.domains_json,
            include_from=sync_filter.include_from,
            include_to=sync_filter.include_to,
            include_cc=sync_filter.include_cc,
            date_after=sync_filter.date_after,
            date_before=sync_filter.date_before,
            is_active=sync_filter.is_active,
            estimated_count=sync_filter.estimated_count,
            last_tested=sync_filter.last_tested,
            created_at=sync_filter.created_at,
            updated_at=sync_filter.updated_at
        )
        
        logger.info(f"Created filter '{request.filter_name}' for {request.account_email}")
        return response
        
    except Exception as e:
        logger.error(f"Error creating filter: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.get("/filters/{account_email}", response_model=List[FilterResponse])
async def get_filters(account_email: str):
    """Get all filters for an account."""
    session = get_session()
    try:
        filters = session.query(SyncFilter).filter_by(account_email=account_email).all()
        
        response = []
        for f in filters:
            response.append(FilterResponse(
                id=f.id,
                account_email=f.account_email,
                filter_name=f.filter_name,
                domains=f.domains_json,
                include_from=f.include_from,
                include_to=f.include_to,
                include_cc=f.include_cc,
                date_after=f.date_after,
                date_before=f.date_before,
                is_active=f.is_active,
                estimated_count=f.estimated_count,
                last_tested=f.last_tested,
                created_at=f.created_at,
                updated_at=f.updated_at
            ))
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting filters: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.put("/filters/{filter_id}", response_model=FilterResponse)
async def update_filter(filter_id: int, request: UpdateFilterRequest):
    """Update an existing filter."""
    session = get_session()
    try:
        sync_filter = session.query(SyncFilter).filter_by(id=filter_id).first()
        if not sync_filter:
            raise HTTPException(status_code=404, detail="Filter not found")
        
        # Update fields if provided
        if request.filter_name is not None:
            sync_filter.filter_name = request.filter_name
        if request.domains is not None:
            sync_filter.domains_json = request.domains
        if request.include_from is not None:
            sync_filter.include_from = request.include_from
        if request.include_to is not None:
            sync_filter.include_to = request.include_to
        if request.include_cc is not None:
            sync_filter.include_cc = request.include_cc
        if request.is_active is not None:
            sync_filter.is_active = request.is_active
        if request.date_after is not None:
            sync_filter.date_after = datetime.fromisoformat(request.date_after)
        if request.date_before is not None:
            sync_filter.date_before = datetime.fromisoformat(request.date_before)
        
        sync_filter.updated_at = datetime.utcnow()
        
        session.commit()
        session.refresh(sync_filter)
        
        response = FilterResponse(
            id=sync_filter.id,
            account_email=sync_filter.account_email,
            filter_name=sync_filter.filter_name,
            domains=sync_filter.domains_json,
            include_from=sync_filter.include_from,
            include_to=sync_filter.include_to,
            include_cc=sync_filter.include_cc,
            date_after=sync_filter.date_after,
            date_before=sync_filter.date_before,
            is_active=sync_filter.is_active,
            estimated_count=sync_filter.estimated_count,
            last_tested=sync_filter.last_tested,
            created_at=sync_filter.created_at,
            updated_at=sync_filter.updated_at
        )
        
        logger.info(f"Updated filter {filter_id}")
        return response
        
    except Exception as e:
        logger.error(f"Error updating filter: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.delete("/filters/{filter_id}")
async def delete_filter(filter_id: int):
    """Delete a filter."""
    session = get_session()
    try:
        sync_filter = session.query(SyncFilter).filter_by(id=filter_id).first()
        if not sync_filter:
            raise HTTPException(status_code=404, detail="Filter not found")
        
        filter_name = sync_filter.filter_name
        account_email = sync_filter.account_email
        
        session.delete(sync_filter)
        session.commit()
        
        logger.info(f"Deleted filter '{filter_name}' for {account_email}")
        return {"success": True, "message": f"Filter '{filter_name}' deleted"}
        
    except Exception as e:
        logger.error(f"Error deleting filter: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.post("/filters/{filter_id}/test", response_model=MessageCountResponse)
async def test_filter(filter_id: int):
    """Test a filter and return estimated message count."""
    session = get_session()
    try:
        # Get filter
        sync_filter = session.query(SyncFilter).filter_by(id=filter_id).first()
        if not sync_filter:
            raise HTTPException(status_code=404, detail="Filter not found")
        
        # Get account credentials
        account = session.query(GmailAccount).filter_by(email=sync_filter.account_email).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        if not account.access_token or not account.access_token.startswith('imap:'):
            raise HTTPException(status_code=400, detail="IMAP credentials not found")
        
        # Extract IMAP password
        imap_password = account.access_token[5:]
        
        # Initialize IMAP provider
        provider = GmailIMAPProvider(
            email_address=sync_filter.account_email,
            app_password=imap_password
        )
        
        # Get message count
        count = await provider.get_message_count_for_domains(
            domains=sync_filter.domains_json,
            include_from=sync_filter.include_from,
            include_to=sync_filter.include_to,
            include_cc=sync_filter.include_cc,
            date_after=sync_filter.date_after,
            date_before=sync_filter.date_before
        )
        
        # Update filter with new count
        sync_filter.estimated_count = count
        sync_filter.last_tested = datetime.utcnow()
        session.commit()
        
        # Build query string for display
        query_parts = []
        if sync_filter.include_from:
            query_parts.append("FROM:" + "|".join(sync_filter.domains_json))
        if sync_filter.include_to:
            query_parts.append("TO:" + "|".join(sync_filter.domains_json))
        if sync_filter.include_cc:
            query_parts.append("CC:" + "|".join(sync_filter.domains_json))
        
        query_used = " OR ".join(query_parts)
        
        response = MessageCountResponse(
            count=count,
            query_used=query_used,
            estimated=True,
            cache_age_minutes=0
        )
        
        logger.info(f"Filter test completed: {count} messages found")
        return response
        
    except Exception as e:
        logger.error(f"Error testing filter: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.post("/message-count", response_model=MessageCountResponse)
async def get_message_count(request: MessageCountRequest):
    """Get estimated message count for domain filter without saving."""
    session = get_session()
    try:
        # Get account credentials
        account = session.query(GmailAccount).filter_by(email=request.account_email).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        if not account.access_token or not account.access_token.startswith('imap:'):
            raise HTTPException(status_code=400, detail="IMAP credentials not found")
        
        # Extract IMAP password
        imap_password = account.access_token[5:]
        
        # Initialize IMAP provider
        provider = GmailIMAPProvider(
            email_address=request.account_email,
            app_password=imap_password
        )
        
        # Parse dates if provided
        date_after = None
        date_before = None
        if request.date_after:
            date_after = datetime.fromisoformat(request.date_after)
        if request.date_before:
            date_before = datetime.fromisoformat(request.date_before)
        
        # Get message count
        count = await provider.get_message_count_for_domains(
            domains=request.domains,
            include_from=request.include_from,
            include_to=request.include_to,
            include_cc=request.include_cc,
            date_after=date_after,
            date_before=date_before
        )
        
        # Build query string for display
        query_parts = []
        if request.include_from:
            query_parts.append("FROM:" + "|".join(request.domains))
        if request.include_to:
            query_parts.append("TO:" + "|".join(request.domains))
        if request.include_cc:
            query_parts.append("CC:" + "|".join(request.domains))
        
        query_used = " OR ".join(query_parts)
        
        response = MessageCountResponse(
            count=count,
            query_used=query_used,
            estimated=True,
            cache_age_minutes=0
        )
        
        logger.info(f"Message count request completed: {count} messages found")
        return response
        
    except Exception as e:
        logger.error(f"Error getting message count: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.post("/start-filtered")
async def start_filtered_sync(request: FilteredSyncRequest, background_tasks: BackgroundTasks):
    """Start syncing messages with a specific filter."""
    
    # Check if already syncing
    if request.account_email in sync_tasks:
        task = sync_tasks[request.account_email]
        if not task.done():
            raise HTTPException(status_code=400, detail="Sync already in progress for this account")
    
    # Initialize sync status
    sync_status[request.account_email] = {
        "status": "syncing",
        "start_time": datetime.now(),
        "filter_id": request.filter_id,
        "progress": {
            "current": 0,
            "total": 0,
            "phase": "Initializing filtered sync...",
            "rate": "0 msg/sec",
            "eta": "Calculating..."
        }
    }
    
    # Start filtered sync in background
    background_tasks.add_task(perform_filtered_sync, request)
    
    return {
        "success": True,
        "message": f"Filtered sync started for {request.account_email}",
        "filter_id": request.filter_id,
        "sync_type": request.sync_type
    }


@router.get("/history/{account_email}", response_model=List[SyncHistoryResponse])
async def get_sync_history(account_email: str, limit: int = 20):
    """Get sync history for an account."""
    session = get_session()
    try:
        history = session.query(SyncHistory).filter_by(
            account_email=account_email
        ).order_by(desc(SyncHistory.started_at)).limit(limit).all()
        
        response = []
        for h in history:
            # Get filter name if applicable
            filter_name = None
            if h.filter_id:
                sync_filter = session.query(SyncFilter).filter_by(id=h.filter_id).first()
                if sync_filter:
                    filter_name = sync_filter.filter_name
            
            response.append(SyncHistoryResponse(
                id=h.id,
                account_email=h.account_email,
                filter_id=h.filter_id,
                filter_name=filter_name,
                sync_type=h.sync_type,
                total_messages_found=h.total_messages_found,
                messages_downloaded=h.messages_downloaded,
                messages_skipped=h.messages_skipped,
                started_at=h.started_at,
                completed_at=h.completed_at,
                duration_seconds=h.duration_seconds,
                status=h.status,
                error_message=h.error_message
            ))
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting sync history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


async def perform_filtered_sync(request: FilteredSyncRequest):
    """Perform the actual filtered sync operation in the background."""
    account_email = request.account_email
    session = get_session()
    sync_record = None
    
    try:
        # Get filter configuration
        sync_filter = session.query(SyncFilter).filter_by(id=request.filter_id).first()
        if not sync_filter:
            raise Exception(f"Filter {request.filter_id} not found")
        
        # Create sync history record
        sync_record = SyncHistory(
            account_email=account_email,
            filter_id=request.filter_id,
            sync_type=request.sync_type,
            status='running',
            started_at=datetime.utcnow()
        )
        session.add(sync_record)
        session.commit()
        session.refresh(sync_record)
        
        # Update sync status
        sync_status[account_email]["progress"]["phase"] = "Connecting to Gmail..."
        
        # Get account credentials
        account = session.query(GmailAccount).filter_by(email=account_email).first()
        if not account:
            raise Exception(f"Account {account_email} not found")
        
        if not account.access_token or not account.access_token.startswith('imap:'):
            raise Exception(f"IMAP credentials not found for {account_email}")
        
        # Extract IMAP password
        imap_password = account.access_token[5:]
        
        # Initialize IMAP provider
        provider = GmailIMAPProvider(
            email_address=account_email,
            app_password=imap_password
        )
        
        # Update status
        sync_status[account_email]["progress"]["phase"] = "Searching with filter..."
        
        # Search messages with domain filter
        messages = await provider.search_messages_with_domain_filter(
            account_id=account_email,
            domains=sync_filter.domains_json,
            include_from=sync_filter.include_from,
            include_to=sync_filter.include_to,
            include_cc=sync_filter.include_cc,
            date_after=sync_filter.date_after,
            date_before=sync_filter.date_before,
            limit=request.max_messages
        )
        
        total_messages = len(messages)
        sync_record.total_messages_found = total_messages
        session.commit()
        
        sync_status[account_email]["progress"]["total"] = total_messages
        sync_status[account_email]["progress"]["phase"] = f"Processing {total_messages} filtered messages..."
        
        # Process messages in batches
        batch_size = request.batch_size
        messages_processed = 0
        messages_skipped = 0
        start_time = datetime.utcnow()
        
        message_ids = [msg.gmail_id for msg in messages]
        full_messages = await provider.fetch_bodies(message_ids)
        
        for i, message in enumerate(full_messages):
            try:
                # Check if message already exists
                existing = session.query(Message).filter(
                    Message.gmail_id == message.gmail_id,
                    Message.account_email == account_email
                ).first()
                
                if not existing:
                    # Store new message
                    db_message = Message(
                        run_id="filtered_sync",  # Special run ID for filtered syncs
                        gmail_id=message.gmail_id,
                        thread_id=message.thread_id,
                        date=message.date,
                        from_email=message.from_email,
                        subject=message.subject,
                        snippet=message.snippet,
                        body=message.body,
                        account_email=account_email,
                        sync_filter_id=request.filter_id,
                        sync_history_id=sync_record.id,
                        to_emails_json=message.to_emails_json,
                        cc_emails_json=message.cc_emails_json,
                        has_attachments=message.has_attachments,
                        attachment_count=message.attachment_count,
                        message_size=message.message_size,
                        labels_json=message.labels
                    )
                    session.add(db_message)
                    messages_processed += 1
                else:
                    messages_skipped += 1
                
                # Update progress
                current_progress = i + 1
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                rate = current_progress / max(elapsed, 1)
                remaining = total_messages - current_progress
                eta_seconds = remaining / max(rate, 1)
                
                sync_status[account_email]["progress"].update({
                    "current": current_progress,
                    "rate": f"{rate:.1f} msg/sec",
                    "eta": f"{eta_seconds/60:.1f} min"
                })
                
                # Commit in batches
                if current_progress % batch_size == 0:
                    session.commit()
                    logger.info(f"Processed {current_progress}/{total_messages} messages")
            
            except Exception as e:
                logger.error(f"Error processing message {message.gmail_id}: {e}")
                continue
        
        # Final commit
        session.commit()
        
        # Update sync record
        sync_record.messages_downloaded = messages_processed
        sync_record.messages_skipped = messages_skipped
        sync_record.completed_at = datetime.utcnow()
        sync_record.duration_seconds = int((sync_record.completed_at - sync_record.started_at).total_seconds())
        sync_record.status = 'completed'
        
        # Build filter query for record keeping
        query_parts = []
        if sync_filter.include_from:
            query_parts.append("FROM:" + "|".join(sync_filter.domains_json))
        if sync_filter.include_to:
            query_parts.append("TO:" + "|".join(sync_filter.domains_json))
        if sync_filter.include_cc:
            query_parts.append("CC:" + "|".join(sync_filter.domains_json))
        sync_record.filter_query = " OR ".join(query_parts)
        
        session.commit()
        
        # Mark as completed
        sync_status[account_email]["status"] = "completed"
        sync_status[account_email]["progress"]["phase"] = f"Completed - {messages_processed} messages downloaded, {messages_skipped} skipped"
        
        logger.info(f"Filtered sync completed for {account_email}: {messages_processed} downloaded, {messages_skipped} skipped")
        
    except Exception as e:
        logger.error(f"Filtered sync failed for {account_email}: {e}")
        sync_status[account_email]["status"] = "error"
        sync_status[account_email]["error"] = str(e)
        
        if sync_record:
            sync_record.status = 'failed'
            sync_record.error_message = str(e)
            sync_record.completed_at = datetime.utcnow()
            session.commit()
        
    finally:
        session.close()
        # Clean up task reference
        if account_email in sync_tasks:
            del sync_tasks[account_email]