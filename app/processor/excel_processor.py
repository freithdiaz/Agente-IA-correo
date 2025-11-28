import pandas as pd
import os
import logging

logger = logging.getLogger(__name__)

class ExcelProcessor:
    def __init__(self):
        pass

    def process_excel(self, file_path):
        """
        Reads an Excel file and returns a summary string.
        """
        try:
            logger.info(f"Processing file: {file_path}")
            # Read the Excel file
            # Using openpyxl engine
            df = pd.read_excel(file_path, engine='openpyxl')

            # Basic stats
            num_rows, num_cols = df.shape
            columns = df.columns.tolist()
            
            # Generate a summary for the AI
            # We want to give the AI enough context without overloading it.
            # Head of the data
            head_data = df.head(5).to_string(index=False)
            
            # Basic description
            description = df.describe(include='all').to_string()

            summary = f"""
            File Analysis:
            - Rows: {num_rows}
            - Columns: {num_cols}
            - Column Names: {', '.join([str(c) for c in columns])}
            
            Sample Data (First 5 rows):
            {head_data}
            
            Statistical Description:
            {description}
            """
            
            return summary

        except Exception as e:
            logger.error(f"Error processing Excel file: {e}")
            raise e
