import json
import os
import time
import re
from pathlib import Path
from typing import List, Dict
from canvasapi import Canvas
from canvasapi.course import Course
from canvasapi.module import Module
from canvasapi.page import Page
from dotenv import load_dotenv

def download_course_modules(canvas, course, download_dir="downloads") -> List[Dict]:
    """Download all module items from a course using canvasapi"""
    
    # Create download directory
    Path(download_dir).mkdir(parents=True, exist_ok=True)

    # Get all modules with their items
    modules = course.get_modules(include=['items'])
    
    all_items = []
    
    for module in modules:
        module_id = getattr(module, 'id', 0)
        module_name = getattr(module, 'name', 'Unknown Module')
        print(f"\nProcessing Module {module_id}: {module_name}")
        
        # Get module items
        items = module.get_module_items()
        
        allowed_types = ['File','Attachment','Page']
        items_to_download = [
            item for item in items 
            if getattr(item, 'type', '') in allowed_types and getattr(item, 'published', False)
        ]
        all_items.extend(items_to_download)

        for item in items_to_download:
            item_type = getattr(item, 'type', '')
            title = getattr(item, 'title', 'untitled')
            position = getattr(item, 'position', 0)
            
            print(f"  Processing: {title} (Type: {item_type}, Position: {position})")
            
            try:
                if item_type == 'File':
                    download_file(item, module, course, canvas, download_dir, module_id, position)
                    
                elif item_type == 'Page':
                    download_page(item, module, course, canvas, download_dir, module_id, position)
                    
                elif item_type == 'Attachment':
                    download_file(item, module, course, canvas, download_dir, module_id, position)
                    
                else:
                    print(f"    Skipping {item_type} - not downloadable")
                    
            except Exception as e:
                print(f"    Error downloading {title}: {e}")
    return all_items
    
def make_sortable_filename(title, module_title, module_position, position, extension=""):
    """Create filename that will sort in module order"""

    basefilename, ogextension = os.path.splitext(title)
    extension = extension if extension else ogextension
    safe_title = re.sub(r'[ <>:"/\\|?*]+', '_', basefilename)
    safe_title = safe_title.strip()
    
    safe_module_title = re.sub(r'[ <>:"/\\|?*]+', '_', module_title)
    truncated_module_title = safe_module_title[:25]
    safe_module_title = safe_module_title.strip()


    prefix = f"{module_position:03d}_{truncated_module_title}_{position:03d}"
    base_name = f"{prefix}_{safe_title}"
    
    if len(base_name) > 200:
        safe_title = safe_title[:200 - len(prefix) - 1]
        base_name = f"{prefix}_{safe_title}"
    
    return f"{base_name}{extension}"

def download_file(item, module, course, canvas, download_dir, module_id, position):
    """Download a file using canvasapi"""
    content_id = getattr(item, 'content_id', None)
    title = getattr(item, 'title', 'untitled')
    
    if not content_id:
        print(f"    No content_id for file: {title}")
        return
    
    try:
        # Get the file object
        file_obj = canvas.get_file(content_id)
        
        # Get original filename and extension
        original_filename = getattr(file_obj, 'filename', title)
        file_ext = Path(original_filename).suffix
        content_type = getattr(file_obj, 'content-type', 'unknown')
        print(f"---- {content_type}\t{original_filename}")
        
        # Create sortable filename
        sortable_filename = make_sortable_filename(title, module.name, module.position, position, file_ext)
        filepath = Path(download_dir) / sortable_filename
        
        # Download the file
        file_obj.download(str(filepath))
        print(f"    Downloaded: {sortable_filename}")
        
    except Exception as e:
        print(f"    Error downloading file {title}: {e}")

def download_page(item, module, course, canvas, download_dir, module_id, position):
        """Download page content as HTML"""
        page_url = getattr(item, 'page_url', None)
        title = getattr(item, 'title', 'untitled')
        
        if not page_url:
            print(f"    No page_url for page: {title}")
            return
        
        try:
            # Get the page
            page = course.get_page(page_url)
            page_content = getattr(page, 'body', '')
            
            # Create sortable filename
            sortable_filename = make_sortable_filename(title, module.name, module.position, position, ".html")
            filepath = Path(download_dir) / sortable_filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"""<!DOCTYPE html>
    <html>
    <head>
        <title>{title}</title>
        <meta charset="utf-8">
    </head>
    <body>
        <h1>{title}</h1>
        {page_content}
    </body>
    </html>""")
            
            print(f"    Downloaded page: {sortable_filename}")
            
        except Exception as e:
            print(f"    Error downloading page {title}: {e}")


def main():
    # Configuration - replace with your actual values
    # Load environment variables from .env file
    load_dotenv()
    
    # Configuration - READ FROM .env FILE
    CANVAS_URL = os.getenv("CANVAS_URL").rstrip('/')
    ACCESS_TOKEN = os.getenv("CANVAS_API_TOKEN")
    COURSE_ID = os.getenv("CONTENT_CANVAS_COURSE_ID")
    DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR")
    CONTENT_DIR = f"./{DOWNLOAD_DIR}/course_{COURSE_ID}_content"

    # Initialize the Canvas API object
    canvas = Canvas(CANVAS_URL, ACCESS_TOKEN)
    course = canvas.get_course(COURSE_ID)
    print(course)
    print(f"creating {CONTENT_DIR}")
    downloaded_items = download_course_modules(canvas,course,CONTENT_DIR)

    # Extract all published pages from published modules
    if downloaded_items:
        print(f"\nSuccessfully extracted {len(downloaded_items)} items!")
        for i in downloaded_items:
            print(f"ID: {i.id}, Module: {i.module_id}, Pos: {i.position}, Type: {i.type}, Title: {i.title}")
    else:
        print("No pages found or error occurred.")


if __name__ == "__main__":
    main()