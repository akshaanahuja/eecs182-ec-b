#!/usr/bin/env python3
"""
One-time script to scrape Ed forum posts and generate a static website.
Fetches posts with titles containing "special participation b" and displays them.
"""

import os
from datetime import datetime
from pathlib import Path

# Try to load from .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, skip .env file loading

try:
    from edapi import EdAPI
except ImportError:
    print("❌ Error: edapi is not installed. Please run: pip install -r requirements.txt")
    exit(1)

# ============================================================================
# CONFIGURATION - Update these values
# ============================================================================

# Get your API token from: https://edstem.org/us/settings/api-tokens
# You can set it as an environment variable ED_API_TOKEN or create a .env file
API_TOKEN = os.getenv('ED_API_TOKEN')

# Your course ID (you can find this in the Ed forum URL)
COURSE_ID = '84647'  # Update this with your course ID

# Title filter - will match any title containing this (case-insensitive)
TITLE_FILTER = "special participation b"

# Output directory for the static website
OUTPUT_DIR = "output"

# ============================================================================
# END CONFIGURATION
# ============================================================================


def escape_html(text):
    """Escape HTML special characters."""
    if not text:
        return ""
    return (str(text)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#x27;'))


def format_date(date_str):
    """Format ISO date string to readable format."""
    if not date_str:
        return "Unknown date"
    try:
        if isinstance(date_str, str):
            # Handle ISO format with or without timezone
            date_str = date_str.replace('Z', '+00:00')
            dt = datetime.fromisoformat(date_str)
            return dt.strftime('%B %d, %Y at %I:%M %p')
    except Exception:
        pass
    return str(date_str)


def parse_thread_content(content):
    """Parse Ed's XML document format to plain text/HTML."""
    if not content:
        return ""
    
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, 'xml')
        # Extract text from the document, preserving some structure
        text = soup.get_text(separator='\n', strip=True)
        return text
    except Exception:
        # If parsing fails, return as-is
        return str(content)


def generate_static_website(threads, output_dir="output"):
    """
    Generate a static HTML website from the scraped threads.
    
    Args:
        threads: List of thread dictionaries
        output_dir: Directory to output the static website
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate main index page
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Special Participation B Posts</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }}
        
        h1 {{
            color: #2c3e50;
            margin-bottom: 10px;
            border-bottom: 3px solid #667eea;
            padding-bottom: 15px;
            font-size: 2.5em;
        }}
        
        .meta {{
            color: #7f8c8d;
            margin-bottom: 30px;
            font-size: 14px;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 6px;
        }}
        
        .post {{
            margin-bottom: 40px;
            padding: 30px;
            background: #fafafa;
            border-left: 5px solid #667eea;
            border-radius: 8px;
            transition: transform 0.2s, box-shadow 0.2s;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .post:hover {{
            transform: translateY(-3px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.15);
        }}
        
        .post-title {{
            font-size: 26px;
            color: #2c3e50;
            margin-bottom: 15px;
            font-weight: 600;
            line-height: 1.3;
        }}
        
        .post-meta {{
            color: #7f8c8d;
            font-size: 14px;
            margin-bottom: 20px;
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            padding-bottom: 15px;
            border-bottom: 1px solid #e0e0e0;
        }}
        
        .post-meta span {{
            display: flex;
            align-items: center;
            gap: 5px;
        }}
        
        .post-content {{
            color: #555;
            line-height: 1.8;
            margin-top: 15px;
            white-space: pre-wrap;
            word-wrap: break-word;
            font-size: 16px;
        }}
        
        .post-content p {{
            margin-bottom: 12px;
        }}
        
        .stats {{
            display: flex;
            gap: 20px;
            margin-top: 20px;
            padding-top: 15px;
            border-top: 1px solid #e0e0e0;
            font-size: 14px;
            color: #7f8c8d;
        }}
        
        .stats span {{
            display: flex;
            align-items: center;
            gap: 5px;
        }}
        
        .no-posts {{
            text-align: center;
            padding: 80px 20px;
            color: #7f8c8d;
        }}
        
        .no-posts h2 {{
            margin-bottom: 15px;
            color: #2c3e50;
            font-size: 2em;
        }}
        
        .no-posts p {{
            font-size: 1.1em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Special Participation B Posts</h1>
        <div class="meta">
            Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')} | 
            Total Posts: {len(threads)}
        </div>
"""
    
    if not threads:
        html_content += """
        <div class="no-posts">
            <h2>No posts found</h2>
            <p>No posts with titles containing "special participation b" were found.</p>
        </div>
"""
    else:
        # Sort threads by created_at (newest first)
        sorted_threads = sorted(
            threads,
            key=lambda x: x.get('created_at', ''),
            reverse=True
        )
        
        for thread in sorted_threads:
            title = escape_html(thread.get('title', 'Untitled'))
            
            # Get content - try document first, then content field
            raw_content = thread.get('document') or thread.get('content') or ''
            content = parse_thread_content(raw_content)
            content = escape_html(content)
            
            # Get author information
            author_info = thread.get('user', {})
            if isinstance(author_info, dict):
                author = author_info.get('name', author_info.get('username', 'Unknown'))
            else:
                author = str(author_info) if author_info else 'Unknown'
            author = escape_html(author)
            
            created = format_date(thread.get('created_at'))
            updated = format_date(thread.get('updated_at'))
            comment_count = thread.get('comment_count', 0) or thread.get('num_comments', 0)
            vote_count = thread.get('vote_count', 0) or thread.get('upvotes', 0) or thread.get('votes', 0)
            
            html_content += f"""
        <div class="post">
            <div class="post-title">{title}</div>
            <div class="post-meta">
                <span>👤 {author}</span>
                <span>📅 {created}</span>
            </div>
            <div class="post-content">{content}</div>
            <div class="stats">
                <span>💬 {comment_count} comments</span>
                <span>👍 {vote_count} votes</span>
            </div>
        </div>
"""
    
    html_content += """
    </div>
</body>
</html>
"""
    
    # Write the HTML file
    output_path = os.path.join(output_dir, 'index.html')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Static website generated successfully at {output_path}")
    return output_path


def main():
    """Main function to run the scraper and generate the static website."""
    
    # Validate configuration
    if not API_TOKEN:
        print("❌ Error: ED_API_TOKEN environment variable is not set")
        print("   Get your token from: https://edstem.org/us/settings/api-tokens")
        print("\n   Options:")
        print("   1. Export in your shell: export ED_API_TOKEN='your_token_here'")
        print("   2. Create a .env file with: ED_API_TOKEN=your_token_here")
        return
    
    if not COURSE_ID or COURSE_ID == 'YOUR_COURSE_ID_HERE':
        print("❌ Error: Please update COURSE_ID in the script with your actual course ID")
        return
    
    # Initialize EdAPI
    print("🔐 Authenticating with Ed API...")
    try:
        ed = EdAPI()
        ed.login()
        user_info = ed.get_user_info()
        user = user_info.get('user', {})
        print(f"✅ Authenticated as {user.get('name', 'User')}")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        print("   Please check your API token")
        return
    
    # Fetch threads with pagination to get ALL threads, not just recent ones
    print(f"📚 Fetching threads from course {COURSE_ID} (with pagination)...")
    all_threads = []
    page = 0
    page_size = 50
    seen_ids = set()
    
    try:
        # Use the session to make direct API calls with pagination
        base_url = "https://us.edstem.org/api/"
        
        while True:
            # The Ed API uses offset-based pagination
            offset = page * page_size
            url = f"{base_url}courses/{COURSE_ID}/threads?limit={page_size}&offset={offset}"
            
            response = ed.session.get(url, headers=ed._auth_header)
            response.raise_for_status()
            data = response.json()
            
            if not isinstance(data, dict):
                break
                
            page_threads = data.get("threads", [])
            
            if not page_threads:
                break
            
            # Filter out duplicates
            new_threads = [
                t for t in page_threads 
                if isinstance(t, dict) and t.get("id") not in seen_ids
            ]
            
            for thread in new_threads:
                thread_id = thread.get("id")
                if thread_id:
                    seen_ids.add(thread_id)
            
            all_threads.extend(new_threads)
            print(f"   Fetched page {page + 1}: {len(new_threads)} threads (total so far: {len(all_threads)})")
            
            # If we got fewer threads than page_size, we've reached the end
            if len(page_threads) < page_size:
                break
            
            page += 1
        
        threads = all_threads
        print(f"✅ Found {len(threads)} total threads (across {page + 1} pages)")
    except Exception as e:
        print(f"⚠️  Error with pagination, falling back to list_threads: {e}")
        try:
            threads = ed.list_threads(course_id=COURSE_ID)
            print(f"✅ Found {len(threads)} total threads (using list_threads - may be limited)")
        except Exception as e2:
            print(f"❌ Error fetching threads: {e2}")
            return
    
    # Filter threads by title
    print(f"🔍 Filtering threads with titles containing '{TITLE_FILTER}' (case-insensitive)...")
    filtered_threads = [
        thread for thread in threads
        if TITLE_FILTER.lower() in thread.get('title', '').lower()
    ]
    
    print(f"✅ Found {len(filtered_threads)} matching posts")
    
    if not filtered_threads:
        print("⚠️  No posts found matching the criteria")
        return
    
    # Fetch full thread details for each filtered thread
    print("📖 Fetching full thread details...")
    detailed_threads = []
    for thread in filtered_threads:
        try:
            thread_id = thread.get('id')
            if thread_id:
                # Get full thread details
                full_thread = ed.get_thread(thread_id=thread_id)
                if full_thread:
                    detailed_threads.append(full_thread)
        except Exception as e:
            print(f"⚠️  Error fetching thread {thread_id}: {e}")
            # Fall back to basic thread info
            detailed_threads.append(thread)
    
    print(f"✅ Retrieved details for {len(detailed_threads)} threads")
    
    # Generate static website
    print("🌐 Generating static website...")
    generate_static_website(detailed_threads, OUTPUT_DIR)
    
    print(f"\n🎉 Done! Your static website is ready in the '{OUTPUT_DIR}' directory")
    print(f"   Open {OUTPUT_DIR}/index.html in your browser to view it")
    print(f"   You can deploy the '{OUTPUT_DIR}' directory to any static hosting service")


if __name__ == '__main__':
    main()

