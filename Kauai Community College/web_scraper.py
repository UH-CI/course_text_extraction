import time
import json
import re
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def extract_course_info(course_div):
    """Extract course information from a course div element."""
    try:
        # Extract course prefix and number from the h3 link
        h3_link = course_div.find('h3').find('a')
        if not h3_link:
            return None
            
        # Get course code from href (e.g., "/accounting-acc/acc-124")
        href = h3_link.get('href', '')
        course_code_match = re.search(r'/([a-z-]+)/([a-z]+-\d+)', href)
        if not course_code_match:
            return None
            
        # Extract course prefix and number
        course_code = course_code_match.group(2).upper()  # e.g., "ACC-124"
        prefix_number_match = re.match(r'([A-Z]+)-(\d+)', course_code)
        if not prefix_number_match:
            return None
            
        course_prefix = prefix_number_match.group(1)
        course_number = prefix_number_match.group(2)
        
        # Extract course title from the span
        title_span = h3_link.find('span', class_='field field--name-field-item field--type-string field--label-hidden field__item')
        course_title = title_span.get_text(strip=True) if title_span else ''
        
        # Extract credits
        credits_span = course_div.find('span', class_='field field--name-field-credits field--type-integer field--label-above')
        credits_item = credits_span.find('span', class_='field__item') if credits_span else None
        num_units = credits_item.get_text(strip=True) if credits_item else ''
        
        # Extract description
        desc_div = course_div.find('div', class_='field field--name-field-description field--type-text-long field--label-above')
        desc_item = desc_div.find('div', class_='field__item') if desc_div else None
        course_desc = desc_item.get_text(strip=True) if desc_item else ''
        
        # Extract class hours for metadata
        class_hours_span = course_div.find('span', class_='field field--name-field-class-hours')
        class_hours_item = class_hours_span.find('span', class_='field__item') if class_hours_span else None
        class_hours = class_hours_item.get_text(strip=True) if class_hours_item else ''
        
        # Extract semester offered for metadata
        semester_span = course_div.find('span', class_='field field--name-field-class-code field--type-entity-reference field--label-above')
        semester_items = semester_span.find('span', class_='field__items') if semester_span else None
        semester_offered = ''
        if semester_items:
            semester_spans = semester_items.find_all('span', class_='field__item')
            semester_offered = ', '.join([span.get_text(strip=True).rstrip(',') for span in semester_spans])
        
        # Extract student learning outcomes for metadata
        outcomes_div = course_div.find('div', class_='field field--name-field-student-learning-outcomes field--type-text-long field--label-above')
        outcomes = ''
        if outcomes_div:
            outcomes_content = outcomes_div.find('div', class_='field__item')
            if outcomes_content:
                outcomes = outcomes_content.get_text(separator=' ', strip=True)
        
        # Build metadata string
        metadata_parts = []
        if class_hours:
            metadata_parts.append(f"Class Hours: {class_hours}")
        if semester_offered:
            metadata_parts.append(f"Semester Offered: {semester_offered}")
        if outcomes:
            metadata_parts.append(f"Course Student Learning Outcomes: {outcomes}")
        
        metadata = '; '.join(metadata_parts)
        
        return {
            'course_prefix': course_prefix,
            'course_number': course_number,
            'course_title': course_title,
            'course_desc': course_desc,
            'num_units': num_units,
            'dept_name': '',  # Will be filled in later
            'inst_ipeds': 141574,
            'metadata': metadata
        }
        
    except Exception as e:
        print(f"Error extracting course info: {e}")
        return None

def extract_single_course_from_h3(h3_element, dept_name):
    """Extract course information from an h3 element and its surrounding context."""
    try:
        # Extract course prefix and number from the h3 link
        link = h3_element.find('a', href=True)
        if not link:
            return None
            
        # Get course code from href (e.g., "/accounting-acc/acc-124")
        href = link.get('href', '')
        course_code_match = re.search(r'/([a-z-]+)/([a-z]+-\d+)', href)
        if not course_code_match:
            return None
            
        # Extract course prefix and number
        course_code = course_code_match.group(2).upper()  # e.g., "ACC-124"
        prefix_number_match = re.match(r'([A-Z]+)-(\d+)', course_code)
        if not prefix_number_match:
            return None
            
        course_prefix = prefix_number_match.group(1)
        course_number = prefix_number_match.group(2)
        
        # Extract course title from the span within the link
        title_span = link.find('span', class_='field field--name-field-item field--type-string field--label-hidden field__item')
        course_title = title_span.get_text(strip=True) if title_span else ''
        
        # Now find the associated course details by looking for siblings or parent containers
        # Start from the h3 and look for the degree-class-overview and degree-class-details
        
        # Method 1: Look in the same parent container
        parent = h3_element.find_parent()
        credits = ''
        class_hours = ''
        description = ''
        semester_offered = ''
        outcomes = ''
        prerequisites = ''
        comments = ''
        
        # Search in progressively larger parent containers
        search_container = parent
        max_depth = 5
        depth = 0
        
        while search_container and depth < max_depth:
            # Look for credits
            if not credits:
                credits_span = search_container.find('span', class_='field field--name-field-credits field--type-integer field--label-above')
                if credits_span:
                    credits_item = credits_span.find('span', class_='field__item')
                    credits = credits_item.get_text(strip=True) if credits_item else ''
            
            # Look for class hours
            if not class_hours:
                class_hours_span = search_container.find('span', class_='field field--name-field-class-hours')
                if not class_hours_span:
                    class_hours_span = search_container.find('span', class_='field field--name-field-class-hours field--type-text-long field--label-above')
                if class_hours_span:
                    class_hours_item = class_hours_span.find('span', class_='field__item')
                    if not class_hours_item:
                        class_hours_item = class_hours_span.find('div', class_='field__item')
                    class_hours = class_hours_item.get_text(strip=True) if class_hours_item else ''
            
            # Look for description
            if not description:
                desc_div = search_container.find('div', class_='field field--name-field-description field--type-text-long field--label-above')
                if desc_div:
                    desc_item = desc_div.find('div', class_='field__item')
                    description = desc_item.get_text(strip=True) if desc_item else ''
            
            # Look for prerequisites
            if not prerequisites:
                prereq_div = search_container.find('div', class_='field field--name-field-pr field--type-text-long field--label-above')
                if prereq_div:
                    prereq_item = prereq_div.find('div', class_='field__item')
                    prerequisites = prereq_item.get_text(strip=True) if prereq_item else ''
            
            # Look for comments
            if not comments:
                comments_div = search_container.find('div', class_='field field--name-field-comments field--type-text-long field--label-above')
                if comments_div:
                    comments_item = comments_div.find('div', class_='field__item')
                    comments = comments_item.get_text(strip=True) if comments_item else ''
            
            # Look for semester offered
            if not semester_offered:
                semester_span = search_container.find('span', class_='field field--name-field-class-code field--type-entity-reference field--label-above')
                if semester_span:
                    semester_items = semester_span.find('span', class_='field__items')
                    if semester_items:
                        semester_spans = semester_items.find_all('span', class_='field__item')
                        semester_offered = ', '.join([span.get_text(strip=True).rstrip(',') for span in semester_spans])
            
            # Look for student learning outcomes
            if not outcomes:
                outcomes_div = search_container.find('div', class_='field field--name-field-student-learning-outcomes field--type-text-long field--label-above')
                if outcomes_div:
                    outcomes_content = outcomes_div.find('div', class_='field__item')
                    if outcomes_content:
                        outcomes = outcomes_content.get_text(separator=' ', strip=True)
            
            # If we found most of the key information, break
            if credits and description:
                break
                
            # Move to parent container
            search_container = search_container.find_parent()
            depth += 1
        
        # Build metadata string
        metadata_parts = []
        if class_hours:
            metadata_parts.append(f"Class Hours: {class_hours}")
        if semester_offered:
            metadata_parts.append(f"Semester Offered: {semester_offered}")
        if prerequisites:
            metadata_parts.append(f"Prerequisites: {prerequisites}")
        if comments:
            metadata_parts.append(f"Comments: {comments}")
        if outcomes:
            metadata_parts.append(f"Course Student Learning Outcomes: {outcomes}")
        
        metadata = '; '.join(metadata_parts)
        
        return {
            'course_prefix': course_prefix,
            'course_number': course_number,
            'course_title': course_title,
            'course_desc': description,
            'num_units': credits,
            'dept_name': dept_name,
            'inst_ipeds': 141574,
            'metadata': metadata
        }
        
    except Exception as e:
        print(f"Error extracting course from h3: {e}")
        return None

def extract_department_courses(dept_url, base_url):
    """Extract all courses from a department page."""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(options=options)
    courses = []
    
    try:
        full_url = urljoin(base_url, dept_url)
        print(f"  Visiting department page: {full_url}")
        driver.get(full_url)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Extract department name
        dept_name_div = soup.find('div', class_='field field--name-name field--type-string field--label-hidden field__item')
        dept_name = dept_name_div.get_text(strip=True) if dept_name_div else ''
        
        # Find all h3 elements that contain course links
        h3_elements = soup.find_all('h3')
        course_h3s = []
        
        for h3 in h3_elements:
            link = h3.find('a', href=True)
            if link and '/' in link.get('href', ''):
                course_h3s.append(h3)
        
        print(f"    Found {len(course_h3s)} course sections")
        
        for h3 in course_h3s:
            try:
                # Extract course info directly from each h3 and its surrounding context
                course_info = extract_single_course_from_h3(h3, dept_name)
                if course_info:
                    courses.append(course_info)
                    print(f"    Extracted: {course_info['course_prefix']} {course_info['course_number']} - {course_info['course_title']}")
                    
            except Exception as e:
                print(f"    Error processing course h3: {e}")
                continue
        
        print(f"    Total courses extracted from department: {len(courses)}")
        
    except Exception as e:
        print(f"    Error extracting from department {dept_url}: {e}")
    finally:
        driver.quit()
        
    return courses

def save_to_json(data, filepath):
    """Save data to JSON file."""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(data)} records to {filepath}")
    except Exception as e:
        print(f"Error saving to {filepath}: {e}")

def crawl_courses(base_catalog_url_template, output_file, start_page=0, end_page=5):
    """
    Crawl courses from Kauai Community College catalog pages.
    
    Args:
        base_catalog_url_template: URL template for catalog pages
        output_file: Output JSON file path
        start_page: Starting page number (default: 0)
        end_page: Ending page number (default: 5)
    """
    
    all_courses = []
    visited_dept_urls = set()  # Track visited department URLs
    seen_courses = set()  # Track seen courses to avoid duplicates
    base_url = "https://catalog.kauai.hawaii.edu"  # Base URL for the site
    
    print(f"Starting course extraction from pages {start_page} to {end_page}...")
    
    # Setup Chrome options
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(options=options)
    
    try:
        for page_num in range(start_page, end_page + 1):
            catalog_url = base_catalog_url_template.format(page_number=page_num)
            print(f"\nProcessing catalog page {page_num}: {catalog_url}")
            
            try:
                driver.get(catalog_url)
                time.sleep(0.1)
                
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                # Find all department links in the format <a href="/accounting-acc" hreflang="en">Accounting (ACC)</a>
                dept_links = soup.find_all('a', href=True, hreflang='en')
                
                # Filter for department links (those that look like subject pages)
                valid_dept_links = []
                for link in dept_links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    # Look for links that match the pattern of department pages
                    if href.startswith('/') and len(href) > 1 and '(' in text and ')' in text:
                        # Only add if we haven't visited this department URL before
                        if href not in visited_dept_urls:
                            valid_dept_links.append(href)
                            visited_dept_urls.add(href)
                
                print(f"  Found {len(valid_dept_links)} new department links on page {page_num}")
                print(f"  Total departments visited so far: {len(visited_dept_urls)}")
                
                # Extract courses from each department
                for dept_url in valid_dept_links:
                    dept_courses = extract_department_courses(dept_url, base_url)
                    
                    # Deduplicate courses based on course_prefix + course_number
                    for course in dept_courses:
                        course_key = f"{course['course_prefix']}-{course['course_number']}"
                        if course_key not in seen_courses:
                            seen_courses.add(course_key)
                            all_courses.append(course)
                        else:
                            print(f"    Skipping duplicate course: {course_key}")
                    
                    time.sleep(0.1)  # Small delay between departments
                    
            except Exception as e:
                print(f"  Error processing catalog page {page_num}: {e}")
                continue
        
        print(f"\nCrawling finished. Extracted {len(all_courses)} unique courses from {len(visited_dept_urls)} departments.")
        save_to_json(all_courses, output_file)
        
    finally:
        driver.quit()

if __name__ == "__main__":
    BASE_CATALOG_URL_TEMPLATE = (
        "https://catalog.kauai.hawaii.edu/classes?page={page_number}"
    )
    OUTPUT_FILE = "kauai_courses.json"

    crawl_courses(
        BASE_CATALOG_URL_TEMPLATE, 
        OUTPUT_FILE, 
        start_page=0, 
        end_page=5
    )
