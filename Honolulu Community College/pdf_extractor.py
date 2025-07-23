#!/usr/bin/env python3
"""
Script to extract course data from Maui courses PDF using Gemini LLM
with intelligent parsing and validation.
"""

import json
import os
import google.generativeai as genai
from datetime import datetime
import time
import re

# Configure Gemini API (you'll need to set your API key)
# Set your API key as an environment variable: export GOOGLE_API_KEY="your_api_key_here"
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))

def extract_text_from_pdf(pdf_path):
    """
    Extract text from PDF file using basic text extraction.
    Falls back to simple file reading if PDF libraries aren't available.
    """
    try:
        # Try to import and use PyMuPDF
        import fitz
        pdf_document = fitz.open(pdf_path)
        pages_text = []
        
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            text = page.get_text()
            pages_text.append({
                'page_number': page_num + 1,
                'text': text
            })
        
        pdf_document.close()
        return pages_text
        
    except ImportError:
        try:
            # Try to import and use pdfplumber
            import pdfplumber
            pages_text = []
            
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    pages_text.append({
                        'page_number': page_num,
                        'text': text if text else ""
                    })
            
            return pages_text
            
        except ImportError:
            print("❌ Error: Neither PyMuPDF nor pdfplumber is installed.")
            print("Please install one of them: pip install PyMuPDF or pip install pdfplumber")
            return None
    except Exception as e:
        print(f"❌ Error extracting text from PDF: {e}")
        return None

def create_gemini_prompt(page_text, context_pages, recent_courses, overlap_courses=None):
    """Create a comprehensive prompt for Gemini to extract course information with overlap handling"""
    
    context_text = ""
    if context_pages:
        context_text = "\n\nCONTEXT FROM PREVIOUS PAGES:\n"
        # Debug: Check what type context_pages is
        print(f"   DEBUG: context_pages type: {type(context_pages)}, length: {len(context_pages) if hasattr(context_pages, '__len__') else 'N/A'}")
        for i, page in enumerate(context_pages, 1):
            # Debug: Check what type each page is
            print(f"   DEBUG: page {i} type: {type(page)}")
            if isinstance(page, str):
                context_text += f"Page {i}: {page[:500]}...\n"
            else:
                context_text += f"Page {i}: {str(page)[:500]}...\n"
    
    recent_courses_text = ""
    if recent_courses:
        recent_courses_text = "\n\nRECENTLY EXTRACTED COURSES (for reference):\n"
        for course in recent_courses[-5:]:
            recent_courses_text += f"- {course.get('course_prefix', 'N/A')} {course.get('course_number', 'N/A')}: {course.get('course_title', 'N/A')}\n"
    
    overlap_text = ""
    if overlap_courses:
        overlap_text = "\n\nOVERLAP COURSES FROM PREVIOUS PAGE (check for continuation/completion):\n"
        for course in overlap_courses:
            overlap_text += f"- {course.get('course_prefix', 'N/A')} {course.get('course_number', 'N/A')}: {course.get('course_title', 'N/A')}\n"
            overlap_text += f"  Description: {course.get('course_desc', 'N/A')[:200]}...\n"
    
    prompt = f"""You are an expert course catalog parser. Extract ALL course information from the following page text.

IMPORTANT INSTRUCTIONS:
1. Extract EVERY course found on this page
2. Each course should have: course_prefix, course_number, course_title, course_desc, num_units, dept_name
3. Set inst_ipeds to "141839" for all courses
4. Include metadata like prerequisites, lecture hours, lab hours in the metadata field
5. If any field is unclear, use context from previous pages and courses
6. OVERLAP HANDLING: If you see courses from the overlap section that continue or are completed on this page, UPDATE them with complete information rather than creating duplicates
7. DO NOT create duplicate courses - if a course appears in overlap, only include it if you're updating/completing it
8. Return ONLY valid JSON array of course objects
9. If no courses found, return empty array []

PAGE TEXT TO ANALYZE:
{page_text}
{context_text}
{recent_courses_text}
{overlap_text}

Return JSON array of courses:"""
    
    return prompt

def validate_and_fix_courses(courses_json, context_pages=None, recent_courses=None):
    """
    Use Gemini to validate and fix any null/unknown values in extracted courses.
    """
    if not courses_json:
        return courses_json
    
    # Check for null/unknown values
    needs_fixing = False
    for course in courses_json:
        for key, value in course.items():
            if value is None or value == "" or str(value).lower() in ["unknown", "null", "n/a"]:
                needs_fixing = True
                break
        if needs_fixing:
            break
    
    if not needs_fixing:
        return courses_json
    
    print("   🔧 Fixing null/unknown values...")
    
    prompt = f"""
The following course data has some null, empty, or unknown values. Please fix these by:
1. Using context from previous pages and recent courses
2. Making reasonable inferences based on course patterns
3. Using standard academic conventions
4. Ensuring all required fields are properly filled

COURSE DATA TO FIX:
{json.dumps(courses_json, indent=2)}
"""

    if context_pages:
        prompt += f"""

CONTEXT FROM PREVIOUS PAGES:
{chr(10).join([f"Page {p['page_number']}: {p['text'][:300]}..." for p in context_pages[-3:]])}
"""

    if recent_courses:
        prompt += f"""

RECENT COURSES FOR REFERENCE:
{json.dumps(recent_courses[-5:], indent=2)}
"""

    prompt += """

Return ONLY the corrected JSON array with all null/unknown values fixed. No additional text.
"""

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        # Extract JSON from response
        response_text = response.text.strip()
        if response_text.startswith('```json'):
            response_text = response_text[7:-3].strip()
        elif response_text.startswith('```'):
            response_text = response_text[3:-3].strip()
        
        fixed_courses = json.loads(response_text)
        return fixed_courses
        
    except Exception as e:
        print(f"   ⚠️ Warning: Could not fix courses - {e}")
        return courses_json

def extract_courses_from_page(page_text, context_pages=None, recent_courses=None, overlap_courses=None, max_retries=3):
    """Extract courses from a single page using Gemini LLM with overlap handling"""
    
    for attempt in range(max_retries):
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = create_gemini_prompt(page_text, context_pages, recent_courses, overlap_courses)
            
            response = model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Clean up response text
            if response_text.startswith('```json'):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith('```'):
                response_text = response_text[3:-3].strip()
            
            # Parse JSON
            courses = json.loads(response_text)
            
            if not isinstance(courses, list):
                courses = [courses] if courses else []
            
            # Validate and fix courses
            courses = validate_and_fix_courses(courses, context_pages, recent_courses)
            
            print(f"   ✅ Extracted {len(courses)} courses")
            return courses
            
        except json.JSONDecodeError as e:
            print(f"   ⚠️ JSON parsing error (attempt {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                print(f"   ❌ Failed to parse JSON after {max_retries} attempts")
                return []
            time.sleep(1)
            
        except Exception as e:
            print(f"   ⚠️ Error processing page (attempt {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                print(f"   ❌ Failed to process page after {max_retries} attempts")
                return []
            time.sleep(2)
    
    return []

def deduplicate_courses(courses):
    """Remove duplicate courses based on course_prefix and course_number"""
    seen = set()
    unique_courses = []
    
    for course in courses:
        course_key = f"{course.get('course_prefix', '')}-{course.get('course_number', '')}"
        if course_key not in seen:
            seen.add(course_key)
            unique_courses.append(course)
        else:
            print(f"   🔄 Skipping duplicate: {course_key}")
    
    return unique_courses

def save_incremental_results(all_courses, pdf_path, output_path, current_page, total_pages):
    """Save current extraction results incrementally"""
    output_data = {
        "metadata": {
            "source_file": os.path.basename(pdf_path),
            "total_pages": total_pages,
            "pages_processed": current_page,
            "total_courses": len(all_courses),
            "extraction_timestamp": datetime.now().isoformat(),
            "extractor": "Gemini LLM",
            "model": "gemini-1.5-flash",
            "status": "in_progress" if current_page < total_pages else "complete"
        },
        "courses": all_courses
    }
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"   💾 Progress saved: {len(all_courses)} courses from {current_page}/{total_pages} pages")
        return True
    except Exception as e:
        print(f"   ⚠️ Error saving progress: {e}")
        return False

def extract_courses_from_pdf(pdf_path, output_path):
    """
    Extract course information from PDF using Gemini LLM.
    """
    print(f"🚀 Starting Gemini-powered course extraction...")
    
    # Check for API key
    if not os.getenv('GOOGLE_API_KEY'):
        print("❌ Error: GOOGLE_API_KEY environment variable not set")
        print("Please set your Gemini API key: export GOOGLE_API_KEY='your_api_key_here'")
        return False
    
    print(f"📄 Extracting text from PDF: {pdf_path}")
    
    # Extract text from PDF
    pages_text = extract_text_from_pdf(pdf_path)
    if not pages_text:
        print("❌ Failed to extract text from PDF")
        return False
    
    print(f"📊 Found {len(pages_text)} pages in PDF")
    
    all_courses = []
    context_pages = []  # Store last 3 pages for context
    recent_courses = []  # Store last 5 courses for context
    
    for i, page_text in enumerate(pages_text, 1):
        print(f"\n📖 Processing page {i}/{len(pages_text)}...")
        
        # Get overlap courses (last 2 courses from previous page)
        overlap_courses = all_courses[-2:] if len(all_courses) >= 2 else None
        if overlap_courses:
            print(f"   🔄 Using {len(overlap_courses)} overlap courses for context")
        
        # Extract courses from current page with overlap context
        print(f"   🤖 Processing with Gemini...")
        
        # Get the actual sliced lists, not slice objects
        context_for_page = context_pages[-3:] if context_pages else []
        recent_for_page = recent_courses[-5:] if recent_courses else []
        
        courses = extract_courses_from_page(
            page_text, 
            context_for_page,     # Last 3 pages
            recent_for_page,      # Last 5 courses
            overlap_courses       # Last 2 courses for overlap handling
        )
        
        if courses:
            print(f"   ✅ Extracted {len(courses)} courses from page {i}")
            
            # Add new courses to collection
            all_courses.extend(courses)
            
            # Deduplicate all courses to prevent duplicates
            all_courses = deduplicate_courses(all_courses)
            
            # Update recent courses for context
            recent_courses.extend(courses)
        else:
            print(f"   ℹ️ No courses found on page {i}")
        
        # Update context
        context_pages.append(page_text)
        
        # Keep only last 3 pages and 5 courses for context
        if len(context_pages) > 3:
            context_pages = context_pages[-3:]
        if len(recent_courses) > 5:
            recent_courses = recent_courses[-5:]
        
        # Save progress after each page
        save_incremental_results(all_courses, pdf_path, output_path, i, len(pages_text))
    
    # Final validation and cleanup
    print(f"\n🔍 Validating and cleaning {len(all_courses)} extracted courses...")
    validated_courses = []
    
    for course in all_courses:
        if validate_and_fix_course(course):
            validated_courses.append(course)
    
    print(f"✅ Final course count: {len(validated_courses)}")
    
    # Save final results with validation
    output_data = {
        "metadata": {
            "source_file": os.path.basename(pdf_path),
            "total_pages": len(pages_text),
            "total_courses": len(validated_courses),
            "extraction_timestamp": datetime.now().isoformat(),
            "extractor": "Gemini LLM",
            "model": "gemini-1.5-flash",
            "status": "complete"
        },
        "courses": validated_courses
    }
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"💾 Final results saved to: {output_path}")
        return True
    except Exception as e:
        print(f"❌ Error saving final results: {e}")
        return False

def main():
    # Define file paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(script_dir, 'courses.pdf')
    output_path = os.path.join(script_dir, 'courses_extracted.json')
    
    print("🎓 Maui Courses Gemini Extractor")
    print("=" * 40)
    
    # Check if PDF exists
    if not os.path.exists(pdf_path):
        print(f"❌ Error: PDF file not found at {pdf_path}")
        print("Please ensure the courses.pdf file is in the same directory as this script.")
        return
    
    # Extract courses from PDF using Gemini
    success = extract_courses_from_pdf(pdf_path, output_path)
    
    if success:
        print(f"\n🎉 Course extraction complete! Use the web server to view results.")
        print(f"💡 Run: python web_server.py to start the web interface")
    else:
        print(f"\n❌ Extraction failed. Please check the error messages above.")

if __name__ == "__main__":
    main()
