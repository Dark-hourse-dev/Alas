"""
ALAS Data Agent — Handles complex document processing and database queries (Phase 4).

Allows ALAS to natively read PDFs, Word Documents, Excel files, and directly query SQL databases.
"""
import os
import logging
import pandas as pd
from sqlalchemy import create_engine, text

logger = logging.getLogger("alas.tools.data")


def process_document(file_path: str) -> str:
    """Extract text/data from PDF, DOCX, CSV, or Excel files."""
    if not os.path.exists(file_path):
        return f"Error: File not found at {file_path}"
        
    ext = file_path.split('.')[-1].lower()
    
    try:
        if ext == 'pdf':
            import PyPDF2
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                extracted_text = ""
                for page in reader.pages:
                    extracted_text += page.extract_text() + "\n"
                
                # Truncate if massive to protect context window
                if len(extracted_text) > 15000:
                    return extracted_text[:15000] + "\n\n...[TRUNCATED FOR LENGTH]..."
                return extracted_text
                
        elif ext in ['docx', 'doc']:
            import docx
            doc = docx.Document(file_path)
            text_content = "\n".join([para.text for para in doc.paragraphs])
            if len(text_content) > 15000:
                return text_content[:15000] + "\n\n...[TRUNCATED FOR LENGTH]..."
            return text_content
            
        elif ext in ['xlsx', 'xls']:
            # Read all sheets, return markdown of first 50 rows of each
            xls = pd.ExcelFile(file_path)
            output = []
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet_name)
                output.append(f"### Sheet: {sheet_name}")
                output.append(df.head(50).to_markdown(index=False))
            return "\n\n".join(output)
            
        elif ext == 'csv':
            df = pd.read_csv(file_path)
            return f"### CSV Preview (First 50 rows)\n{df.head(50).to_markdown(index=False)}"
            
        else:
            return f"Error: Unsupported file format '{ext}'. Supported: pdf, docx, xlsx, csv."
            
    except Exception as e:
        logger.error(f"Document processing failed: {e}", exc_info=True)
        return f"Failed to process document {file_path}: {e}"


def query_database(db_uri: str, query: str) -> str:
    """Execute a read-only SQL query against a database and return markdown."""
    try:
        # Strict safety check - read only queries
        unsafe_keywords = ['insert', 'update', 'delete', 'drop', 'alter', 'truncate', 'grant', 'revoke']
        query_lower = query.lower()
        if any(f" {kw} " in f" {query_lower} " or query_lower.startswith(f"{kw} ") for kw in unsafe_keywords):
            return "⛔ PERMISSION DENIED: Only SELECT queries are permitted for safety. Database is read-only."
            
        engine = create_engine(db_uri)
        with engine.connect() as conn:
            result = conn.execute(text(query))
            rows = result.fetchmany(100) # Limit to 100 rows to save context space
            
            if not rows:
                return "Query executed successfully but returned 0 rows."
                
            # Convert to pandas dataframe to easily generate markdown table
            columns = result.keys()
            df = pd.DataFrame(rows, columns=columns)
            return f"### Query Results (Max 100 rows)\n{df.to_markdown(index=False)}"
            
    except Exception as e:
        logger.error(f"Database query failed: {e}", exc_info=True)
        return f"Database query failed: {e}"
