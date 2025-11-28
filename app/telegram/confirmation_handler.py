"""
Telegram Confirmation Handler
Manages user confirmations for file editing operations via inline buttons
"""
import logging
from typing import Dict, Callable, Any
import uuid
import time

logger = logging.getLogger(__name__)

class ConfirmationHandler:
    """Handles confirmation requests via Telegram inline buttons"""
    
    def __init__(self):
        # Store pending confirmations: {confirmation_id: {data, callback, timestamp}}
        self.pending_confirmations: Dict[str, Dict[str, Any]] = {}
        self.timeout_seconds = 300  # 5 minutes
    
    def create_confirmation(self, 
                          message: str, 
                          data: Dict[str, Any],
                          on_confirm: Callable = None,
                          on_cancel: Callable = None) -> str:
        """
        Creates a confirmation request
        
        Args:
            message: Message to show user
            data: Data to pass to callbacks
            on_confirm: Function to call if user confirms
            on_cancel: Function to call if user cancels
            
        Returns:
            confirmation_id
        """
        confirmation_id = str(uuid.uuid4())[:8]
        
        self.pending_confirmations[confirmation_id] = {
            "message": message,
            "data": data,
            "on_confirm": on_confirm,
            "on_cancel": on_cancel,
            "timestamp": time.time()
        }
        
        logger.info(f"Created confirmation {confirmation_id}")
        return confirmation_id
    
    def handle_response(self, confirmation_id: str, confirmed: bool) -> Dict[str, Any]:
        """
        Handles user response to confirmation
        
        Returns:
            Result from callback or error
        """
        if confirmation_id not in self.pending_confirmations:
            return {"error": "Confirmación no encontrada o expirada"}
        
        conf = self.pending_confirmations.pop(confirmation_id)
        
        # Check timeout
        if time.time() - conf["timestamp"] > self.timeout_seconds:
            return {"error": "Confirmación expirada"}
        
        # Call appropriate callback
        if confirmed and conf["on_confirm"]:
            try:
                result = conf["on_confirm"](conf["data"])
                return {"success": True, "result": result}
            except Exception as e:
                logger.error(f"Error in confirm callback: {e}")
                return {"error": str(e)}
        elif not confirmed and conf["on_cancel"]:
            try:
                result = conf["on_cancel"](conf["data"])
                return {"success": True, "result": result, "cancelled": True}
            except Exception as e:
                logger.error(f"Error in cancel callback: {e}")
                return {"error": str(e)}
        
        return {"success": True, "cancelled": not confirmed}
    
    def cleanup_expired(self):
        """Remove expired confirmations"""
        current_time = time.time()
        expired = [
            cid for cid, conf in self.pending_confirmations.items()
            if current_time - conf["timestamp"] > self.timeout_seconds
        ]
        
        for cid in expired:
            del self.pending_confirmations[cid]
            logger.info(f"Removed expired confirmation {cid}")
    
    def format_confirmation_message(self, confirmation_id: str, issues: list, suggestions: list) -> str:
        """
        Formats a confirmation message for Telegram
        
        Returns:
            Formatted message string
        """
        message = "📊 **Análisis de Archivo Completado**\n\n"
        message += "**Problemas detectados:**\n"
        
        for i, issue in enumerate(issues[:5], 1):  # Limit to 5
            message += f"{i}. {issue}\n"
        
        if len(issues) > 5:
            message += f"... y {len(issues) - 5} más\n"
        
        message += "\n¿Deseas que corrija estos problemas automáticamente?\n"
        message += f"\n_ID: {confirmation_id}_"
        
        return message

# Global instance
confirmation_handler = ConfirmationHandler()
