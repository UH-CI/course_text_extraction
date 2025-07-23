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

def extract_course_from_page(driver, course_url):
    """Extract course information from individual course page."""
    try:
        print(f"    Visiting course: {course_url}")
        driver.get(course_url)
        time.sleep(1)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Find the main course container
        course_container = soup.find('div', class_='course-view__itemDetailContainer___2tFFK')
        if not course_container:
            print(f"    No course container found for {course_url}")
            return None
        
        # Extract course title and parse prefix/number
        title_div = course_container.find('h2')
        if not title_div:
            print(f"    No title found for {course_url}")
            return None
            
        title_text = title_div.get_text(strip=True)
        # Parse "ACC124 - Principles of Accounting I (LEC - Lecture)"
        title_match = re.match(r'([A-Z]+)(\d+)\s*-\s*([^(]+)', title_text)
        if not title_match:
            print(f"    Could not parse title: {title_text}")
            return None
            
        course_prefix = title_match.group(1)
        course_number = title_match.group(2)
        course_title = title_match.group(3).strip()
        
        # Extract description
        description = ''
        desc_labels = course_container.find_all('h3', class_='course-view__label___FPV12')
        for label in desc_labels:
            if 'Description' in label.get_text():
                # Find the description content
                desc_container = label.find_parent()
                while desc_container:
                    desc_div = desc_container.find('div', class_='course-view__pre___2VF54')
                    if desc_div:
                        description = desc_div.get_text(strip=True)
                        break
                    desc_container = desc_container.find_parent()
                break
        
        # Extract credits
        credits = ''
        for label in desc_labels:
            if 'Credits' in label.get_text():
                credit_container = label.find_parent()
                while credit_container:
                    credit_div = credit_container.find('div', class_='course-view__pre___2VF54')
                    if credit_div:
                        credits = credit_div.get_text(strip=True)
                        break
                    credit_container = credit_container.find_parent()
                break
        
        # Extract prerequisites
        prerequisites = ''
        for label in desc_labels:
            if 'Prerequisites' in label.get_text():
                prereq_container = label.find_parent()
                while prereq_container:
                    prereq_div = prereq_container.find('div', class_='course-view__pre___2VF54')
                    if prereq_div:
                        prerequisites = prereq_div.get_text(strip=True)
                        break
                    prereq_container = prereq_container.find_parent()
                break
        
        # Extract recommended course preparation
        recommended_prep = ''
        for label in desc_labels:
            if 'Recommended Course Preparation' in label.get_text():
                prep_container = label.find_parent()
                while prep_container:
                    prep_div = prep_container.find('div', class_='course-view__pre___2VF54')
                    if prep_div:
                        recommended_prep = prep_div.get_text(strip=True)
                        break
                    prep_container = prep_container.find_parent()
                break
        
        # Extract contact hours
        contact_hours = ''
        contact_hours_section = course_container.find('h3', string=lambda text: text and 'Contact Hours' in text)
        if contact_hours_section:
            # Look for the table with contact hours
            table = course_container.find('table')
            if table:
                rows = table.find_all('tr')
                if len(rows) >= 2:  # Header + data row
                    cells = rows[1].find_all('td')
                    if cells:
                        lecture_hours = cells[0].get_text(strip=True) if len(cells) > 0 else ''
                        lab_hours = cells[1].get_text(strip=True) if len(cells) > 1 else ''
                        other_hours = cells[2].get_text(strip=True) if len(cells) > 2 else ''
                        
                        hours_parts = []
                        if lecture_hours:
                            hours_parts.append(f"{lecture_hours} lecture")
                        if lab_hours:
                            hours_parts.append(f"{lab_hours} lab")
                        if other_hours:
                            hours_parts.append(f"{other_hours} other")
                        contact_hours = ', '.join(hours_parts)
        
        # Build metadata
        metadata_parts = []
        if prerequisites:
            metadata_parts.append(f"Prerequisites: {prerequisites}")
        if recommended_prep:
            metadata_parts.append(f"Recommended Course Preparation: {recommended_prep}")
        if contact_hours:
            metadata_parts.append(f"Contact Hours: {contact_hours}")
        
        metadata = '; '.join(metadata_parts)
        
        # Determine department name from course prefix (simplified mapping)
        dept_mapping = {
            'ACC': 'Accounting',
            'ART': 'Art',
            'BIOL': 'Biology',
            'BUSN': 'Business',
            'CHEM': 'Chemistry',
            'ENG': 'English',
            'HIST': 'History',
            'MATH': 'Mathematics',
            'PHIL': 'Philosophy',
            'PHYS': 'Physics',
            'PSY': 'Psychology'
        }
        dept_name = dept_mapping.get(course_prefix, course_prefix)
        
        course_info = {
            'course_prefix': course_prefix,
            'course_number': course_number,
            'course_title': course_title,
            'course_desc': description,
            'num_units': credits,
            'dept_name': dept_name,
            'inst_ipeds': 141574,
            'metadata': metadata
        }
        
        print(f"    Extracted: {course_prefix} {course_number} - {course_title}")
        return course_info
        
    except Exception as e:
        print(f"    Error extracting course from {course_url}: {e}")
        return None

def collect_course_links(driver):
    """Expand all content and collect course links from the catalog page."""
    try:
        print("  Expanding all content by clicking show buttons...")
        
        # Find and click all buttons with aria-label containing 'show'
        buttons = driver.find_elements(By.XPATH, "//button[contains(@aria-label, 'show')]")
        print(f"  Found {len(buttons)} show buttons to click")
        
        for btn in buttons:
            try:
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(0.1)  # small delay to allow rendering
            except Exception as e:
                print(f"    Error clicking button: {e}")
                continue
        
        print("  Finished expanding content, collecting course links...")
        time.sleep(2)  # Allow time for all content to load
        
        # Collect all course links
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Find all links that match the pattern for course links
        course_links = []
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link.get('href', '')
            # Look for links that match the pattern: #/courses/QHF2JZ7Lb?bc=true&...
            if href.startswith('#/courses/') and 'bc=true' in href:
                # Convert to full URL
                full_url = f"https://www.leeward.hawaii.edu/catalog{href}"
                course_links.append(full_url)
        
        # Remove duplicates
        course_links = list(set(course_links))
        print(f"  Found {len(course_links)} unique course links")
        
        return course_links
        
    except Exception as e:
        print(f"  Error collecting course links: {e}")
        return []

def save_to_json(data, filepath):
    """Save data to JSON file."""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(data)} records to {filepath}")
    except Exception as e:
        print(f"Error saving to {filepath}: {e}")

def crawl_courses(base_catalog_url, output_file):
    """
    Crawl courses from Leeward Community College catalog page.
    
    Args:
        base_catalog_url: URL of the catalog page
        output_file: Output JSON file path
    """
    
    all_courses = []
    seen_courses = set()  # Track seen courses to avoid duplicates
    
    print(f"Starting course extraction from Leeward Community College catalog...")
    
    # Setup Chrome options
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(options=options)
    
    try:
        print(f"\nVisiting catalog page: {base_catalog_url}")
        driver.get(base_catalog_url)
        time.sleep(3)  # Allow page to load completely
        
        # Expand all content and collect course links
        course_links = collect_course_links(driver)
        
        if not course_links:
            print("No course links found!")
            return
        
        print(f"\nProcessing {len(course_links)} course links...")
        
        # Process each course link
        for i, course_url in enumerate(course_links, 1):
            try:
                print(f"\n[{i}/{len(course_links)}] Processing course...")
                course_info = extract_course_from_page(driver, course_url)
                
                if course_info:
                    # Deduplicate courses based on course_prefix + course_number
                    course_key = f"{course_info['course_prefix']}-{course_info['course_number']}"
                    if course_key not in seen_courses:
                        seen_courses.add(course_key)
                        all_courses.append(course_info)
                        print(f"    Added: {course_info['course_prefix']} {course_info['course_number']} - {course_info['course_title']}")
                    else:
                        print(f"    Skipping duplicate course: {course_key}")
                else:
                    print(f"    Failed to extract course data")
                    
                # Small delay between courses
                time.sleep(0.5)
                
            except Exception as e:
                print(f"    Error processing course {course_url}: {e}")
                continue
        
        print(f"\nCrawling finished. Extracted {len(all_courses)} unique courses.")
        save_to_json(all_courses, output_file)
        
    except Exception as e:
        print(f"Error in main crawling process: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    BASE_CATALOG_URL = "https://www.leeward.hawaii.edu/catalog#/courses"
    OUTPUT_FILE = "leeward_courses.json"

    crawl_courses(
        BASE_CATALOG_URL, 
        OUTPUT_FILE
    )
