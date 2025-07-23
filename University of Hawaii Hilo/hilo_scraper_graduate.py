import time
import json
import re
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def load_translations(translations_file_path):
    """Load course prefix to department name translations from JSON file."""
    try:
        with open(translations_file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load translations file {translations_file_path}: {e}")
        return {}

def parse_course_from_html(html_content, source_url, translations=None):
    """
    Parse course information from HTML content using regex to find course blocks.
    Looks for patterns like: <p><strong>ACC 200 Accounting Internship (3)</strong> Description...</p>
    """
    courses = []
    
    # Extract department name from h1 tag with id="page-content-title"
    dept_name = None
    h1_pattern = r'<h1[^>]*id=["\']page-content-title["\'][^>]*>([^<]+)</h1>'
    h1_match = re.search(h1_pattern, html_content, re.IGNORECASE)
    if h1_match:
        h1_text = h1_match.group(1).strip()
        # Extract text before parentheses
        dept_match = re.match(r'^([^(]+)', h1_text)
        if dept_match:
            dept_name = dept_match.group(1).strip()
            print(f"  Found department: {dept_name}")
    
    # Regex to find course blocks in HTML
    # Pattern: <p><strong>PREFIX NUMBER Title (Units)</strong> Description...</p>
    course_pattern = r'<p><strong>([A-Z]+)\s+(\d+[A-Z]*)\s+([^(]+?)\s*\(([^)]+)\)</strong>\s*([^<]*(?:<[^>]*>[^<]*)*?)</p>'
    
    matches = re.finditer(course_pattern, html_content, re.IGNORECASE | re.DOTALL)
    
    for match in matches:
        prefix = match.group(1).strip()
        number = match.group(2).strip()
        title = match.group(3).strip()
        units = match.group(4).strip()
        description = match.group(5).strip()
        
        # Clean up description by removing HTML tags
        description = re.sub(r'<[^>]+>', '', description).strip()
        
        course_data = {
            'course_prefix': prefix,
            'course_number': number,
            'course_title': title,
            'course_desc': description,
            'num_units': units,
            'dept_name': dept_name,  # Use extracted department name
            'inst_ipeds': 141574,  # UH Hilo IPEDS code
            'metadata': {},  # Can be expanded later if needed
            'source_url': source_url,
            'extraction_timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        courses.append(course_data)
        print(f"  Extracted: {prefix} {number} - {title}")
    
    return courses

def collect_department_links(base_url, driver):
    """
    Collect all department/course section links from the main catalog page.
    Looks for patterns like: <li><a href="acc-courses">Accounting (ACC) Courses</a></li>
    """
    print(f"Collecting department links from: {base_url}")
    
    try:
        driver.get(base_url)
        time.sleep(1)
        
        # Find all links that end with "-courses" or "-gr" (for graduate/post-baccalaureate courses)
        course_links = driver.find_elements(By.CSS_SELECTOR, "a[href$='-courses']")
        gr_links = driver.find_elements(By.CSS_SELECTOR, "a[href$='-gr']")
        links = course_links + gr_links
        
        department_links = []
        for link in links:
            href = link.get_attribute('href')
            text = link.text.strip()
            
            # Convert relative URLs to absolute
            if href and not href.startswith('http'):
                href = urljoin(base_url, href)
            
            if href:
                department_links.append({
                    'url': href,
                    'name': text
                })
                print(f"  Found: {text} -> {href}")
        
        print(f"Collected {len(department_links)} department links")
        return department_links
        
    except Exception as e:
        print(f"Error collecting department links: {e}")
        return []

def extract_courses_from_department(dept_info, translations, delay=0.1):
    """Extract courses from a single department page using its own webdriver instance."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=options)
    
    try:
        dept_url = dept_info['url']
        dept_name = dept_info['name']
        
        print(f"Processing department: {dept_name}")
        driver.get(dept_url)
        time.sleep(delay)
        
        page_source = driver.page_source
        courses = parse_course_from_html(page_source, dept_url, translations)
        
        print(f"  Extracted {len(courses)} courses from {dept_name}")
        return courses
        
    except Exception as e:
        print(f"Error extracting courses from {dept_info['name']}: {e}")
        return []
    finally:
        driver.quit()

def save_to_json(data, filepath, lock=None):
    """Save data to JSON file with optional thread lock."""
    try:
        if lock:
            with lock:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"Saved {len(data)} records to {filepath}")
        else:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"Saved {len(data)} records to {filepath}")
    except Exception as e:
        print(f"Error saving JSON: {e}")

def crawl_hilo_courses(base_catalog_url, output_file, max_workers=4, delay_between_requests=0.1, batch_size=10):
    """
    Crawl UH Hilo courses by first collecting department links, then extracting courses from each.
    
    Args:
        base_catalog_url: Main catalog URL to collect department links from
        output_file: Output JSON file path
        max_workers: Number of parallel browser instances (default: 4)
        delay_between_requests: Delay between requests in seconds (default: 0.1)
        batch_size: Number of departments to process before saving (default: 10)
    """
    print(f"Starting UH Hilo course crawl with {max_workers} workers, {delay_between_requests}s delay")
    
    # Load translations for department names
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        script_dir = os.getcwd()
    
    translations_path = os.path.join(script_dir, 'translations.json')
    translations = load_translations(translations_path)
    print(f"Loaded {len(translations)} department translations")

    # Setup main driver for collecting department links
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    main_driver = webdriver.Chrome(options=options)

    try:
        # Step 1: Collect all department links
        department_links = collect_department_links(base_catalog_url, main_driver)
        
        if not department_links:
            print("No department links found. Exiting.")
            return
        
        # Step 2: Process departments in parallel
        all_extracted = []
        file_lock = Lock()
        total_course_count = 0
        
        print(f"\nProcessing {len(department_links)} departments with {max_workers} workers...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all department extraction tasks
            future_to_dept = {
                executor.submit(extract_courses_from_department, dept_info, translations, delay_between_requests): dept_info 
                for dept_info in department_links
            }
            
            # Process completed tasks
            completed_count = 0
            batch_results = []
            
            for future in as_completed(future_to_dept):
                dept_info = future_to_dept[future]
                completed_count += 1
                
                try:
                    courses = future.result()
                    if courses:
                        batch_results.extend(courses)
                        all_extracted.extend(courses)
                        total_course_count += len(courses)
                        print(f"[{completed_count}/{len(department_links)}] Completed {dept_info['name']}: {len(courses)} courses (Total: {total_course_count})")
                    else:
                        print(f"[{completed_count}/{len(department_links)}] No courses found in {dept_info['name']}")
                    
                    # Save in batches to prevent data loss
                    if len(batch_results) >= batch_size * 10 or completed_count == len(department_links):  # Adjust batch size for courses
                        save_to_json(all_extracted, output_file, file_lock)
                        batch_results = []
                        
                except Exception as e:
                    print(f"[{completed_count}/{len(department_links)}] Error processing {dept_info['name']}: {e}")
        
        print(f"\nCrawling finished. Extracted {len(all_extracted)} courses total from {len(department_links)} departments.")
        save_to_json(all_extracted, output_file, file_lock)
        
    finally:
        main_driver.quit()

if __name__ == "__main__":
    BASE_CATALOG_URL = "https://hilo.hawaii.edu/catalog/graduate-courses"
    OUTPUT_FILE = "hilo_courses_graduate.json"

    # Parallelization parameters
    MAX_WORKERS = 30         # Number of parallel browser instances
    DELAY = 0.1            # Delay between requests in seconds
    BATCH_SIZE = 5         # Save frequency (departments processed before saving)

    crawl_hilo_courses(
        BASE_CATALOG_URL, 
        OUTPUT_FILE, 
        max_workers=MAX_WORKERS,
        delay_between_requests=DELAY,
        batch_size=BATCH_SIZE
    )
