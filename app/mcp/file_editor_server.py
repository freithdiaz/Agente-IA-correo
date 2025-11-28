"""
MCP Server for File Editing Operations
Provides tools for analyzing and editing Excel/CSV files
"""
import pandas as pd
import os
import logging
from datetime import datetime
from typing import Dict, List, Any
import json

logger = logging.getLogger(__name__)

class FileEditorServer:
    """MCP Server that provides file editing capabilities"""
    
    def __init__(self):
        self.tools = {
            "analyze_excel": self.analyze_excel,
            "edit_excel": self.edit_excel,
            "save_file": self.save_file
        }
    
    def analyze_excel(self, file_path: str) -> Dict[str, Any]:
        """
        Analyzes an Excel/CSV file and detects potential issues
        
        Returns:
            {
                "issues": [...],
                "suggestions": [...],
                "needs_editing": bool
            }
        """
        try:
            # Read file
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            
            issues = []
            suggestions = []
            
            # Check column names
            for col in df.columns:
                if ' ' in str(col) or str(col).strip() != str(col):
                    issues.append(f"Columna '{col}' tiene espacios o formato inconsistente")
                    suggestions.append({
                        "type": "rename_column",
                        "column": col,
                        "new_name": str(col).strip().replace(' ', '_')
                    })
            
            # Check for null values
            null_counts = df.isnull().sum()
            for col, count in null_counts.items():
                if count > 0:
                    issues.append(f"Columna '{col}' tiene {count} valores nulos")
                    suggestions.append({
                        "type": "fill_nulls",
                        "column": col,
                        "count": int(count)
                    })
            
            # Check date columns
            for col in df.columns:
                if 'fecha' in str(col).lower() or 'date' in str(col).lower():
                    # Try to detect inconsistent date formats
                    sample = df[col].dropna().head(10)
                    if len(sample) > 0:
                        issues.append(f"Columna de fecha '{col}' puede tener formato inconsistente")
                        suggestions.append({
                            "type": "standardize_dates",
                            "column": col
                        })
            
            return {
                "issues": issues,
                "suggestions": suggestions,
                "needs_editing": len(issues) > 0,
                "row_count": len(df),
                "column_count": len(df.columns)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing file: {e}")
            return {
                "issues": [f"Error al analizar: {str(e)}"],
                "suggestions": [],
                "needs_editing": False
            }
    
    def edit_excel(self, file_path: str, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Applies editing operations to an Excel/CSV file
        
        Args:
            file_path: Path to file
            operations: List of operations to apply
                [
                    {"type": "rename_column", "column": "old", "new_name": "new"},
                    {"type": "fill_nulls", "column": "col", "value": 0},
                    {"type": "standardize_dates", "column": "fecha"}
                ]
        
        Returns:
            {
                "success": bool,
                "operations_applied": int,
                "dataframe": DataFrame (in memory)
            }
        """
        try:
            # Read file
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            
            operations_applied = 0
            
            for op in operations:
                try:
                    if op["type"] == "rename_column":
                        df.rename(columns={op["column"]: op["new_name"]}, inplace=True)
                        operations_applied += 1
                        
                    elif op["type"] == "fill_nulls":
                        value = op.get("value", 0)
                        df[op["column"]].fillna(value, inplace=True)
                        operations_applied += 1
                        
                    elif op["type"] == "standardize_dates":
                        df[op["column"]] = pd.to_datetime(df[op["column"]], errors='coerce')
                        operations_applied += 1
                        
                except Exception as e:
                    logger.warning(f"Failed to apply operation {op}: {e}")
            
            return {
                "success": True,
                "operations_applied": operations_applied,
                "dataframe": df
            }
            
        except Exception as e:
            logger.error(f"Error editing file: {e}")
            return {
                "success": False,
                "operations_applied": 0,
                "error": str(e)
            }
    
    def save_file(self, dataframe: pd.DataFrame, original_path: str, suffix: str = "_editado") -> str:
        """
        Saves edited DataFrame to a new file
        
        Returns:
            Path to saved file
        """
        try:
            # Generate new filename
            base_dir = os.path.dirname(original_path)
            base_name = os.path.basename(original_path)
            name, ext = os.path.splitext(base_name)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_name = f"{name}{suffix}_{timestamp}{ext}"
            new_path = os.path.join(base_dir, new_name)
            
            # Save based on extension
            if ext == '.csv':
                dataframe.to_csv(new_path, index=False)
            else:
                dataframe.to_excel(new_path, index=False)
            
            logger.info(f"File saved: {new_path}")
            return new_path
            
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            raise
    
    def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """Call a tool by name with parameters"""
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        return self.tools[tool_name](**params)
