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

def parse_course_preview_html(html, url, translations=None):
    soup = BeautifulSoup(html, 'html.parser')
    container = soup.find('td', class_='block_content', colspan="2")
    if not container:
        return None

    # Course prefix, number, title
    course_title_h1 = container.find('h1', id='course_preview_title')
    prefix = number = title = None
    if course_title_h1:
        text = course_title_h1.get_text(separator=' ', strip=True)
        match = re.match(r'([A-Z]+)\s+([\dA-Z]+)\s*-\s*(.*)', text)
        if match:
            prefix, number, title = match.groups()

    # Units (credits)
    credits_match = re.search(r'Credits:\s*(\d+(\.\d+)?)', container.get_text())
    credits_text = credits_match.group(1) if credits_match else None

    # Full text as lines
    full_text = container.get_text(separator='\n', strip=True)
    credits_pos = full_text.find('Credits:')

    # Extract description: from Credits: to before first <strong> label or end of content
    desc = None
    if credits_pos >= 0:
        # Find where the description ends: position of first <strong> tag's text after credits, or end of text if none found
        strong_tags = container.find_all('strong')
        end_pos = len(full_text)
        for tag in strong_tags:
            label = tag.get_text(strip=True)
            idx = full_text.find(label)
            if idx > credits_pos and idx < end_pos:
                end_pos = idx
        desc = full_text[credits_pos + len('Credits:'):end_pos].strip()

    # Now extract all metadata fields dynamically: all <strong> labels and their following text content
    metadata = {}
    strong_tags = container.find_all('strong')
    for tag in strong_tags:
        label = tag.get_text(strip=True).rstrip(':')
        content_parts = []
        sibling = tag.next_sibling
        while sibling:
            if getattr(sibling, 'name', None) == 'strong':
                break
            if isinstance(sibling, str):
                content_parts.append(sibling.strip())
            else:
                content_parts.append(sibling.get_text(strip=True))
            sibling = sibling.next_sibling
        value = ' '.join([part for part in content_parts if part])
        metadata[label] = value

    # Clean metadata of description-related keys
    metadata.pop('Credits', None)
    if '' in metadata:
        metadata.pop('')

    # Get department name from translations
    dept_name = None
    if translations and prefix:
        dept_name = translations.get(prefix, None)
    
    return {
        'course_prefix': prefix,
        'course_number': number,
        'course_title': title,
        'course_desc': desc,
        'num_units': credits_text,
        'dept_name': dept_name,
        'inst_ipeds': None,     # Placeholder if you want to add later
        'metadata': metadata,
        'source_url': url,
        'extraction_timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
    }

def save_to_json(data, filepath, lock=None):
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

def extract_single_course(course_url, translations, delay=0.1):
    """Extract a single course using its own webdriver instance."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=options)
    
    try:
        driver.get(course_url)
        time.sleep(delay)
        
        page_source = driver.page_source
        parsed = parse_course_preview_html(page_source, course_url, translations)
        return parsed
    except Exception as e:
        print(f"Error extracting course {course_url}: {e}")
        return None
    finally:
        driver.quit()

def crawl_courses(base_catalog_url_template, base_course_url_prefix, output_file, start_page=0, end_page=92, 
                 max_workers=4, delay_between_requests=0.1, batch_size=50):
    """
    Parallelized course crawler with configurable parameters.
    
    Args:
        max_workers: Number of parallel browser instances (default: 4)
        delay_between_requests: Delay between requests in seconds (default: 0.1)
        batch_size: Number of courses to process before saving (default: 50)
    """
    print(f"Starting parallelized crawl with {max_workers} workers, {delay_between_requests}s delay, batch size {batch_size}")
    
    # Load translations for department names
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        script_dir = os.getcwd()
    
    translations_path = os.path.join(script_dir, 'translations.json')
    translations = load_translations(translations_path)
    print(f"Loaded {len(translations)} department translations from {translations_path}")

    # Setup for catalog page collection
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)

    visited_courses = set()
    all_extracted = []
    file_lock = Lock()
    total_course_count = 0

    # Process each catalog page one by one
    for page_num in range(start_page, end_page + 1):
        catalog_url = base_catalog_url_template.format(page_number=page_num)
        print(f"\nVisiting catalog page {page_num}: {catalog_url}")
        
        # Collect course links from current catalog page
        current_page_course_links = set()
        try:
            driver.get(catalog_url)
            time.sleep(0.1)

            links = driver.find_elements(By.CSS_SELECTOR, "a[href]")
            for link in links:
                href = link.get_attribute('href')
                if href and href.startswith(base_course_url_prefix):
                    if href not in visited_courses:
                        current_page_course_links.add(href)
            
            print(f"  Found {len(current_page_course_links)} new course links on this page.")
        except Exception as e:
            print(f"  Error visiting catalog page {catalog_url}: {e}")
            continue

        if not current_page_course_links:
            continue

        # Process courses from current catalog page in parallel
        course_urls = list(current_page_course_links)
        print(f"\nProcessing {len(course_urls)} courses from page {page_num} with {max_workers} workers...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all course extraction tasks
            future_to_url = {
                executor.submit(extract_single_course, url, translations, delay_between_requests): url 
                for url in course_urls
            }
            
            # Process completed tasks
            completed_count = 0
            batch_results = []
            
            for future in as_completed(future_to_url):
                course_url = future_to_url[future]
                completed_count += 1
                total_course_count += 1
                
                try:
                    parsed = future.result()
                    if parsed:
                        print(f"[{completed_count}/{len(course_urls)}] [Total: {total_course_count}] Extracted: {parsed['course_prefix']} {parsed['course_number']} - {parsed['course_title']}")
                        batch_results.append(parsed)
                        all_extracted.append(parsed)
                    else:
                        print(f"[{completed_count}/{len(course_urls)}] [Total: {total_course_count}] Failed to parse: {course_url}")
                    
                    visited_courses.add(course_url)
                    
                    # Save in batches to prevent data loss while maintaining performance
                    if len(batch_results) >= batch_size or completed_count == len(course_urls):
                        save_to_json(all_extracted, output_file, file_lock)
                        batch_results = []
                        
                except Exception as e:
                    print(f"[{completed_count}/{len(course_urls)}] [Total: {total_course_count}] Error processing {course_url}: {e}")
        
        print(f"\nCompleted catalog page {page_num}. Total courses extracted so far: {len(all_extracted)}")

    driver.quit()
    print(f"\nParallelized crawling finished. Extracted {len(all_extracted)} courses total.")
    save_to_json(all_extracted, output_file, file_lock)

if __name__ == "__main__":
    BASE_CATALOG_URL_TEMPLATE = (
        "https://catalog.manoa.hawaii.edu/content.php?"
        "catoid=2&catoid=2&navoid=420&"
        "filter%5Bitem_type%5D=3&filter%5Bonly_active%5D=1&"
        "filter%5B3%5D=1&filter%5Bcpage%5D={page_number}#acalog_template_course_filter"
    )
    BASE_COURSE_URL_PREFIX = "https://catalog.manoa.hawaii.edu/preview_course_nopop.php?catoid=2&coid="
    OUTPUT_FILE = "extracted_coursesV2.json"

    # Parallelization parameters - adjust these for speed vs. server load balance
    MAX_WORKERS = 50        # Number of parallel browser instances (higher = faster, but more resource intensive)
    DELAY = 0.05          # Delay between requests in seconds (lower = faster, but higher server load)
    BATCH_SIZE = 100       # Save frequency (lower = more frequent saves, higher = better performance)

    crawl_courses(
        BASE_CATALOG_URL_TEMPLATE, 
        BASE_COURSE_URL_PREFIX, 
        OUTPUT_FILE, 
        start_page=0, 
        end_page=92,
        max_workers=MAX_WORKERS,
        delay_between_requests=DELAY,
        batch_size=BATCH_SIZE
    )
