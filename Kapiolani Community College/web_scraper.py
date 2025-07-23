import time
import json
import re
import os
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def setup_driver():
    """Setup Chrome driver with options"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    return webdriver.Chrome(options=chrome_options)

def extract_department_name(soup):
    """Extract department name from the blue header table"""
    # Look for the department name table with specific styling
    dept_table = soup.find('table', style=lambda x: x and 'royalblue' in x and 'background-color:royalblue' in x)
    if dept_table:
        dept_cell = dept_table.find('td')
        if dept_cell:
            dept_text = dept_cell.get_text(strip=True)
            # Extract department name from "ACCOUNTING (ACC) COURSES" format
            match = re.match(r'^(.+?)\s*\([A-Z]+\)\s*COURSES?', dept_text)
            if match:
                return match.group(1).strip()
    return None

def parse_course_details(soup, dept_name, page_url):
    """Parse course details from the lightgray table format"""
    courses = []
    
    # Find all course tables with lightgray background
    course_tables = soup.find_all('table', style=lambda x: x and 'lightgray' in x and 'background-color:lightgray' in x)
    
    for table in course_tables:
        try:
            course_data = {
                'course_prefix': None,
                'course_number': None,
                'course_title': None,
                'course_desc': None,
                'num_units': None,
                'dept_name': dept_name,
                'inst_ipeds': 141574,  # Hardcoded as requested
                'metadata': None,
                'source_url': page_url,
                'extraction_timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            rows = table.find_all('tr')
            if not rows:
                continue
                
            # First row: Course code and title
            first_row = rows[0]
            course_link = first_row.find('a')
            if course_link:
                course_text = course_link.get_text(strip=True)
                # Parse "ACC124: Principles of Accounting I" format
                match = re.match(r'^([A-Z]+)(\d+[A-Z]*):?\s*(.*)$', course_text)
                if match:
                    course_data['course_prefix'] = match.group(1)
                    course_data['course_number'] = match.group(2)
                    course_data['course_title'] = match.group(3).strip()
            
            # Process remaining rows
            description_parts = []
            metadata_parts = []
            credits = None
            
            for row in rows[1:]:
                cell = row.find('td')
                if not cell:
                    continue
                    
                cell_text = cell.get_text(strip=True)
                
                # Check for credits
                if cell_text.startswith('Credits:'):
                    credits_match = re.search(r'Credits:\s*(\d+|V)', cell_text)
                    if credits_match:
                        credits = credits_match.group(1)
                # Check for prerequisites/corequisites
                elif 'Prereq:' in cell_text or 'Coreq:' in cell_text:
                    metadata_parts.append(cell_text)
                # Otherwise, it's likely part of the description
                else:
                    if cell_text and not cell_text.startswith('Credits:'):
                        description_parts.append(cell_text)
            
            # Set the extracted data
            course_data['num_units'] = credits
            course_data['course_desc'] = ' '.join(description_parts).strip() if description_parts else None
            course_data['metadata'] = '; '.join(metadata_parts).strip() if metadata_parts else None
            
            # Only add course if we have essential information
            if course_data['course_prefix'] and course_data['course_number']:
                courses.append(course_data)
                print(f"  Extracted: {course_data['course_prefix']}{course_data['course_number']} - {course_data['course_title']}")
            
        except Exception as e:
            print(f"  Error parsing course table: {e}")
            continue
    
    return courses

def get_all_catalog_links(driver, base_url, base_course_url_prefix):
    """Get all links from the base catalog page that match the URL prefix"""
    print(f"Fetching links from: {base_url}")
    
    try:
        driver.get(base_url)
        time.sleep(2)
        
        # Find all links that start with the base course URL prefix
        links = driver.find_elements(By.CSS_SELECTOR, "a[href]")
        catalog_links = set()
        
        for link in links:
            href = link.get_attribute('href')
            if href and href.startswith(base_course_url_prefix):
                catalog_links.add(href)
        
        print(f"Found {len(catalog_links)} catalog links")
        return list(catalog_links)
        
    except Exception as e:
        print(f"Error fetching catalog links: {e}")
        return []

def scrape_catalog_page(driver, page_url):
    """Scrape a single catalog page for courses"""
    print(f"\nScraping: {page_url}")
    
    try:
        driver.get(page_url)
        time.sleep(1)
        
        # Get page source and parse with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Extract department name
        dept_name = extract_department_name(soup)
        if not dept_name:
            print(f"  No department name found, skipping page")
            return []
        
        print(f"  Department: {dept_name}")
        
        # Parse course details
        courses = parse_course_details(soup, dept_name, page_url)
        print(f"  Extracted {len(courses)} courses")
        
        return courses
        
    except Exception as e:
        print(f"  Error scraping page {page_url}: {e}")
        return []

def save_courses_to_json(courses, output_file):
    """Save courses to JSON file"""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(courses, f, indent=2, ensure_ascii=False)
        print(f"\nSaved {len(courses)} courses to {output_file}")
    except Exception as e:
        print(f"Error saving to JSON: {e}")

def main():
    """Main scraping function"""
    # Configuration
    BASE_CATALOG_URL = "https://www.papakuhikuhi.com/courses.php"
    BASE_COURSE_URL_PREFIX = "https://www.papakuhikuhi.com/subject.php?code="
    OUTPUT_FILE = "kapiolani_courses.json"
    
    print("🎓 Kapiolani Community College Course Scraper")
    print("=" * 50)
    
    # Setup driver
    driver = setup_driver()
    
    try:
        # Get all catalog links
        catalog_links = get_all_catalog_links(driver, BASE_CATALOG_URL, BASE_COURSE_URL_PREFIX)
        
        if not catalog_links:
            print("No catalog links found!")
            return
        
        # Track visited pages to avoid duplicates
        visited_pages = set()
        all_courses = []
        
        # Scrape each catalog page
        for i, page_url in enumerate(catalog_links, 1):
            if page_url in visited_pages:
                print(f"[{i}/{len(catalog_links)}] Skipping already visited: {page_url}")
                continue
                
            print(f"[{i}/{len(catalog_links)}] Processing page...")
            courses = scrape_catalog_page(driver, page_url)
            
            if courses:
                all_courses.extend(courses)
            
            visited_pages.add(page_url)
            
            # Small delay between requests
            time.sleep(0.5)
        
        # Save results
        save_courses_to_json(all_courses, OUTPUT_FILE)
        
        print(f"\n✅ Scraping completed!")
        print(f"📊 Total courses extracted: {len(all_courses)}")
        print(f"📄 Pages visited: {len(visited_pages)}")
        
    except Exception as e:
        print(f"Error in main scraping process: {e}")
    
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
