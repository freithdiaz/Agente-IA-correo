import httpx
import logging
from app.config import Config

logger = logging.getLogger(__name__)

class TelegramSender:
    def __init__(self):
        self.config = Config
        self.base_url = f"https://api.telegram.org/bot{self.config.TELEGRAM_BOT_TOKEN}"

    def send_message(self, text):
        """Sends a text message to the configured Telegram chat."""
        if not self.config.TELEGRAM_BOT_TOKEN or not self.config.TELEGRAM_CHAT_ID:
            logger.warning("Telegram credentials missing. Skipping notification.")
            return

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.config.TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "Markdown"
        }
        
        try:
            response = httpx.post(url, json=payload)
            if response.status_code == 200:
                logger.info("Telegram message sent successfully.")
            elif response.status_code == 400:
                logger.warning("Markdown parsing failed. Retrying with plain text...")
                # Remove parse_mode completely for plain text
                payload.pop("parse_mode", None)
                response = httpx.post(url, json=payload)
                if response.status_code == 200:
                    logger.info("Telegram message sent successfully (Plain Text).")
                else:
                    logger.error(f"Failed to send Telegram message (Retry): {response.text}")
            else:
                logger.error(f"Failed to send Telegram message: {response.text}")
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
    
    def send_confirmation_message(self, text: str, confirmation_id: str):
        """Sends a message with inline confirmation buttons"""
        if not self.config.TELEGRAM_BOT_TOKEN or not self.config.TELEGRAM_CHAT_ID:
            logger.warning("Telegram credentials missing. Skipping notification.")
            return

        url = f"{self.base_url}/sendMessage"
        
        # Create inline keyboard with Yes/No buttons
        keyboard = {
            "inline_keyboard": [[
                {"text": "✅ Sí, corregir", "callback_data": f"confirm_{confirmation_id}"},
                {"text": "❌ No, dejar así", "callback_data": f"cancel_{confirmation_id}"}
            ]]
        }
        
        payload = {
            "chat_id": self.config.TELEGRAM_CHAT_ID,
            "text": text,
            "reply_markup": keyboard
        }
        
        try:
            response = httpx.post(url, json=payload)
            if response.status_code == 200:
                logger.info("Confirmation message sent successfully.")
            else:
                logger.error(f"Failed to send confirmation message: {response.text}")
        except Exception as e:
            logger.error(f"Error sending confirmation message: {e}")
