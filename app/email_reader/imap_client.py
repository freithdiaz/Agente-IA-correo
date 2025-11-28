import imaplib
import email
from email.header import decode_header
import os
import logging
from app.config import Config
import re

logger = logging.getLogger(__name__)

class ImapClient:
    def __init__(self):
        self.config = Config
        self.mail = None

    def connect(self):
        """Connects to the IMAP server."""
        try:
            self.mail = imaplib.IMAP4_SSL(self.config.IMAP_SERVER, self.config.IMAP_PORT)
            self.mail.login(self.config.IMAP_USER, self.config.IMAP_PASSWORD)
            logger.info(f"Connected to IMAP server: {self.config.IMAP_SERVER}")
        except Exception as e:
            logger.error(f"Failed to connect to IMAP server: {e}")
            raise

    def check_connection(self):
        """Checks if connection is active, reconnects if not."""
        try:
            self.mail.noop()
        except Exception:
            logger.warning("IMAP connection lost. Reconnecting...")
            self.connect()

    def get_messages(self, subject_filter=None):
        """Fetches unread messages matching the subject filter."""
        if not self.mail:
            self.connect()
        else:
            self.check_connection()

        try:
            self.mail.select("INBOX")
            
            # Search for ALL messages (not just unread)
            # We'll filter by subject and then check if they're unread
            status, messages = self.mail.search(None, 'ALL')
            
            if status != "OK":
                logger.warning("No messages found or error searching.")
                return []

            email_ids = messages[0].split()
            found_messages = []
            
            # Limit to last 10 messages to avoid timeout
            email_ids = email_ids[-10:] if len(email_ids) > 10 else email_ids

            for e_id in email_ids:
                try:
                    # Fetch the email body using BODY.PEEK to avoid marking as read
                    res, msg_data = self.mail.fetch(e_id, "(BODY.PEEK[])")
                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])
                            
                            # Decode Subject with error handling
                            subject, encoding = decode_header(msg["Subject"])[0]
                            if isinstance(subject, bytes):
                                # Try multiple encodings with fallback
                                try:
                                    subject = subject.decode(encoding if encoding else "utf-8")
                                except (UnicodeDecodeError, LookupError):
                                    try:
                                        subject = subject.decode("latin-1")
                                    except:
                                        subject = subject.decode("utf-8", errors="replace")
                            
                            # No longer filter by subject - process all emails

                            # Extract Body with error handling
                            body = ""
                            if msg.is_multipart():
                                for part in msg.walk():
                                    content_type = part.get_content_type()
                                    content_disposition = str(part.get("Content-Disposition"))
                                    
                                    if "attachment" not in content_disposition:
                                        if content_type == "text/plain":
                                            try:
                                                body = part.get_payload(decode=True).decode(errors="replace")
                                            except:
                                                body = str(part.get_payload(decode=True))
                                            break # Prefer plain text
                                        elif content_type == "text/html":
                                            try:
                                                body = part.get_payload(decode=True).decode(errors="replace")
                                            except:
                                                body = str(part.get_payload(decode=True))
                            else:
                                try:
                                    body = msg.get_payload(decode=True).decode(errors="replace")
                                except:
                                    body = str(msg.get_payload(decode=True))

                            # Check for Attachments (optional now)
                            has_attachments = False
                            for part in msg.walk():
                                if part.get_content_maintype() == 'multipart':
                                    continue
                                if part.get('Content-Disposition') is None:
                                    continue
                                has_attachments = True
                                break
                            
                            # Check if message is unread (UNSEEN flag)
                            flags_res, flags_data = self.mail.fetch(e_id, '(FLAGS)')
                            is_unread = b'\\Seen' not in flags_data[0] if flags_data else True

                            # Process if unread (with or without attachments)
                            if is_unread:
                                found_messages.append({
                                    'id': e_id, # Keep as bytes or string depending on lib, usually bytes in list
                                    'subject': subject,
                                    'hasAttachments': True,
                                    'body': {'content': body}, # Match Outlook structure for compatibility
                                    'msg_object': msg # Store full object for attachment downloading
                                })
                except Exception as e:
                    logger.warning(f"Error processing message {e_id}: {e}")
                    continue
            
            return found_messages

        except Exception as e:
            logger.error(f"Error fetching IMAP messages: {e}")
            return []

    def download_attachments(self, message_id, save_path):
        """Downloads attachments for a specific message."""
        # In IMAP, we might have already fetched the message, or we fetch it again.
        # Since we stored 'msg_object' in get_messages, we can use that if we passed the whole object,
        # but main.py passes message_id. So we fetch again to be stateless-ish.
        
        if not self.mail:
            self.connect()
            self.mail.select("INBOX")

        saved_files = []
        try:
            res, msg_data = self.mail.fetch(message_id, "(BODY.PEEK[])")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    for part in msg.walk():
                        if part.get_content_maintype() == 'multipart':
                            continue
                        if part.get('Content-Disposition') is None:
                            continue
                            
                        filename = part.get_filename()
                        if filename:
                            filename = decode_header(filename)[0][0]
                            if isinstance(filename, bytes):
                                filename = filename.decode()
                                
                            # Accept multiple file types
                            if filename.endswith(('.xlsx', '.xls', '.csv', '.doc', '.docx', '.pdf', '.txt')):
                                filepath = os.path.join(save_path, filename)
                                with open(filepath, "wb") as f:
                                    f.write(part.get_payload(decode=True))
                                saved_files.append(filepath)
                                logger.info(f"Downloaded: {filename}")
                                
        except Exception as e:
            logger.error(f"Error downloading attachments (IMAP): {e}")
            
        return saved_files

    def mark_as_read(self, message_id):
        """Marks a message as read."""
        if not self.mail:
            self.connect()
            self.mail.select("INBOX")
            
        try:
            # In IMAP, fetching the body usually marks it as read (Seen).
            # But we can explicitly set the flag to be sure.
            self.mail.store(message_id, '+FLAGS', '\\Seen')
            logger.info(f"Message {message_id} marked as read.")
        except Exception as e:
            logger.error(f"Error marking message as read (IMAP): {e}")
