#!/usr/bin/env python3
"""
Simple script to scrape Ed forum posts and generate a static website.
No CLI arguments needed - just update the configuration below.
"""

import os
from datetime import datetime
from edapi import EdAPI

# ============================================================================
# CONFIGURATION - Update these values
# ============================================================================

# Get your API token from: https://edstem.org/us/settings/api-tokens
# You can set it as an environment variable ED_API_TOKEN or paste it here
API_TOKEN = os.getenv('ED_API_TOKEN', 'YOUR_API_TOKEN_HERE')

# Your course ID (you can find this in the Ed forum URL)
COURSE_ID = 'YOUR_COURSE_ID_HERE'

# Title prefix to filter posts
TITLE_PREFIX = "Special Participation B: "

# Output directory for the static website
OUTPUT_DIR = "output"

# ============================================================================
# END CONFIGURATION
# ============================================================================


def generate_static_website(threads, output_dir="output"):
    """
    Generate a static HTML website from the scraped threads.
    
    Args:
        threads: List of thread dictionaries
        output_dir: Directory to output the static website
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Escape HTML in content
    def escape_html(text):
        if not text:
            return ""
        return (str(text)
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#x27;'))
    
    # Format date
    def format_date(date_str):
        if not date_str:
            return "Unknown date"
        try:
            # Try parsing ISO format
            if isinstance(date_str, str):
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                return dt.strftime('%B %d, %Y at %I:%M %p')
        except:
            pass
        return str(date_str)
    
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
            <p>No posts with titles starting with "Special Participation B: " were found.</p>
        </div>
"""
    else:
        for thread in threads:
            title = escape_html(thread.get('title', 'Untitled'))
            body = escape_html(thread.get('content', '') or thread.get('body', 'No content available'))
            
            # Get author information
            author_info = thread.get('user', {})
            if isinstance(author_info, dict):
                author = author_info.get('name', author_info.get('username', 'Unknown'))
            else:
                author = str(author_info) if author_info else 'Unknown'
            
            created = format_date(thread.get('created_at') or thread.get('created'))
            updated = thread.get('updated_at') or thread.get('updated')
            comment_count = thread.get('comment_count', 0) or thread.get('num_comments', 0)
            vote_count = thread.get('vote_count', 0) or thread.get('upvotes', 0) or thread.get('votes', 0)
            
            html_content += f"""
        <div class="post">
            <div class="post-title">{title}</div>
            <div class="post-meta">
                <span>👤 {escape_html(author)}</span>
                <span>📅 {created}</span>
            </div>
            <div class="post-content">{body}</div>
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
    if API_TOKEN == 'YOUR_API_TOKEN_HERE' or not API_TOKEN:
        print("❌ Error: Please set your ED_API_TOKEN environment variable or update API_TOKEN in the script")
        print("   Get your token from: https://edstem.org/us/settings/api-tokens")
        return
    
    if COURSE_ID == 'YOUR_COURSE_ID_HERE' or not COURSE_ID:
        print("❌ Error: Please update COURSE_ID in the script with your actual course ID")
        return
    
    # Initialize EdAPI
    print("🔐 Authenticating with Ed API...")
    try:
        ed = EdAPI(API_TOKEN)
        user_info = ed.get_user_info()
        user = user_info.get('user', {})
        print(f"✅ Authenticated as {user.get('name', 'User')}")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        print("   Please check your API token")
        return
    
    # Fetch threads
    print(f"📚 Fetching threads from course {COURSE_ID}...")
    try:
        threads = ed.list_threads(course_id=COURSE_ID)
        print(f"✅ Found {len(threads)} total threads")
    except Exception as e:
        print(f"❌ Error fetching threads: {e}")
        return
    
    # Filter threads by title prefix
    print(f"🔍 Filtering threads with titles starting with '{TITLE_PREFIX}'...")
    filtered_threads = [
        thread for thread in threads
        if thread.get('title', '').startswith(TITLE_PREFIX)
    ]
    
    print(f"✅ Found {len(filtered_threads)} matching posts")
    
    if not filtered_threads:
        print("⚠️  No posts found matching the criteria")
    
    # Generate static website
    print("🌐 Generating static website...")
    generate_static_website(filtered_threads, OUTPUT_DIR)
    
    print(f"\n🎉 Done! Your static website is ready in the '{OUTPUT_DIR}' directory")
    print(f"   Open {OUTPUT_DIR}/index.html in your browser to view it")
    print(f"   You can deploy the '{OUTPUT_DIR}' directory to any static hosting service")


if __name__ == '__main__':
    main()

