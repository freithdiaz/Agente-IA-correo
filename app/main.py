import logging
import time
import os
from app.config import Config
from app.email_reader.outlook_client import OutlookClient
from app.processor.excel_processor import ExcelProcessor
from app.processor.text_processor import TextProcessor
from app.ai.ai_client import AIClient
from app.telegram.telegram_sender import TelegramSender
from app.mcp.file_editor_server import FileEditorServer
from app.telegram.confirmation_handler import confirmation_handler
from app.telegram.bot_server import bot_server

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting Automated Email Processing System...")
    
    try:
        # Validate Config
        Config.validate()
        
        # Initialize Clients
        if Config.EMAIL_PROVIDER == "IMAP":
            from app.email_reader.imap_client import ImapClient
            outlook = ImapClient()
            logger.info("Using IMAP Client")
        else:
            outlook = OutlookClient()
            logger.info("Using Outlook Client (Graph API)")
            
        excel_processor = ExcelProcessor()
        text_processor = TextProcessor()
        ai_client = AIClient()
        telegram = TelegramSender()
        mcp_server = FileEditorServer()
        
        # Start Telegram bot for handling confirmations
        bot_server.start_polling()
        logger.info("Telegram bot server started for confirmations")
        
        logger.info("Service started. Press Ctrl+C to stop.")
        
        while True:
            try:
                # 1. Check for Emails (all unread, no subject filter)
                logger.info("Checking for new unread emails...")
                messages = outlook.get_messages(subject_filter=None)
                
                if not messages:
                    logger.info("No new matching emails found.")
                
                for msg in messages:
                    msg_id = msg['id']
                    subject = msg.get('subject')
                    if not subject:
                        subject = "Sin Asunto"
                    
                    body_content = msg.get('body', {}).get('content', '')
                    
                    # Clean body content (remove HTML tags)
                    import re
                    body_text = re.sub('<[^<]+?>', '', body_content)
                    
                    logger.info(f"Processing email: {subject}")
                    
                    try:
                        # 2. Download Attachments (if any)
                        saved_files = outlook.download_attachments(msg_id, Config.ATTACHMENT_SAVE_PATH)
                        
                        data_summary = ""
                        
                        if saved_files:
                            # Process attachments
                            for file_path in saved_files:
                                logger.info(f"Processing file: {file_path}")
                                
                                # Check file type and process accordingly
                                if file_path.endswith(('.xlsx', '.xls')):
                                    excel_summary = excel_processor.process_excel(file_path)
                                    data_summary += excel_summary + "\n\n"
                                    
                                    # MCP Analysis for potential editing
                                    logger.info("Analyzing file for potential improvements...")
                                    analysis_result = mcp_server.call_tool("analyze_excel", {"file_path": file_path})
                                    
                                    if analysis_result.get("needs_editing"):
                                        # Create confirmation request
                                        def on_confirm(data):
                                            """Callback when user confirms editing"""
                                            logger.info("User confirmed file editing")
                                            file_path = data["file_path"]
                                            suggestions = data["suggestions"]
                                            
                                            # Apply edits
                                            edit_result = mcp_server.call_tool("edit_excel", {
                                                "file_path": file_path,
                                                "operations": suggestions
                                            })
                                            
                                            if edit_result.get("success"):
                                                # Save edited file
                                                new_path = mcp_server.call_tool("save_file", {
                                                    "dataframe": edit_result["dataframe"],
                                                    "original_path": file_path,
                                                    "suffix": "_corregido"
                                                })
                                                
                                                return {"file_path": new_path}
                                            else:
                                                raise Exception(edit_result.get("error", "Unknown error"))
                                        
                                        def on_cancel(data):
                                            """Callback when user cancels"""
                                            logger.info("User cancelled file editing")
                                            return {"cancelled": True}
                                        
                                        # Create confirmation
                                        confirmation_id = confirmation_handler.create_confirmation(
                                            message="File editing confirmation",
                                            data={
                                                "file_path": file_path,
                                                "suggestions": analysis_result["suggestions"]
                                            },
                                            on_confirm=on_confirm,
                                            on_cancel=on_cancel
                                        )
                                        
                                        # Send confirmation message to Telegram
                                        conf_message = confirmation_handler.format_confirmation_message(
                                            confirmation_id,
                                            analysis_result["issues"],
                                            analysis_result["suggestions"]
                                        )
                                        telegram.send_confirmation_message(conf_message, confirmation_id)
                                        logger.info(f"Sent confirmation request {confirmation_id} to Telegram")
                                    
                                elif file_path.endswith('.csv'):
                                    # For CSV, read and summarize
                                    import pandas as pd
                                    df = pd.read_csv(file_path)
                                    data_summary += f"CSV File: {file_path.split(os.sep)[-1]}\n"
                                    data_summary += f"Rows: {len(df)}, Columns: {len(df.columns)}\n"
                                    data_summary += f"Columns: {', '.join(df.columns)}\n"
                                    data_summary += df.head(10).to_string() + "\n\n"
                                
                                elif file_path.endswith(('.docx', '.pdf', '.txt')):
                                    # Process text documents
                                    text_summary = text_processor.process_file(file_path)
                                    data_summary += text_summary + "\n\n"
                                    
                                else:
                                    # For other files, just note them
                                    data_summary += f"Archivo adjunto: {file_path.split(os.sep)[-1]}\n\n"
                        else:
                            logger.info("No attachments found. Processing email body only.")
                        
                        # 3. AI Analysis (with or without attachments)
                        logger.info("Generating AI Analysis...")
                        analysis = ai_client.analyze_data(data_summary, email_body=body_text)
                        
                        # 4. Send to Telegram
                        file_info = f"*Adjuntos:* {len(saved_files)}" if saved_files else "*Sin adjuntos*"
                        message_text = f"📧 *Nuevo Correo*\n\n{file_info}\n*Asunto:* {subject}\n\n{analysis}"
                        telegram.send_message(message_text)
                        
                        # 5. Mark as Read
                        outlook.mark_as_read(msg_id)
                        
                        logger.info("Processing complete.")
                            
                    except Exception as e:
                        logger.error(f"Error processing message {msg_id}: {e}")
                        telegram.send_message(f"⚠️ Error processing email '{subject}': {str(e)}")
            
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
            
            # Wait before next check
            time.sleep(30)  # Check every 30 seconds

    except KeyboardInterrupt:
        logger.info("Stopping service...")
        bot_server.stop_polling()
    except Exception as e:
        logger.critical(f"Critical system error: {e}")

if __name__ == "__main__":
    main()
