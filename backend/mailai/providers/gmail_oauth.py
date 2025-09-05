"""Real Gmail provider with OAuth2 authentication."""

import base64
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse, parse_qs

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .interfaces import GmailProvider, Message, MessageMeta
from ..models.simple_db import get_session, GmailAccount

logger = logging.getLogger(__name__)


class GmailOAuthProvider(GmailProvider):
    """Gmail provider using OAuth2 for authentication."""
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scopes = [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile',
            'openid'
        ]
        
    def create_auth_url(self, state: str = None) -> str:
        """Create OAuth authorization URL."""
        # Use consistent client config format
        client_config = {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        }
        
        flow = Flow.from_client_config(
            client_config,
            scopes=self.scopes
        )
        flow.redirect_uri = self.redirect_uri
        
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state,
            prompt='consent'  # Force consent to get refresh token
        )
        
        return auth_url
    
    async def handle_oauth_callback(self, authorization_response: str) -> Dict[str, Any]:
        """Handle OAuth callback and store credentials."""
        logger.info(f"🔵 OAuth callback started with response: {authorization_response[:100]}...")
        try:
            # Use exact same client config format as create_auth_url
            client_config = {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token"
                }
            }
            
            flow = Flow.from_client_config(
                client_config,
                scopes=self.scopes
            )
            flow.redirect_uri = self.redirect_uri
            
            # Exchange authorization code for tokens
            logger.info("🔵 Exchanging authorization code for tokens...")
            flow.fetch_token(authorization_response=authorization_response)
            credentials = flow.credentials
            logger.info(f"🔵 Tokens received - Access token: {bool(credentials.token)}, Refresh token: {bool(credentials.refresh_token)}")
            
            # Get user email from Gmail API
            logger.info("🔵 Getting user profile from Gmail API...")
            service = build('gmail', 'v1', credentials=credentials)
            profile = service.users().getProfile(userId='me').execute()
            email = profile['emailAddress']
            logger.info(f"🔵 Gmail profile retrieved for: {email}")
            
            # Store account in database
            logger.info(f"🔵 Storing account in database: {email}")
            session = get_session()
            try:
                account = session.query(GmailAccount).filter_by(email=email).first()
                if not account:
                    logger.info(f"🔵 Creating new account for: {email}")
                    account = GmailAccount(
                        account_id=email,  # Use email as account ID for simplicity
                        email=email
                    )
                    session.add(account)
                else:
                    logger.info(f"🔵 Updating existing account for: {email}")
                
                # Update OAuth tokens
                logger.info(f"🔵 Setting account status to 'connected' and storing tokens...")
                account.access_token = credentials.token
                account.refresh_token = credentials.refresh_token
                account.token_expires_at = credentials.expiry
                account.status = "connected"
                account.connected_at = datetime.utcnow()
                account.sync_error = None
                
                logger.info(f"🔵 Committing database changes...")
                session.commit()
                logger.info(f"✅ Account {email} successfully stored as 'connected'")
                
                return {
                    "success": True,
                    "email": email,
                    "account_id": account.account_id
                }
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"❌ OAuth callback error: {e}")
            logger.exception("Full OAuth callback error traceback:")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_credentials(self, account_id: str) -> Optional[Credentials]:
        """Get and refresh credentials for an account."""
        session = get_session()
        try:
            account = session.query(GmailAccount).filter_by(account_id=account_id).first()
            if not account or not account.access_token:
                return None
            
            credentials = Credentials(
                token=account.access_token,
                refresh_token=account.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            
            # Refresh if needed
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
                
                # Update tokens in database
                account.access_token = credentials.token
                account.token_expires_at = credentials.expiry
                account.updated_at = datetime.utcnow()
                session.commit()
            
            return credentials
            
        except Exception as e:
            logger.error(f"Error getting credentials for {account_id}: {e}")
            # Mark account as error
            account = session.query(GmailAccount).filter_by(account_id=account_id).first()
            if account:
                account.status = "error"
                account.sync_error = str(e)
                session.commit()
            return None
        finally:
            session.close()
    
    async def search(self, query_str: str) -> List[MessageMeta]:
        """Search Gmail messages by query string using the first connected account."""
        # For now, use the first available account
        session = get_session()
        try:
            account = session.query(GmailAccount).filter_by(status="connected").first()
            if not account:
                return []
            return await self.search_messages(account.account_id, query_str)
        finally:
            session.close()
    
    async def fetch_bodies(self, message_ids: List[str]) -> List[Message]:
        """Fetch full message bodies by ID using the first connected account."""
        # For now, use the first available account
        session = get_session()
        try:
            account = session.query(GmailAccount).filter_by(status="connected").first()
            if not account:
                return []
            
            messages = []
            for msg_id in message_ids:
                message = await self.get_message(account.account_id, msg_id)
                if message:
                    messages.append(message)
            return messages
        finally:
            session.close()
    
    async def authenticate(self) -> bool:
        """Check if any accounts are authenticated."""
        session = get_session()
        try:
            account = session.query(GmailAccount).filter_by(status="connected").first()
            return account is not None
        finally:
            session.close()
    
    async def search_messages(self, account_id: str, query: str, max_results: int = 100) -> List[MessageMeta]:
        """Search for messages in Gmail."""
        credentials = self._get_credentials(account_id)
        if not credentials:
            raise Exception(f"No valid credentials for account {account_id}")
        
        try:
            service = build('gmail', 'v1', credentials=credentials)
            
            # Search for messages
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            message_metas = []
            
            for msg in messages:
                # Get message metadata
                msg_data = service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='metadata',
                    metadataHeaders=['From', 'Subject', 'Date']
                ).execute()
                
                # Parse headers
                headers = {h['name']: h['value'] for h in msg_data['payload']['headers']}
                
                # Parse date
                date_str = headers.get('Date', '')
                try:
                    date = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z')
                except:
                    date = datetime.utcnow()
                
                message_meta = MessageMeta(
                    gmail_id=msg['id'],
                    thread_id=msg_data['threadId'],
                    date=date,
                    from_email=headers.get('From', ''),
                    subject=headers.get('Subject', ''),
                    labels=msg_data.get('labelIds', []),
                    snippet=msg_data.get('snippet', '')
                )
                
                message_metas.append(message_meta)
            
            return message_metas
            
        except HttpError as e:
            logger.error(f"Gmail API error for {account_id}: {e}")
            raise Exception(f"Gmail API error: {e}")
    
    async def get_message(self, account_id: str, message_id: str) -> Optional[Message]:
        """Get full message content."""
        credentials = self._get_credentials(account_id)
        if not credentials:
            raise Exception(f"No valid credentials for account {account_id}")
        
        try:
            service = build('gmail', 'v1', credentials=credentials)
            
            # Get full message
            msg_data = service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            # Parse headers
            headers = {h['name']: h['value'] for h in msg_data['payload']['headers']}
            
            # Parse date
            date_str = headers.get('Date', '')
            try:
                date = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z')
            except:
                date = datetime.utcnow()
            
            # Extract body and check for attachments
            body = self._extract_body(msg_data['payload'])
            has_attachments, attachment_count = self._check_attachments(msg_data['payload'])
            
            # Extract recipient emails
            to_emails = self._parse_email_list(headers.get('To', ''))
            cc_emails = self._parse_email_list(headers.get('Cc', ''))
            bcc_emails = self._parse_email_list(headers.get('Bcc', ''))
            
            # Get message size (approximate from payload)
            message_size = msg_data.get('sizeEstimate', 0)
            
            # Determine content type and multipart status
            content_type = msg_data['payload'].get('mimeType', 'text/plain')
            is_multipart = 'parts' in msg_data['payload']
            
            message = Message(
                gmail_id=message_id,
                thread_id=msg_data['threadId'],
                date=date,
                from_email=headers.get('From', ''),
                subject=headers.get('Subject', ''),
                labels=msg_data.get('labelIds', []),
                body=body,
                snippet=msg_data.get('snippet', ''),
                to_emails_json=to_emails,
                cc_emails_json=cc_emails,
                bcc_emails_json=bcc_emails,
                reply_to_email=headers.get('Reply-To'),
                message_size=message_size,
                has_attachments=has_attachments,
                attachment_count=attachment_count,
                message_id_header=headers.get('Message-ID'),
                in_reply_to=headers.get('In-Reply-To'),
                references=headers.get('References'),
                content_type=content_type,
                is_multipart=is_multipart
            )
            
            return message
            
        except HttpError as e:
            logger.error(f"Error getting message {message_id} for {account_id}: {e}")
            return None
    
    def _extract_body(self, payload: Dict[str, Any]) -> str:
        """Extract text body from Gmail message payload."""
        body = ""
        
        if 'parts' in payload:
            # Multipart message
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        body += base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                elif part['mimeType'] == 'text/html' and not body:
                    # Fall back to HTML if no plain text
                    if 'data' in part['body']:
                        html_body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                        # Could add HTML to text conversion here
                        body = html_body
        else:
            # Single part message
            if payload['mimeType'] == 'text/plain':
                if 'data' in payload['body']:
                    body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
        
        return body
    
    def _check_attachments(self, payload: Dict[str, Any]) -> tuple[bool, int]:
        """Check if message has attachments and count them."""
        attachment_count = 0
        
        def count_attachments(part: Dict[str, Any]):
            nonlocal attachment_count
            if 'parts' in part:
                for subpart in part['parts']:
                    count_attachments(subpart)
            elif part.get('filename') and part['filename'].strip():
                attachment_count += 1
            elif part.get('body', {}).get('attachmentId'):
                attachment_count += 1
        
        count_attachments(payload)
        return attachment_count > 0, attachment_count
    
    def _parse_email_list(self, email_str: str) -> List[str]:
        """Parse comma-separated email list."""
        if not email_str:
            return []
        
        # Split by comma and clean up
        emails = []
        for email in email_str.split(','):
            email = email.strip()
            if email:
                # Extract email from "Name <email@domain.com>" format
                if '<' in email and '>' in email:
                    email = email[email.find('<')+1:email.find('>')]
                emails.append(email)
        
        return emails
    
    async def disconnect_account(self, account_id: str) -> bool:
        """Disconnect and remove account."""
        session = get_session()
        try:
            account = session.query(GmailAccount).filter_by(account_id=account_id).first()
            if account:
                account.status = "disconnected"
                account.access_token = None
                account.refresh_token = None
                account.token_expires_at = None
                account.sync_error = None
                account.updated_at = datetime.utcnow()
                session.commit()
                return True
            return False
        finally:
            session.close()
    
    async def get_account_info(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Get account information."""
        session = get_session()
        try:
            account = session.query(GmailAccount).filter_by(account_id=account_id).first()
            if not account:
                return None
            
            return {
                "account_id": account.account_id,
                "email": account.email,
                "display_name": account.display_name,
                "status": account.status,
                "connected_at": account.connected_at.isoformat() if account.connected_at else None,
                "last_sync": account.last_sync.isoformat() if account.last_sync else None,
                "total_messages": account.total_messages,
                "sync_error": account.sync_error
            }
        finally:
            session.close()
    
    async def list_accounts(self) -> List[Dict[str, Any]]:
        """List all connected accounts."""
        session = get_session()
        try:
            accounts = session.query(GmailAccount).all()
            return [
                {
                    "account_id": account.account_id,
                    "email": account.email,
                    "display_name": account.display_name,
                    "status": account.status,
                    "connected_at": account.connected_at.isoformat() if account.connected_at else None,
                    "last_sync": account.last_sync.isoformat() if account.last_sync else None,
                    "total_messages": account.total_messages,
                    "sync_error": account.sync_error
                }
                for account in accounts
            ]
        finally:
            session.close()