"""
Simple Telegram Bot Server
Handles callback queries from inline buttons
"""
import httpx
import logging
from app.config import Config
from app.telegram.confirmation_handler import confirmation_handler
import time
import threading

logger = logging.getLogger(__name__)

class TelegramBotServer:
    """Polls Telegram for updates and handles callbacks"""
    
    def __init__(self):
        self.config = Config
        self.base_url = f"https://api.telegram.org/bot{self.config.TELEGRAM_BOT_TOKEN}"
        self.last_update_id = 0
        self.running = False
    
    def start_polling(self):
        """Start polling for updates in background thread"""
        if self.running:
            return
        
        self.running = True
        thread = threading.Thread(target=self._poll_loop, daemon=True)
        thread.start()
        logger.info("Telegram bot polling started")
    
    def stop_polling(self):
        """Stop polling"""
        self.running = False
        logger.info("Telegram bot polling stopped")
    
    def _poll_loop(self):
        """Main polling loop"""
        while self.running:
            try:
                self._poll_once()
                time.sleep(1)  # Poll every second
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                time.sleep(5)  # Wait longer on error
    
    def _poll_once(self):
        """Poll for updates once"""
        try:
            url = f"{self.base_url}/getUpdates"
            params = {
                "offset": self.last_update_id + 1,
                "timeout": 30
            }
            
            response = httpx.get(url, params=params, timeout=35)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    updates = data.get("result", [])
                    for update in updates:
                        self._handle_update(update)
                        self.last_update_id = update["update_id"]
            elif response.status_code == 409:
                logger.warning("Telegram conflict: Another instance is running. Waiting 10s...")
                time.sleep(10)
        except Exception as e:
            logger.error(f"Error polling updates: {e}")
    
    def _handle_update(self, update: dict):
        """Handle a single update"""
        # Handle callback queries (button presses)
        if "callback_query" in update:
            callback = update["callback_query"]
            callback_data = callback.get("data", "")
            
            if callback_data.startswith("confirm_"):
                confirmation_id = callback_data.replace("confirm_", "")
                self._handle_confirmation(confirmation_id, True, callback)
            elif callback_data.startswith("cancel_"):
                confirmation_id = callback_data.replace("cancel_", "")
                self._handle_confirmation(confirmation_id, False, callback)
    
    def _handle_confirmation(self, confirmation_id: str, confirmed: bool, callback: dict):
        """Handle confirmation response"""
        result = confirmation_handler.handle_response(confirmation_id, confirmed)
        
        # Answer callback query
        try:
            answer_url = f"{self.base_url}/answerCallbackQuery"
            answer_payload = {
                "callback_query_id": callback["id"],
                "text": "✅ Procesando..." if confirmed else "❌ Cancelado"
            }
            httpx.post(answer_url, json=answer_payload)
            
            # Send result message
            if "error" in result:
                message = f"❌ Error: {result['error']}"
            elif result.get("cancelled"):
                message = "❌ Operación cancelada"
            elif "result" in result and "file_path" in result["result"]:
                message = f"✅ Archivo editado y guardado:\n\n📁 {result['result']['file_path']}"
            else:
                message = "✅ Operación completada"
            
            # Send message to chat
            from app.telegram.telegram_sender import TelegramSender
            sender = TelegramSender()
            sender.send_message(message)
            
        except Exception as e:
            logger.error(f"Error handling confirmation: {e}")

# Global instance
bot_server = TelegramBotServer()
