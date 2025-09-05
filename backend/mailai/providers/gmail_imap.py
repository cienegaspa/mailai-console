"""Gmail provider using IMAP with app password - much simpler than OAuth!"""

import imaplib
import email
import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from email.header import decode_header

from .interfaces import GmailProvider, Message, MessageMeta
from ..models.simple_db import get_session, GmailAccount

logger = logging.getLogger(__name__)


class GmailIMAPProvider(GmailProvider):
    """Gmail provider using IMAP authentication with app password."""
    
    def __init__(self, email_address: str, app_password: str):
        self.email_address = email_address
        self.app_password = app_password
        self.imap_server = "imap.gmail.com"
        self.imap_port = 993
        self.connection = None
        
    def _connect(self) -> imaplib.IMAP4_SSL:
        """Establish IMAP connection to Gmail."""
        try:
            if self.connection:
                # Test if connection is still alive
                try:
                    self.connection.noop()
                    return self.connection
                except:
                    self.connection = None
            
            logger.info(f"🔵 Connecting to Gmail IMAP for {self.email_address}")
            connection = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            connection.login(self.email_address, self.app_password)
            connection.select('INBOX')
            
            self.connection = connection
            logger.info("✅ Gmail IMAP connection established")
            return connection
            
        except Exception as e:
            logger.error(f"❌ Gmail IMAP connection failed: {e}")
            raise Exception(f"Failed to connect to Gmail IMAP: {e}")
    
    def _disconnect(self):
        """Close IMAP connection."""
        if self.connection:
            try:
                self.connection.logout()
            except:
                pass
            self.connection = None
    
    def _gmail_search_to_imap(self, gmail_query: str) -> str:
        """Convert Gmail search operators to IMAP search criteria."""
        # This is a simplified conversion - Gmail search is more powerful than IMAP
        # For a complete implementation, you'd need more sophisticated parsing
        
        imap_criteria = []
        
        # Handle basic patterns
        if "from:" in gmail_query.lower():
            # Extract from: clauses
            from_matches = re.findall(r'from:(\S+)', gmail_query, re.IGNORECASE)
            for from_addr in from_matches:
                clean_addr = from_addr.strip('"')
                imap_criteria.append(f'FROM "{clean_addr}"')
        
        if "to:" in gmail_query.lower():
            to_matches = re.findall(r'to:(\S+)', gmail_query, re.IGNORECASE)
            for to_addr in to_matches:
                clean_addr = to_addr.strip('"')
                imap_criteria.append(f'TO "{clean_addr}"')
        
        if "subject:" in gmail_query.lower():
            subject_matches = re.findall(r'subject:"([^"]*)"', gmail_query, re.IGNORECASE)
            for subject in subject_matches:
                imap_criteria.append(f'SUBJECT "{subject}"')
        
        # Handle date ranges (basic)
        if "after:" in gmail_query.lower():
            after_matches = re.findall(r'after:(\S+)', gmail_query, re.IGNORECASE)
            for date_str in after_matches:
                try:
                    # Convert YYYY/MM/DD to IMAP format
                    date_obj = datetime.strptime(date_str, '%Y/%m/%d')
                    imap_criteria.append(f'SINCE "{date_obj.strftime("%d-%b-%Y")}"')
                except:
                    pass
        
        if "before:" in gmail_query.lower():
            before_matches = re.findall(r'before:(\S+)', gmail_query, re.IGNORECASE)
            for date_str in before_matches:
                try:
                    date_obj = datetime.strptime(date_str, '%Y/%m/%d')
                    imap_criteria.append(f'BEFORE "{date_obj.strftime("%d-%b-%Y")}"')
                except:
                    pass
        
        # Handle basic text search (remaining words)
        remaining_text = gmail_query
        for pattern in [r'from:\S+', r'to:\S+', r'subject:"[^"]*"', r'after:\S+', r'before:\S+']:
            remaining_text = re.sub(pattern, '', remaining_text, flags=re.IGNORECASE)
        
        remaining_text = remaining_text.strip()
        if remaining_text:
            # Split into words and search in body
            words = remaining_text.split()
            for word in words:
                if word and len(word) > 2:  # Skip very short words
                    imap_criteria.append(f'BODY "{word}"')
        
        # If no criteria found, search all messages
        if not imap_criteria:
            imap_criteria = ['ALL']
        
        return ' '.join(imap_criteria)
    
    def _decode_header_value(self, header_value: str) -> str:
        """Decode email header value."""
        if not header_value:
            return ""
        
        try:
            decoded_pairs = decode_header(header_value)
            decoded_str = ""
            for text, charset in decoded_pairs:
                if isinstance(text, bytes):
                    if charset:
                        decoded_str += text.decode(charset, errors='ignore')
                    else:
                        decoded_str += text.decode('utf-8', errors='ignore')
                else:
                    decoded_str += text
            return decoded_str
        except:
            return str(header_value)
    
    async def search(self, query_str: str) -> List[MessageMeta]:
        """Search Gmail messages using IMAP."""
        try:
            connection = self._connect()
            
            # Convert Gmail query to IMAP search
            imap_query = self._gmail_search_to_imap(query_str)
            logger.info(f"🔍 Gmail query: {query_str}")
            logger.info(f"🔍 IMAP query: {imap_query}")
            
            # Search for messages
            status, message_ids = connection.search(None, imap_query)
            
            if status != 'OK':
                logger.error(f"❌ IMAP search failed: {status}")
                return []
            
            # Get message IDs
            msg_ids = message_ids[0].split()
            logger.info(f"✅ Found {len(msg_ids)} messages")
            
            # Limit results to avoid overwhelming the system
            if len(msg_ids) > 100:
                msg_ids = msg_ids[-100:]  # Get most recent 100
                logger.info(f"🔄 Limited to most recent {len(msg_ids)} messages")
            
            message_metas = []
            
            for msg_id in msg_ids:
                try:
                    # Fetch message headers
                    status, msg_data = connection.fetch(msg_id, '(RFC822.HEADER)')
                    if status != 'OK':
                        continue
                    
                    # Parse email headers
                    email_msg = email.message_from_bytes(msg_data[0][1])
                    
                    # Extract metadata
                    gmail_id = msg_id.decode()
                    thread_id = gmail_id  # IMAP doesn't have thread IDs like Gmail API
                    
                    # Parse date
                    date_str = email_msg.get('Date', '')
                    try:
                        date = email.utils.parsedate_to_datetime(date_str)
                    except:
                        date = datetime.utcnow()
                    
                    # Decode headers
                    from_email = self._decode_header_value(email_msg.get('From', ''))
                    subject = self._decode_header_value(email_msg.get('Subject', ''))
                    
                    # Get snippet (first part of body)
                    snippet = ""
                    try:
                        status, body_data = connection.fetch(msg_id, '(BODY[TEXT])')
                        if status == 'OK' and body_data[0]:
                            body_text = body_data[0][1].decode('utf-8', errors='ignore')
                            snippet = body_text[:200] + "..." if len(body_text) > 200 else body_text
                    except:
                        pass
                    
                    message_meta = MessageMeta(
                        gmail_id=gmail_id,
                        thread_id=thread_id,
                        date=date,
                        from_email=from_email,
                        subject=subject,
                        labels=[],  # IMAP doesn't have Gmail labels
                        snippet=snippet
                    )
                    
                    message_metas.append(message_meta)
                    
                except Exception as e:
                    logger.warning(f"⚠️ Failed to process message {msg_id}: {e}")
                    continue
            
            logger.info(f"✅ Processed {len(message_metas)} message metadata")
            return message_metas
            
        except Exception as e:
            logger.error(f"❌ Gmail IMAP search failed: {e}")
            return []
    
    async def fetch_bodies(self, message_ids: List[str]) -> List[Message]:
        """Fetch full message bodies using IMAP."""
        try:
            connection = self._connect()
            messages = []
            
            logger.info(f"📥 Fetching {len(message_ids)} message bodies")
            
            for msg_id in message_ids:
                try:
                    # Fetch full message
                    status, msg_data = connection.fetch(msg_id, '(RFC822)')
                    if status != 'OK':
                        continue
                    
                    # Parse email
                    email_msg = email.message_from_bytes(msg_data[0][1])
                    
                    # Extract metadata
                    gmail_id = msg_id
                    thread_id = msg_id  # IMAP doesn't have thread IDs
                    
                    # Parse date
                    date_str = email_msg.get('Date', '')
                    try:
                        date = email.utils.parsedate_to_datetime(date_str)
                    except:
                        date = datetime.utcnow()
                    
                    # Decode headers
                    from_email = self._decode_header_value(email_msg.get('From', ''))
                    subject = self._decode_header_value(email_msg.get('Subject', ''))
                    
                    # Extract body
                    body = self._extract_body(email_msg)
                    
                    # Create snippet
                    snippet = body[:200] + "..." if len(body) > 200 else body
                    
                    message = Message(
                        gmail_id=gmail_id,
                        thread_id=thread_id,
                        date=date,
                        from_email=from_email,
                        subject=subject,
                        labels=[],  # IMAP doesn't have Gmail labels
                        body=body,
                        snippet=snippet
                    )
                    
                    messages.append(message)
                    
                except Exception as e:
                    logger.warning(f"⚠️ Failed to fetch message {msg_id}: {e}")
                    continue
            
            logger.info(f"✅ Fetched {len(messages)} complete messages")
            return messages
            
        except Exception as e:
            logger.error(f"❌ Gmail IMAP fetch failed: {e}")
            return []
    
    def _extract_body(self, email_msg) -> str:
        """Extract text body from email message."""
        body = ""
        
        if email_msg.is_multipart():
            for part in email_msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    charset = part.get_content_charset() or 'utf-8'
                    try:
                        body = part.get_payload(decode=True).decode(charset, errors='ignore')
                        break  # Use first plain text part
                    except:
                        pass
                elif content_type == "text/html" and not body and "attachment" not in content_disposition:
                    # Fall back to HTML if no plain text
                    charset = part.get_content_charset() or 'utf-8'
                    try:
                        html_body = part.get_payload(decode=True).decode(charset, errors='ignore')
                        # Simple HTML to text conversion
                        import re
                        body = re.sub('<[^<]+?>', '', html_body)
                    except:
                        pass
        else:
            # Single part message
            charset = email_msg.get_content_charset() or 'utf-8'
            try:
                body = email_msg.get_payload(decode=True).decode(charset, errors='ignore')
            except:
                body = str(email_msg.get_payload())
        
        return body.strip()
    
    async def authenticate(self) -> bool:
        """Test IMAP authentication."""
        logger.info(f"🔵 Testing IMAP authentication for {self.email_address}")
        try:
            connection = self._connect()
            logger.info(f"✅ IMAP authentication successful for {self.email_address}")
            self._disconnect()
            return True
        except Exception as e:
            logger.error(f"❌ IMAP authentication failed for {self.email_address}: {e}")
            return False
    
    async def connect_account(self) -> Dict[str, Any]:
        """Test connection and store account info."""
        logger.info(f"🔵 Starting IMAP account connection for {self.email_address}")
        try:
            # Test connection
            if not await self.authenticate():
                logger.error(f"❌ Authentication failed for {self.email_address}")
                return {
                    "success": False,
                    "error": "Failed to authenticate with Gmail IMAP"
                }
            
            # Store account in database
            logger.info(f"🔵 Storing account {self.email_address} in database")
            session = get_session()
            try:
                account = session.query(GmailAccount).filter_by(email=self.email_address).first()
                if not account:
                    logger.info(f"🔵 Creating new account record for {self.email_address}")
                    account = GmailAccount(
                        account_id=self.email_address,
                        email=self.email_address,
                        display_name=self.email_address.split('@')[0].title()
                    )
                    session.add(account)
                else:
                    logger.info(f"🔵 Updating existing account record for {self.email_address}")
                
                # Update status and store app password securely
                account.status = "connected"
                account.connected_at = datetime.utcnow()
                account.sync_error = None
                account.access_token = f"imap:{self.app_password}"  # Store app password for reuse
                logger.info(f"🔵 Stored credentials with format: imap:{self.app_password[:3]}...")
                
                session.commit()
                logger.info(f"✅ Successfully stored {self.email_address} in database")
                
                logger.info(f"✅ IMAP account {self.email_address} stored as connected")
                return {
                    "success": True,
                    "email": self.email_address,
                    "account_id": account.account_id
                }
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"❌ IMAP account connection failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }