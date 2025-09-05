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
        """Establish IMAP connection to Gmail with timeout."""
        try:
            logger.info(f"🔵 Connecting to Gmail IMAP for {self.email_address}")
            # Create connection with timeout
            import socket
            connection = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            connection.sock.settimeout(30)  # 30 second timeout
            connection.login(self.email_address, self.app_password)
            connection.select('INBOX')
            
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
        connection = None
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
        finally:
            # Always disconnect
            if connection:
                try:
                    connection.logout()
                except:
                    pass
    
    async def fetch_bodies(self, message_ids: List[str]) -> List[Message]:
        """Fetch full message bodies using IMAP."""
        connection = None
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
                    
                    # Better thread ID extraction from headers
                    message_id = email_msg.get('Message-ID', '').strip()
                    in_reply_to = email_msg.get('In-Reply-To', '').strip() 
                    references = email_msg.get('References', '').strip()
                    
                    # Use In-Reply-To for threading, fall back to Message-ID
                    if in_reply_to:
                        thread_id = in_reply_to
                    elif references:
                        # Use first reference as thread ID
                        refs = references.split()
                        thread_id = refs[0] if refs else message_id or msg_id
                    else:
                        thread_id = message_id or msg_id
                    
                    # Parse date
                    date_str = email_msg.get('Date', '')
                    try:
                        date = email.utils.parsedate_to_datetime(date_str)
                    except:
                        date = datetime.utcnow()
                    
                    # Decode headers
                    from_email = self._decode_header_value(email_msg.get('From', ''))
                    subject = self._decode_header_value(email_msg.get('Subject', ''))
                    to_emails = self._extract_email_addresses(email_msg.get('To', ''))
                    cc_emails = self._extract_email_addresses(email_msg.get('Cc', ''))
                    bcc_emails = self._extract_email_addresses(email_msg.get('Bcc', ''))
                    reply_to = self._decode_header_value(email_msg.get('Reply-To', ''))
                    
                    # Extract body
                    body = self._extract_body(email_msg)
                    
                    # Create snippet
                    snippet = body[:200] + "..." if len(body) > 200 else body
                    
                    # Message size and attachments
                    message_size = len(str(email_msg)) if email_msg else 0
                    has_attachments = self._has_attachments(email_msg)
                    attachment_count = self._count_attachments(email_msg)
                    
                    # Content type info
                    content_type = email_msg.get_content_type() if hasattr(email_msg, 'get_content_type') else 'text/plain'
                    is_multipart = email_msg.is_multipart() if hasattr(email_msg, 'is_multipart') else False
                    
                    message = Message(
                        gmail_id=gmail_id,
                        thread_id=thread_id,
                        date=date,
                        from_email=from_email,
                        subject=subject,
                        labels=[],  # IMAP doesn't have Gmail labels
                        body=body,
                        snippet=snippet,
                        to_emails_json=to_emails,
                        cc_emails_json=cc_emails,
                        bcc_emails_json=bcc_emails,
                        reply_to_email=reply_to,
                        message_size=message_size,
                        has_attachments=has_attachments,
                        attachment_count=attachment_count,
                        message_id_header=message_id,
                        in_reply_to=in_reply_to,
                        references=references,
                        content_type=content_type,
                        is_multipart=is_multipart
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
        finally:
            # Always disconnect
            if connection:
                try:
                    connection.logout()
                except:
                    pass
    
    def _extract_email_addresses(self, header_value: str) -> List[str]:
        """Extract email addresses from To, Cc, Bcc headers."""
        if not header_value:
            return []
        
        import email.utils
        addresses = []
        try:
            # Parse addresses
            parsed = email.utils.getaddresses([header_value])
            for name, addr in parsed:
                if addr:
                    addresses.append(addr.strip())
        except:
            # Fallback: simple split
            addresses = [addr.strip() for addr in header_value.split(',') if '@' in addr]
        
        return addresses
    
    def _has_attachments(self, email_msg) -> bool:
        """Check if message has attachments."""
        if not email_msg.is_multipart():
            return False
        
        for part in email_msg.walk():
            content_disposition = str(part.get("Content-Disposition", ""))
            if "attachment" in content_disposition:
                return True
        
        return False
    
    def _count_attachments(self, email_msg) -> int:
        """Count number of attachments."""
        if not email_msg.is_multipart():
            return 0
        
        count = 0
        for part in email_msg.walk():
            content_disposition = str(part.get("Content-Disposition", ""))
            if "attachment" in content_disposition:
                count += 1
        
        return count

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
        connection = None
        try:
            connection = self._connect()
            logger.info(f"✅ IMAP authentication successful for {self.email_address}")
            return True
        except Exception as e:
            logger.error(f"❌ IMAP authentication failed for {self.email_address}: {e}")
            return False
        finally:
            if connection:
                try:
                    connection.logout()
                except:
                    pass
    
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
    
    def build_domain_filter_query(
        self, 
        domains: List[str], 
        include_from: bool = True,
        include_to: bool = True, 
        include_cc: bool = True,
        date_after: Optional[datetime] = None,
        date_before: Optional[datetime] = None
    ) -> str:
        """Build IMAP search query for domain filtering."""
        
        # Build domain conditions
        domain_conditions = []
        
        for domain in domains:
            domain_parts = []
            
            if include_from:
                domain_parts.append(f"FROM {domain}")
            if include_to:
                domain_parts.append(f"TO {domain}")
            if include_cc:
                domain_parts.append(f"CC {domain}")
            
            if domain_parts:
                # Combine with OR for this domain
                domain_conditions.append(f"({' '.join(domain_parts)})")
        
        # Start with domain filter
        query_parts = []
        if domain_conditions:
            if len(domain_conditions) == 1:
                query_parts.append(domain_conditions[0])
            else:
                query_parts.append(f"({' OR '.join(domain_conditions)})")
        
        # Add date filters
        if date_after:
            query_parts.append(f"SINCE {date_after.strftime('%d-%b-%Y')}")
        if date_before:
            query_parts.append(f"BEFORE {date_before.strftime('%d-%b-%Y')}")
        
        # Combine all conditions with AND
        final_query = ' '.join(query_parts) if query_parts else "ALL"
        
        logger.info(f"Built IMAP search query: {final_query}")
        return final_query
    
    async def get_message_count_for_domains(
        self,
        domains: List[str],
        include_from: bool = True,
        include_to: bool = True,
        include_cc: bool = True,
        date_after: Optional[datetime] = None,
        date_before: Optional[datetime] = None
    ) -> int:
        """Get estimated message count for domain filter without downloading content."""
        connection = None
        try:
            connection = self._connect()
            
            # Build IMAP search query
            search_query = self.build_domain_filter_query(
                domains=domains,
                include_from=include_from,
                include_to=include_to,
                include_cc=include_cc,
                date_after=date_after,
                date_before=date_before
            )
            
            logger.info(f"🔍 Getting message count with query: {search_query}")
            
            # Perform IMAP search (fast, only gets message UIDs)
            status, message_ids = connection.search(None, search_query)
            
            if status != 'OK':
                logger.warning(f"Search failed with status: {status}")
                return 0
            
            # Count message IDs
            if message_ids[0]:
                msg_ids = message_ids[0].split()
                count = len(msg_ids)
                logger.info(f"✅ Found {count} messages matching domain filter")
                return count
            else:
                logger.info("✅ No messages found matching domain filter")
                return 0
                
        except Exception as e:
            logger.error(f"❌ Error getting message count for domains: {e}")
            return 0
        finally:
            if connection:
                try:
                    connection.logout()
                except:
                    pass
    
    async def search_messages_with_domain_filter(
        self,
        account_id: str,
        domains: List[str],
        include_from: bool = True,
        include_to: bool = True,
        include_cc: bool = True,
        date_after: Optional[datetime] = None,
        date_before: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[MessageMeta]:
        """Search messages using domain-based filtering."""
        connection = None
        try:
            connection = self._connect()
            
            # Build IMAP search query
            search_query = self.build_domain_filter_query(
                domains=domains,
                include_from=include_from,
                include_to=include_to,
                include_cc=include_cc,
                date_after=date_after,
                date_before=date_before
            )
            
            logger.info(f"🔍 Searching with domain filter: {search_query}")
            
            # Perform search
            status, message_ids = connection.search(None, search_query)
            if status != 'OK':
                logger.error(f"Search failed: {status}")
                return []
            
            if not message_ids[0]:
                logger.info("No messages found matching filter")
                return []
            
            msg_ids = message_ids[0].split()
            
            # Apply limit if specified
            if limit and len(msg_ids) > limit:
                msg_ids = msg_ids[:limit]
                logger.info(f"Limited results to {limit} messages")
            
            logger.info(f"Found {len(msg_ids)} messages, fetching metadata...")
            
            message_metas = []
            for msg_id in msg_ids:
                try:
                    # Fetch headers and basic info
                    status, msg_data = connection.fetch(msg_id, '(ENVELOPE INTERNALDATE)')
                    if status != 'OK':
                        continue
                    
                    # Parse envelope
                    envelope = msg_data[0][1]
                    date_part = msg_data[0][0]
                    
                    # Extract date
                    import email.utils
                    date_str = date_part.decode('utf-8').split('INTERNALDATE "')[1].split('"')[0]
                    date = email.utils.parsedate_to_datetime(date_str.replace('  ', ' '))
                    
                    # Parse envelope for basic info
                    import imaplib
                    envelope_str = envelope.decode('utf-8', errors='ignore')
                    
                    # Extract basic fields (simplified parsing)
                    subject = "No Subject"
                    from_email = "unknown@unknown.com"
                    
                    # Try to extract subject and from email from envelope
                    try:
                        # This is a simplified envelope parser
                        # In production, you'd want more robust parsing
                        if '"' in envelope_str:
                            parts = envelope_str.split('"')
                            if len(parts) > 3:
                                subject = parts[3] if parts[3].strip() else "No Subject"
                            if len(parts) > 7:
                                from_email = parts[7] if '@' in parts[7] else from_email
                    except:
                        pass
                    
                    # Create MessageMeta
                    message_meta = MessageMeta(
                        gmail_id=msg_id.decode(),
                        thread_id=msg_id.decode(),  # IMAP doesn't have thread IDs
                        date=date,
                        from_email=from_email,
                        subject=subject,
                        labels=[],
                        snippet=""  # Will be filled when body is fetched
                    )
                    
                    message_metas.append(message_meta)
                    
                except Exception as e:
                    logger.warning(f"Failed to process message {msg_id}: {e}")
                    continue
            
            logger.info(f"✅ Retrieved {len(message_metas)} message metadata with domain filter")
            return message_metas
            
        except Exception as e:
            logger.error(f"❌ Domain-filtered search failed: {e}")
            return []
        finally:
            if connection:
                try:
                    connection.logout()
                except:
                    pass