"""
This module contains the tool functions that the DataRunnerAgent can execute.
"""
import io
import duckdb
import pdfplumber
from tavily import TavilyClient
import json
import tiktoken
import re
from typing import List, Dict, Any, Optional, Tuple
import openai
from difflib import get_close_matches
from dataclasses import dataclass

from app.config import settings
from app.services.supabase_client import download_file_from_supabase

# DEFAULT_SUPABASE_BUCKET is no longer needed here, will use settings.SUPABASE_BUCKET_NAME

@dataclass
class CSVSchemaInfo:
    """Information about CSV file structure"""
    columns: List[str]
    data_types: Dict[str, str]
    sample_values: Dict[str, List[str]]
    row_count: int
    key_columns: Dict[str, List[str]]  # categorized columns (company, product, etc.)

@dataclass
class QueryPlan:
    """Plan for executing multiple SQL queries"""
    objective: str
    steps: List[Dict[str, str]]  # [{"description": "", "sql": "", "validation": ""}]
    expected_result_type: str

def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    """Count tokens in text using tiktoken"""
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception:
        # Fallback to rough approximation
        return len(text.split()) * 1.3

def find_best_column_match(target: str, available_columns: List[str], threshold: float = 0.6) -> Optional[str]:
    """
    Find the best matching column name using fuzzy matching.
    
    Args:
        target: Target column name to find
        available_columns: List of available column names
        threshold: Minimum similarity threshold (0.0 to 1.0)
    
    Returns:
        Best matching column name or None if no good match found
    """
    target_lower = target.lower().strip()
    
    # First, try exact match (case insensitive)
    for col in available_columns:
        if col.lower().strip() == target_lower:
            return col
    
    # Try fuzzy matching
    matches = get_close_matches(target_lower, [col.lower() for col in available_columns], n=1, cutoff=threshold)
    if matches:
        # Find the original column name
        for col in available_columns:
            if col.lower() == matches[0]:
                return col
    
    # Try partial matches for common patterns
    common_patterns = {
        'company': ['company', 'empresa', 'corporation', 'corp', 'manufacturer', 'applicant'],
        'product': ['product', 'medicamento', 'drug', 'medicine', 'brand', 'trademark'],
        'country': ['country', 'pais', 'nation', 'location'],
        'approval': ['approval', 'approved', 'authorization', 'permit', 'license'],
        'date': ['date', 'fecha', 'time', 'year', 'month'],
        'status': ['status', 'estado', 'state', 'condition']
    }
    
    target_category = None
    for category, keywords in common_patterns.items():
        if any(keyword in target_lower for keyword in keywords):
            target_category = category
            break
    
    if target_category:
        for col in available_columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in common_patterns[target_category]):
                return col
    
    return None

async def analyze_csv_schema(file_id: str) -> CSVSchemaInfo:
    """
    Analyze CSV file structure and return comprehensive schema information.
    
    Args:
        file_id: The ID/path of the CSV file in the Supabase bucket
        
    Returns:
        CSVSchemaInfo object with detailed schema analysis
    """
    try:
        csv_bytes = await download_file_from_supabase(
            bucket_name=settings.SUPABASE_BUCKET_NAME, 
            file_path_in_bucket=file_id
        )
        
        if not csv_bytes:
            raise Exception(f"Could not download CSV file '{file_id}'")
        
        import pandas as pd
        csv_file_like_object = io.BytesIO(csv_bytes)
        df = pd.read_csv(csv_file_like_object)
        
        # Basic info
        columns = list(df.columns)
        row_count = len(df)
        
        # Data types
        data_types = {}
        for col in columns:
            dtype = str(df[col].dtype)
            if dtype.startswith('int'):
                data_types[col] = 'integer'
            elif dtype.startswith('float'):
                data_types[col] = 'numeric'
            elif dtype.startswith('datetime'):
                data_types[col] = 'datetime'
            else:
                data_types[col] = 'text'
        
        # Sample values (up to 5 unique values per column)
        sample_values = {}
        for col in columns:
            unique_vals = df[col].dropna().unique()
            sample_values[col] = [str(val) for val in unique_vals[:5]]
        
        # Categorize columns by content type
        key_columns = {
            'company': [],
            'product': [],
            'country': [],
            'approval': [],
            'date': [],
            'status': [],
            'other': []
        }
        
        for col in columns:
            col_lower = col.lower()
            categorized = False
            
            # Company-related columns
            if any(keyword in col_lower for keyword in ['company', 'empresa', 'corporation', 'manufacturer', 'applicant']):
                key_columns['company'].append(col)
                categorized = True
            
            # Product-related columns
            elif any(keyword in col_lower for keyword in ['product', 'medicamento', 'drug', 'medicine', 'brand', 'trademark']):
                key_columns['product'].append(col)
                categorized = True
            
            # Country-related columns
            elif any(keyword in col_lower for keyword in ['country', 'pais', 'nation', 'location']):
                key_columns['country'].append(col)
                categorized = True
            
            # Approval-related columns
            elif any(keyword in col_lower for keyword in ['approval', 'approved', 'authorization', 'permit', 'license']):
                key_columns['approval'].append(col)
                categorized = True
            
            # Date-related columns
            elif any(keyword in col_lower for keyword in ['date', 'fecha', 'time', 'year', 'month']) or data_types[col] == 'datetime':
                key_columns['date'].append(col)
                categorized = True
            
            # Status-related columns
            elif any(keyword in col_lower for keyword in ['status', 'estado', 'state', 'condition']):
                key_columns['status'].append(col)
                categorized = True
            
            if not categorized:
                key_columns['other'].append(col)
        
        return CSVSchemaInfo(
            columns=columns,
            data_types=data_types,
            sample_values=sample_values,
            row_count=row_count,
            key_columns=key_columns
        )
        
    except Exception as e:
        raise Exception(f"Error analyzing CSV schema for '{file_id}': {str(e)}")

def create_query_plan(objective: str, schema_info: CSVSchemaInfo) -> QueryPlan:
    """
    Create a multi-step query plan based on the objective and CSV schema.
    
    Args:
        objective: The research objective/question
        schema_info: CSV schema information
        
    Returns:
        QueryPlan with step-by-step approach
    """
    objective_lower = objective.lower()
    steps = []
    
    # Step 1: Always start with schema exploration for complex questions
    if any(word in objective_lower for word in ['how many', 'count', 'companies', 'products']):
        steps.append({
            "description": "Explore CSV structure and columns",
            "sql": "SELECT column_name FROM information_schema.columns WHERE table_name = 'current_csv_table'",
            "validation": "Should return list of column names"
        })
    
    # Step 2: Data exploration based on question type
    if 'company' in objective_lower or 'companies' in objective_lower:
        company_cols = schema_info.key_columns.get('company', [])
        if company_cols:
            main_company_col = company_cols[0]
            steps.append({
                "description": f"Explore company data in column '{main_company_col}'",
                "sql": f"SELECT DISTINCT \"{main_company_col}\" FROM current_csv_table LIMIT 10",
                "validation": "Should return list of company names"
            })
    
    # Step 3: Enhanced product-specific search in MULTIPLE columns
    product_mentioned = None
    # Extract potential product names from objective
    import re
    potential_products = re.findall(r'\b[A-Z][A-Z0-9]+\b', objective)  # All-caps words likely product names
    if potential_products:
        product_mentioned = potential_products[0]
        
        product_cols = schema_info.key_columns.get('product', [])
        if product_cols:
            # Search in Brand Name column
            brand_name_col = None
            generic_name_col = None
            
            for col in schema_info.columns:
                if 'brand' in col.lower() and 'name' in col.lower():
                    brand_name_col = col
                elif 'generic' in col.lower() and 'name' in col.lower():
                    generic_name_col = col
            
            # Search in Brand Name first
            if brand_name_col:
                steps.append({
                    "description": f"Search for product '{product_mentioned}' in Brand Name column '{brand_name_col}'",
                    "sql": f"SELECT * FROM current_csv_table WHERE UPPER(\"{brand_name_col}\") LIKE '%{product_mentioned.upper()}%' LIMIT 5",
                    "validation": f"Should return rows with brand name '{product_mentioned}'"
                })
            
            # Also search in Generic Name column (critical for generic drugs!)
            if generic_name_col:
                steps.append({
                    "description": f"Search for product '{product_mentioned}' in Generic Name column '{generic_name_col}'",
                    "sql": f"SELECT * FROM current_csv_table WHERE UPPER(\"{generic_name_col}\") LIKE '%{product_mentioned.upper()}%' LIMIT 5",
                    "validation": f"Should return rows with generic name '{product_mentioned}'"
                })
            
            # If no specific columns found, use the first product column
            if not brand_name_col and not generic_name_col and product_cols:
                main_product_col = product_cols[0]
                steps.append({
                    "description": f"Search for product '{product_mentioned}' in column '{main_product_col}'",
                    "sql": f"SELECT * FROM current_csv_table WHERE UPPER(\"{main_product_col}\") LIKE '%{product_mentioned.upper()}%' LIMIT 5",
                    "validation": f"Should return rows containing '{product_mentioned}'"
                })
    
    # Step 4: Enhanced counting with multiple column search
    if 'how many companies' in objective_lower and product_mentioned:
        company_cols = schema_info.key_columns.get('company', [])
        
        if company_cols:
            main_company_col = company_cols[0]
            
            # Build comprehensive WHERE clause checking multiple columns
            where_conditions = []
            
            # Check Brand Name
            brand_name_col = None
            generic_name_col = None
            for col in schema_info.columns:
                if 'brand' in col.lower() and 'name' in col.lower():
                    brand_name_col = col
                elif 'generic' in col.lower() and 'name' in col.lower():
                    generic_name_col = col
            
            if brand_name_col:
                where_conditions.append(f"UPPER(\"{brand_name_col}\") LIKE '%{product_mentioned.upper()}%'")
            if generic_name_col:
                where_conditions.append(f"UPPER(\"{generic_name_col}\") LIKE '%{product_mentioned.upper()}%'")
            
            if where_conditions:
                combined_where = " OR ".join(where_conditions)
                steps.append({
                    "description": f"Count distinct companies that have registered {product_mentioned} (checking multiple columns)",
                    "sql": f"SELECT COUNT(DISTINCT \"{main_company_col}\") as company_count FROM current_csv_table WHERE {combined_where}",
                    "validation": f"Should return count of companies with {product_mentioned}"
                })
                
                # Also get the actual company names
                steps.append({
                    "description": f"List companies that have registered {product_mentioned} (from all relevant columns)",
                    "sql": f"SELECT DISTINCT \"{main_company_col}\" as company_name FROM current_csv_table WHERE {combined_where}",
                    "validation": f"Should return names of companies with {product_mentioned}"
                })
    
    # Determine expected result type
    if 'how many' in objective_lower or 'count' in objective_lower:
        expected_result_type = "numeric_count_with_details"
    elif 'list' in objective_lower or 'what are' in objective_lower:
        expected_result_type = "list_of_items"
    else:
        expected_result_type = "general_information"
    
    return QueryPlan(
        objective=objective,
        steps=steps,
        expected_result_type=expected_result_type
    )

def validate_query_result(step_description: str, result: str, expected_validation: str) -> Tuple[bool, str]:
    """
    Validate if a query result meets expectations.
    
    Args:
        step_description: Description of what the step should accomplish
        result: Actual result from query
        expected_validation: Expected validation criteria
        
    Returns:
        Tuple of (is_valid, feedback_message)
    """
    try:
        # Parse result if it's JSON
        if result.startswith('[') or result.startswith('{'):
            parsed_result = json.loads(result)
            
            # Empty result validation
            if not parsed_result:
                return False, f"Query returned empty result for: {step_description}"
            
            # Count validation
            if 'count' in expected_validation.lower():
                if isinstance(parsed_result, list) and len(parsed_result) == 1:
                    if any('count' in str(key).lower() for key in parsed_result[0].keys()):
                        return True, "Count query successful"
                return False, f"Expected count result, got: {type(parsed_result)}"
            
            # List validation
            if 'list' in expected_validation.lower():
                if isinstance(parsed_result, list) and len(parsed_result) > 0:
                    return True, f"List query returned {len(parsed_result)} items"
                return False, "Expected non-empty list result"
            
            return True, "Query executed successfully"
            
        # Handle error results
        elif 'error' in result.lower():
            return False, f"Query failed: {result}"
        
        # Non-JSON results
        else:
            if result.strip():
                return True, "Query returned data"
            else:
                return False, "Query returned empty result"
                
    except Exception as e:
        return False, f"Error validating result: {str(e)}"

async def execute_query_plan(file_id: str, query_plan: QueryPlan) -> Dict[str, Any]:
    """
    Execute a multi-step query plan and return comprehensive results.
    
    Args:
        file_id: CSV file identifier
        query_plan: QueryPlan object with steps to execute
        
    Returns:
        Dictionary with execution results, errors, and final answer
    """
    results = {
        'objective': query_plan.objective,
        'steps_executed': [],
        'final_answer': '',
        'success': True,
        'errors': [],
        'warnings': []
    }
    
    try:
        # Download and setup CSV
        csv_bytes = await download_file_from_supabase(
            bucket_name=settings.SUPABASE_BUCKET_NAME, 
            file_path_in_bucket=file_id
        )
        
        if not csv_bytes:
            results['success'] = False
            results['errors'].append(f"Could not download CSV file '{file_id}'")
            return results
        
        import pandas as pd
        csv_file_like_object = io.BytesIO(csv_bytes)
        df = pd.read_csv(csv_file_like_object)
        
        con = duckdb.connect(database=':memory:', read_only=False)
        con.register('current_csv_table', df)
        
        # Execute each step in the plan
        step_results = []
        
        for i, step in enumerate(query_plan.steps):
            step_result = {
                'step_number': i + 1,
                'description': step['description'],
                'sql': step['sql'],
                'result': '',
                'success': True,
                'validation_passed': True,
                'feedback': ''
            }
            
            try:
                # Execute SQL
                result_relation = con.execute(step['sql'])
                result_df = result_relation.fetchdf()
                
                if result_df.empty:
                    step_result['result'] = '[]'
                else:
                    result_dicts = result_df.to_dict(orient='records')
                    step_result['result'] = json.dumps(result_dicts, indent=2)
                
                # Validate result
                is_valid, feedback = validate_query_result(
                    step['description'], 
                    step_result['result'], 
                    step.get('validation', '')
                )
                
                step_result['validation_passed'] = is_valid
                step_result['feedback'] = feedback
                
                if not is_valid:
                    results['warnings'].append(f"Step {i+1} validation failed: {feedback}")
                
                step_results.append(step_result)
                
            except Exception as e:
                step_result['success'] = False
                step_result['result'] = f"Error: {str(e)}"
                step_result['validation_passed'] = False
                step_result['feedback'] = f"SQL execution failed: {str(e)}"
                
                results['errors'].append(f"Step {i+1} failed: {str(e)}")
                step_results.append(step_result)
                
                # Try to suggest alternative approaches
                if 'column' in str(e).lower() and 'not found' in str(e).lower():
                    # Column name issue - try to suggest alternatives
                    available_columns = list(df.columns)
                    failed_column = re.search(r'"([^"]+)"', str(e))
                    if failed_column:
                        col_name = failed_column.group(1)
                        suggested_col = find_best_column_match(col_name, available_columns)
                        if suggested_col:
                            results['warnings'].append(f"Column '{col_name}' not found. Did you mean '{suggested_col}'?")
        
        results['steps_executed'] = step_results
        
        # Generate final answer based on results
        final_answer_parts = []
        final_answer_parts.append(f"## Analysis Results for: {query_plan.objective}\n")
        
        # Add successful results
        successful_steps = [step for step in step_results if step['success'] and step['validation_passed']]
        
        if successful_steps:
            final_answer_parts.append("### Key Findings:\n")
            
            for step in successful_steps:
                final_answer_parts.append(f"**{step['description']}:**")
                
                try:
                    result_data = json.loads(step['result'])
                    if isinstance(result_data, list) and result_data:
                        if len(result_data) == 1 and 'count' in str(result_data[0]).lower():
                            # Count result
                            count_val = list(result_data[0].values())[0]
                            final_answer_parts.append(f"- Count: **{count_val}**")
                        else:
                            # List result
                            final_answer_parts.append(f"- Found {len(result_data)} records:")
                            for item in result_data[:10]:  # Show up to 10 items
                                if isinstance(item, dict):
                                    key_val = list(item.values())[0] if item.values() else str(item)
                                    final_answer_parts.append(f"  - {key_val}")
                                else:
                                    final_answer_parts.append(f"  - {item}")
                            if len(result_data) > 10:
                                final_answer_parts.append(f"  - ... and {len(result_data) - 10} more")
                    final_answer_parts.append("")
                    
                except json.JSONDecodeError:
                    final_answer_parts.append(f"- {step['result']}\n")
        
        # Add summary for count questions
        if 'how many' in query_plan.objective.lower():
            count_steps = [step for step in successful_steps if 'count' in step['description'].lower()]
            if count_steps:
                try:
                    result_data = json.loads(count_steps[0]['result'])
                    if result_data and isinstance(result_data, list):
                        count_val = list(result_data[0].values())[0]
                        final_answer_parts.append(f"### Final Answer: **{count_val}** companies")
                except:
                    pass
        
        # Add errors and warnings if any
        if results['errors']:
            final_answer_parts.append("### Issues Encountered:")
            for error in results['errors']:
                final_answer_parts.append(f"- ❌ {error}")
            final_answer_parts.append("")
        
        if results['warnings']:
            final_answer_parts.append("### Warnings:")
            for warning in results['warnings']:
                final_answer_parts.append(f"- ⚠️ {warning}")
        
        results['final_answer'] = "\n".join(final_answer_parts)
        con.close()
        
        return results
        
    except Exception as e:
        results['success'] = False
        results['errors'].append(f"Critical error in query plan execution: {str(e)}")
        results['final_answer'] = f"Error: Could not execute analysis - {str(e)}"
        return results

def chunk_text_intelligently(text: str, max_chunk_tokens: int = 3000, overlap_tokens: int = 200) -> List[str]:
    """
    Intelligently chunk text while preserving context and structure.
    Prioritizes keeping sections, paragraphs, and sentences intact.
    """
    # Split by sections (forms, chapters, etc.)
    section_patterns = [
        r'\n\s*FORM\s+\w+',  # Forms like "FORM CT-11"
        r'\n\s*Chapter\s+\w+',  # Chapters
        r'\n\s*Rule\s+\d+',  # Rules
        r'\n\s*SCHEDULE\s+\w+',  # Schedules
        r'\n\s*[A-Z\s]{10,}\n',  # All caps headers
    ]
    
    chunks = []
    current_chunk = ""
    current_tokens = 0
    
    # First try to split by major sections
    sections = re.split('|'.join(section_patterns), text)
    
    for section in sections:
        section = section.strip()
        if not section:
            continue
            
        section_tokens = count_tokens(section)
        
        # If section is small enough, add to current chunk
        if current_tokens + section_tokens <= max_chunk_tokens:
            current_chunk += "\n\n" + section if current_chunk else section
            current_tokens += section_tokens
        else:
            # Save current chunk if it has content
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            
            # If section itself is too large, split it further
            if section_tokens > max_chunk_tokens:
                # Split by paragraphs
                paragraphs = section.split('\n\n')
                current_chunk = ""
                current_tokens = 0
                
                for para in paragraphs:
                    para_tokens = count_tokens(para)
                    
                    if current_tokens + para_tokens <= max_chunk_tokens:
                        current_chunk += "\n\n" + para if current_chunk else para
                        current_tokens += para_tokens
                    else:
                        if current_chunk.strip():
                            chunks.append(current_chunk.strip())
                        
                        # If paragraph is still too large, split by sentences
                        if para_tokens > max_chunk_tokens:
                            sentences = re.split(r'(?<=[.!?])\s+', para)
                            current_chunk = ""
                            current_tokens = 0
                            
                            for sentence in sentences:
                                sent_tokens = count_tokens(sentence)
                                if current_tokens + sent_tokens <= max_chunk_tokens:
                                    current_chunk += " " + sentence if current_chunk else sentence
                                    current_tokens += sent_tokens
                                else:
                                    if current_chunk.strip():
                                        chunks.append(current_chunk.strip())
                                    current_chunk = sentence
                                    current_tokens = sent_tokens
                        else:
                            current_chunk = para
                            current_tokens = para_tokens
            else:
                current_chunk = section
                current_tokens = section_tokens
    
    # Add final chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks

def summarize_text_chunk(text: str, focus_query: str = None) -> str:
    """
    Summarize a text chunk using OpenAI API with optional focus on specific topics.
    """
    if not settings.OPENAI_API_KEY:
        # Fallback to simple truncation
        return text[:2000] + "..." if len(text) > 2000 else text
    
    try:
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        
        system_prompt = """You are an expert at summarizing regulatory and legal documents. 
        Create a concise but comprehensive summary that preserves key information, requirements, 
        timelines, processes, and specific details. Maintain the structure and important terminology."""
        
        if focus_query:
            system_prompt += f"\n\nPay special attention to information related to: {focus_query}"
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Summarize this regulatory document section:\n\n{text}"}
            ],
            max_tokens=800,  # Limit summary length
            temperature=0.1  # Low temperature for consistent, factual summaries
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Warning: Failed to summarize chunk: {e}")
        # Fallback to simple truncation
        return text[:2000] + "..." if len(text) > 2000 else text

def extract_relevant_sections(text: str, query: str = None) -> str:
    """
    Extract sections most relevant to the query using keyword matching and context.
    """
    if not query:
        return text
    
    # Convert query to keywords
    query_keywords = re.findall(r'\b\w+\b', query.lower())
    query_keywords = [kw for kw in query_keywords if len(kw) > 3]  # Filter short words
    
    # Split text into sections
    sections = re.split(r'\n\s*(?=FORM|Chapter|Rule|SCHEDULE|[A-Z\s]{10,})', text)
    
    # Score sections by relevance
    scored_sections = []
    for section in sections:
        if len(section.strip()) < 50:  # Skip very short sections
            continue
            
        section_lower = section.lower()
        score = sum(1 for keyword in query_keywords if keyword in section_lower)
        
        # Bonus for exact phrase matches
        if query.lower() in section_lower:
            score += 5
        
        # Bonus for regulatory keywords
        regulatory_keywords = ['clinical trial', 'approval', 'requirement', 'timeline', 'compliance', 
                             'safety', 'regulation', 'permission', 'licence', 'drug', 'pharmaceutical']
        score += sum(1 for keyword in regulatory_keywords if keyword in section_lower)
        
        if score > 0:
            scored_sections.append((score, section))
    
    # Sort by relevance and take top sections
    scored_sections.sort(key=lambda x: x[0], reverse=True)
    
    # Take top sections up to token limit
    selected_sections = []
    total_tokens = 0
    max_tokens = 8000  # Conservative limit
    
    for score, section in scored_sections:
        section_tokens = count_tokens(section)
        if total_tokens + section_tokens <= max_tokens:
            selected_sections.append(section)
            total_tokens += section_tokens
        else:
            break
    
    return "\n\n---\n\n".join(selected_sections) if selected_sections else text[:8000]

async def read_pdf(file_id: str, query: str = None) -> str:
    """
    Reads text content from a PDF file stored in Supabase with intelligent processing
    for large documents including chunking, summarization, and relevance filtering.

    Args:
        file_id: The ID/path of the PDF file in the Supabase bucket.
        query: Optional query to focus extraction and summarization on relevant content.

    Returns:
        A string containing the processed text from the PDF or an error message.
    """
    if not settings.SUPABASE_BUCKET_NAME:
        return "Error: Supabase bucket name is not configured in settings."

    print(f"[Tool] read_pdf attempting for file_id: {file_id}, bucket: {settings.SUPABASE_BUCKET_NAME}")
    
    try:
        pdf_bytes = await download_file_from_supabase(bucket_name=settings.SUPABASE_BUCKET_NAME, file_path_in_bucket=file_id)
        if not pdf_bytes:
            return f"Error: Could not download PDF file '{file_id}' from bucket '{settings.SUPABASE_BUCKET_NAME}'. File not found or empty."

        pdf_file_like_object = io.BytesIO(pdf_bytes)
        
        text_content = []
        try:
            with pdfplumber.open(pdf_file_like_object) as pdf:
                if not pdf.pages:
                    return f"Error: PDF file '{file_id}' contains no pages."
                
                total_pages = len(pdf.pages)
                print(f"[Tool] Processing PDF with {total_pages} pages")
                
                for page_num, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text_content.append(page_text)
                    
                    # Progress logging for large documents
                    if page_num % 10 == 0 and page_num > 0:
                        print(f"[Tool] Processed {page_num}/{total_pages} pages")
            
            if not text_content:
                return f"Warning: No text could be extracted from PDF file '{file_id}'. It might be an image-based PDF or empty."
            
            # Join all pages
            full_text = "\n\n---\n\n".join(text_content)
            total_tokens = count_tokens(full_text)
            
            print(f"[Tool] Extracted {total_tokens} tokens from PDF")
            
            # If document is small enough, return as-is
            if total_tokens <= 8000:
                return full_text
            
            print(f"[Tool] Large document detected ({total_tokens} tokens), applying intelligent processing")
            
            # Step 1: Extract relevant sections if query provided
            if query:
                print(f"[Tool] Filtering content relevant to: {query}")
                relevant_text = extract_relevant_sections(full_text, query)
                relevant_tokens = count_tokens(relevant_text)
                print(f"[Tool] Filtered to {relevant_tokens} tokens")
                
                if relevant_tokens <= 8000:
                    return f"[FILTERED CONTENT - {relevant_tokens} tokens from {total_tokens} total]\n\n{relevant_text}"
                
                # Use relevant text for further processing
                full_text = relevant_text
            
            # Step 2: Intelligent chunking
            print(f"[Tool] Chunking document for processing")
            chunks = chunk_text_intelligently(full_text, max_chunk_tokens=3000)
            print(f"[Tool] Created {len(chunks)} chunks")
            
            # Step 3: Summarize chunks
            summarized_chunks = []
            for i, chunk in enumerate(chunks):
                print(f"[Tool] Summarizing chunk {i+1}/{len(chunks)}")
                summary = summarize_text_chunk(chunk, query)
                summarized_chunks.append(f"[SECTION {i+1}]\n{summary}")
            
            # Combine summaries
            final_result = "\n\n" + "="*50 + "\n\n".join(summarized_chunks)
            final_tokens = count_tokens(final_result)
            
            print(f"[Tool] Final processed content: {final_tokens} tokens")
            
            # Add processing note
            processing_note = f"[PROCESSED LARGE PDF - Original: {total_tokens} tokens, Processed: {final_tokens} tokens from {len(chunks)} sections of '{file_id}']\n\n"
            
            return processing_note + final_result
            
        except pdfplumber.pdfminer.pdfdocument.PDFEncryptionError:
            return f"Error: PDF file '{file_id}' is encrypted and cannot be opened."
        except Exception as e:
            # Catch other pdfplumber or general errors during PDF processing
            return f"Error processing PDF file '{file_id}': {str(e)}"
            
    except Exception as e:
        return f"Error in read_pdf for file '{file_id}': {str(e)}"

async def query_csv(file_id: str, sql_query: str = None, objective: str = None) -> str:
    """
    Enhanced CSV querying with intelligent schema discovery, multi-step planning, and validation.
    
    Args:
        file_id: The ID/path of the CSV file in the Supabase bucket.
        sql_query: Optional SQL query (for simple queries)
        objective: Optional natural language objective (for complex analysis)

    Returns:
        A comprehensive string containing query results, analysis, and insights.
    """
    if not settings.SUPABASE_BUCKET_NAME:
        return "Error: Supabase bucket name is not configured in settings."
    
    print(f"[Tool] Enhanced query_csv for file_id: {file_id}, bucket: {settings.SUPABASE_BUCKET_NAME}")
    
    try:
        # If objective is provided, use intelligent planning approach
        if objective and not sql_query:
            print(f"[Tool] Using intelligent planning for objective: {objective}")
            
            # Step 1: Analyze CSV schema
            try:
                schema_info = await analyze_csv_schema(file_id)
                print(f"[Tool] Schema analysis complete: {len(schema_info.columns)} columns, {schema_info.row_count} rows")
            except Exception as e:
                return f"Error analyzing CSV schema: {str(e)}"
            
            # Step 2: Create query plan
            query_plan = create_query_plan(objective, schema_info)
            print(f"[Tool] Created query plan with {len(query_plan.steps)} steps")
            
            # Step 3: Execute query plan
            results = await execute_query_plan(file_id, query_plan)
            
            # Format comprehensive results
            output_parts = []
            output_parts.append(f"## Enhanced CSV Analysis Results")
            output_parts.append(f"**File:** {file_id}")
            output_parts.append(f"**Objective:** {objective}")
            output_parts.append(f"**Schema:** {len(schema_info.columns)} columns, {schema_info.row_count} rows")
            output_parts.append("")
            
            # Add schema information
            output_parts.append("### 📊 CSV Schema Information:")
            output_parts.append("**Columns by Category:**")
            for category, cols in schema_info.key_columns.items():
                if cols:
                    output_parts.append(f"- **{category.title()}:** {', '.join(cols)}")
            output_parts.append("")
            
            # Add execution details
            if results['steps_executed']:
                output_parts.append("### 🔍 Query Execution Steps:")
                for step in results['steps_executed']:
                    status_icon = "✅" if step['success'] and step['validation_passed'] else "❌"
                    output_parts.append(f"{status_icon} **Step {step['step_number']}:** {step['description']}")
                    if not step['success']:
                        output_parts.append(f"   Error: {step['feedback']}")
                output_parts.append("")
            
            # Add the main results
            output_parts.append(results['final_answer'])
            
            # Add technical details
            if results['errors'] or results['warnings']:
                output_parts.append("\n### 🔧 Technical Details:")
                if results['errors']:
                    output_parts.append("**Errors:**")
                    for error in results['errors']:
                        output_parts.append(f"- {error}")
                if results['warnings']:
                    output_parts.append("**Warnings:**")
                    for warning in results['warnings']:
                        output_parts.append(f"- {warning}")
            
            return "\n".join(output_parts)
        
        # Otherwise, use traditional single-query approach with enhanced error handling
        else:
            print(f"[Tool] Using traditional SQL query approach")
            
            if not sql_query:
                return "Error: Either 'sql_query' or 'objective' must be provided."
            
            # First, analyze schema for better error messages
            try:
                schema_info = await analyze_csv_schema(file_id)
                available_columns = schema_info.columns
            except Exception as e:
                print(f"[Tool] Warning: Could not analyze schema: {e}")
                available_columns = []
            
            # Download and setup CSV
            csv_bytes = await download_file_from_supabase(
                bucket_name=settings.SUPABASE_BUCKET_NAME, 
                file_path_in_bucket=file_id
            )
            
            if not csv_bytes:
                return f"Error: Could not download CSV file '{file_id}' from bucket '{settings.SUPABASE_BUCKET_NAME}'. File not found or empty."

            csv_file_like_object = io.BytesIO(csv_bytes)
            con = duckdb.connect(database=':memory:', read_only=False)
            
            try:
                import pandas as pd
                df = pd.read_csv(csv_file_like_object)
                if df.empty:
                    return json.dumps([])  # Return empty JSON list
                con.register('current_csv_table', df)
                
                # Update available_columns if we didn't get them from schema analysis
                if not available_columns:
                    available_columns = list(df.columns)
                    
            except ImportError:
                return "Error: pandas library is required for query_csv but is not installed."
            except pd.errors.EmptyDataError:
                return f"Error: CSV file '{file_id}' is empty or contains no data."
            except pd.errors.ParserError as pe:
                return f"Error: Could not parse CSV file '{file_id}'. Invalid format. Details: {pe}"
            except Exception as e:
                return f"Error reading CSV '{file_id}' into DataFrame: {str(e)}"

            # Validate SQL query references
            if "FROM current_csv_table" not in sql_query.upper() and f"FROM '{file_id}'" not in sql_query:
                print(f"[Tool] Warning: SQL query may not reference the correct table")
            
            try:
                result_relation = con.execute(sql_query)
                result_df = result_relation.fetchdf()
                
                if result_df.empty:
                    return json.dumps([])
                
                result_dicts = result_df.to_dict(orient='records')
                
                # Add helpful context to results
                output_parts = []
                output_parts.append(f"## CSV Query Results")
                output_parts.append(f"**File:** {file_id} ({len(df)} rows, {len(df.columns)} columns)")
                output_parts.append(f"**Query:** `{sql_query}`")
                output_parts.append(f"**Results:** {len(result_dicts)} records found")
                output_parts.append("")
                output_parts.append("### Data:")
                output_parts.append("```json")
                output_parts.append(json.dumps(result_dicts, indent=2))
                output_parts.append("```")
                
                if available_columns:
                    output_parts.append(f"\n**Available Columns:** {', '.join(available_columns)}")
                
                return "\n".join(output_parts)
                
            except duckdb.Error as de:
                error_msg = str(de)
                
                # Enhanced error recovery with column suggestions
                if 'column' in error_msg.lower() and available_columns:
                    # Try to extract the problematic column name
                    import re
                    column_match = re.search(r'"([^"]+)"', error_msg)
                    if column_match:
                        failed_column = column_match.group(1)
                        suggested_column = find_best_column_match(failed_column, available_columns)
                        
                        if suggested_column:
                            suggestion_msg = f"\n\n💡 **Suggestion:** Column '{failed_column}' not found. Did you mean '{suggested_column}'?"
                            suggestion_msg += f"\n\n**Available columns:** {', '.join(available_columns)}"
                            return f"DuckDB Error: {error_msg}{suggestion_msg}"
                
                return f"DuckDB Error executing SQL query '{sql_query}' on file '{file_id}': {error_msg}\n\n**Available columns:** {', '.join(available_columns) if available_columns else 'Unknown'}"
                
            except Exception as e:
                return f"Error executing SQL query '{sql_query}' on file '{file_id}': {str(e)}"
                
            finally:
                con.close()
            
    except Exception as e:
        return f"Error in query_csv for file '{file_id}': {str(e)}"

def web_search(query: str, max_results: int = 5) -> str:
    """
    Performs a web search using the Tavily API.

    Args:
        query: The search query.
        max_results: The maximum number of search results to return.

    Returns:
        A string containing the formatted search results or an error message.
    """
    print(f"[Tool] web_search attempting for query: '{query}'")

    if not settings.TAVILY_API_KEY:
        return "Error: Tavily API key not configured. Please set TAVILY_API_KEY in your environment."

    try:
        tavily_client = TavilyClient(api_key=settings.TAVILY_API_KEY)
        
        # Using search_depth="advanced" for potentially more thorough results
        # Tavily search returns a dictionary, typically with a "results" key containing a list of sources
        response = tavily_client.search(query=query, search_depth="advanced", max_results=max_results)
        
        results = response.get("results", [])
        
        if not results:
            return f"No web search results found for query: '{query}'"
        
        # Format results into a readable string
        formatted_results = []
        for i, result in enumerate(results):
            formatted_results.append(
                f"Result {i+1}:\n" \
                f"  Title: {result.get('title', 'N/A')}\n" \
                f"  URL: {result.get('url', 'N/A')}\n" \
                f"  Content Snippet: {result.get('content', 'N/A')[:500]}...\n" # Limiting content snippet length
            )
        return "\n---\n".join(formatted_results)
        
    except Exception as e:
        return f"Error during Tavily web search for query '{query}': {str(e)}"

# Example for direct testing of these functions (optional)
if __name__ == '__main__':
    print("Testing tool function stubs...")
    # Note: To test query_csv and read_pdf properly, you'd need Supabase connection
    # and files uploaded. For web_search, you need a TAVILY_API_KEY in your .env
    
    # Create a dummy .env if it doesn't exist for simple Tavily test
    if not settings.TAVILY_API_KEY:
        print("TAVILY_API_KEY not found in environment. Web search test will show error.")
    if not settings.SUPABASE_BUCKET_NAME:
        print("SUPABASE_BUCKET_NAME not found. query_csv and read_pdf tests will show error if they were to run fully.")

    # print(f"Calling query_csv: {query_csv('test.csv', 'SELECT * FROM test')}") # Needs asyncio.run for async
    # print(f"Calling read_pdf: {read_pdf('test.pdf')}") # Needs asyncio.run for async
    print(f"Calling web_search: {web_search('latest AI advancements')}") 