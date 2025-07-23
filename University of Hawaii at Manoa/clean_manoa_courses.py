import json
import re

INPUT_FILE = "extracted_coursesV2.json"
OUTPUT_FILE = "extracted_coursesV2_cleaned.json"
INST_IPEDS_VALUE = "141574"

def clean_course(course):
    # Fill inst_ipeds as a number
    course["inst_ipeds"] = 141574

    # Remove unwanted fields
    course.pop("source_url", None)
    course.pop("extraction_timestamp", None)

    desc = course.get("course_desc", "")
    num_units = course.get("num_units", None)
    metadata = course.get("metadata", {})
    
    metadata = course.get("metadata", {})
    if isinstance(metadata, dict):
        meta_str = "; ".join(f"{k}: {v}" for k, v in metadata.items())
        # Remove the unwanted substring everywhere it appears
        meta_str = meta_str.replace("Print (opens a new window)Help (opens a new window)", "")
        # Clean up potential double semicolons or extra spaces
        meta_str = re.sub(r';\s*;', ';', meta_str).strip('; ').strip()
        course["metadata"] = meta_str
    elif metadata is None:
        course["metadata"] = ""

    if isinstance(desc, str):
        desc_stripped = desc.strip()
        # If desc is a single value (e.g. "V" or "3")
        if re.fullmatch(r'[A-Za-z0-9.]+', desc_stripped):
            course["num_units"] = desc_stripped
            course["course_desc"] = ""
        else:
            # If desc starts with X\n, remove X and the newline, set num_units to X
            match = re.match(r'^([A-Za-z0-9.]+)\s*\n(.*)', desc)
            if match:
                course["num_units"] = match.group(1)
                course["course_desc"] = match.group(2).strip()
            else:
                # If not matching, keep the original description and num_units
                course["course_desc"] = desc
                course["num_units"] = num_units
    else:
        course["course_desc"] = ""
        course["num_units"] = num_units
    return course

def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        courses = json.load(f)

    cleaned = [clean_course(dict(course)) for course in courses]

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)

    print(f"Processed {len(cleaned)} courses. Output: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()