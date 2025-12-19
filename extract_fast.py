#!/usr/bin/env python3
"""
Fast extraction of PDFs from Special Participation B posts only.
Uses parallel downloads with progress bar.
"""

import os
import re
import json
import sys
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
warnings.filterwarnings('ignore')

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

OUTPUT_DIR = "output"
PDF_DIR = os.path.join(OUTPUT_DIR, "pdfs")
HEADERS = {'User-Agent': 'Mozilla/5.0'}


def progress_bar(current, total, prefix='', width=40):
    """Simple progress bar."""
    percent = current / total if total > 0 else 1
    filled = int(width * percent)
    bar = '█' * filled + '░' * (width - filled)
    sys.stdout.write(f'\r{prefix} |{bar}| {current}/{total} ({percent*100:.0f}%)')
    sys.stdout.flush()


def download_file(args):
    """Download a single file."""
    url, thread_id, filepath = args
    
    try:
        if os.path.exists(filepath):
            return filepath, None, True  # Already exists
        
        # Convert Google Drive URL
        if 'drive.google.com' in url:
            match = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
            if match:
                url = f"https://drive.google.com/uc?export=download&id={match.group(1)}&confirm=1"
            else:
                return None, "Bad URL", False
        
        response = requests.get(url, headers=HEADERS, timeout=20)
        
        if response.status_code != 200:
            return None, f"HTTP {response.status_code}", False
        
        # Check if PDF
        if response.content[:5] != b'%PDF-':
            return None, "Not PDF", False
        
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        return filepath, None, False
        
    except Exception as e:
        return None, str(e)[:30], False


def extract_text(filepath):
    """Extract text from PDF."""
    if not pdfplumber or not filepath or not os.path.exists(filepath):
        return ""
    try:
        text = ""
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages[:30]:  # Max 30 pages
                t = page.extract_text()
                if t:
                    text += t + "\n"
        return text.strip()
    except:
        return ""


def main():
    print("🚀 Fast PDF Extraction (Special Participation B only)")
    print("=" * 55)
    
    os.makedirs(PDF_DIR, exist_ok=True)
    
    # Load threads_full_raw.json (has the raw content with file tags)
    raw_path = os.path.join(OUTPUT_DIR, 'threads_full_raw.json')
    
    if not os.path.exists(raw_path):
        print("❌ No data. Run generate_site.py first.")
        return
    
    with open(raw_path, 'r') as f:
        posts = json.load(f)
    
    print(f"📂 Loaded {len(posts)} Special Participation B posts")
    
    # Extract file URLs
    download_tasks = []
    seen = set()
    
    for post in posts:
        tid = post.get('id')
        content = post.get('content', '') + ' ' + post.get('document', '')
        
        # Ed-hosted files
        for url in re.findall(r'<file[^>]*url="([^"]+)"', content):
            if url not in seen:
                seen.add(url)
                fhash = url.split('/')[-1][:15]
                download_tasks.append((url, tid, os.path.join(PDF_DIR, f"{tid}_{fhash}.pdf")))
        
        # Google Drive files
        for url in re.findall(r'https://drive\.google\.com/file/d/[a-zA-Z0-9_-]+', content):
            if url not in seen:
                seen.add(url)
                match = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
                fhash = match.group(1)[:15] if match else 'unk'
                download_tasks.append((url, tid, os.path.join(PDF_DIR, f"{tid}_{fhash}.pdf")))
    
    print(f"📁 Found {len(download_tasks)} unique files")
    
    # Check how many already exist
    existing = sum(1 for _, _, fp in download_tasks if os.path.exists(fp))
    to_download = len(download_tasks) - existing
    print(f"   ✓ Already downloaded: {existing}")
    print(f"   → To download: {to_download}")
    
    if to_download == 0 and existing > 0:
        print("\n✅ All files already downloaded!")
    else:
        # Download in parallel
        print(f"\n📥 Downloading...")
        
        downloaded = 0
        skipped = 0
        failed = 0
        
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(download_file, task) for task in download_tasks]
            
            for i, future in enumerate(as_completed(futures)):
                filepath, error, was_cached = future.result()
                
                if was_cached:
                    pass  # Already counted
                elif filepath:
                    downloaded += 1
                elif error == "Not PDF":
                    skipped += 1
                else:
                    failed += 1
                
                progress_bar(i + 1, len(download_tasks), "   Progress")
        
        print()  # New line after progress bar
        print(f"   ✅ New downloads: {downloaded}")
        print(f"   ⏭️  Skipped (not PDF): {skipped}")
        print(f"   ❌ Failed: {failed}")
    
    # Extract text from all PDFs
    print(f"\n📖 Extracting text from PDFs...")
    
    extractions = []
    pdf_files = [(t[0], t[1], t[2]) for t in download_tasks if os.path.exists(t[2])]
    
    # Get post titles
    post_titles = {p.get('id'): p.get('title', '') for p in posts}
    
    for i, (url, tid, filepath) in enumerate(pdf_files):
        progress_bar(i + 1, len(pdf_files), "   Progress")
        
        text = extract_text(filepath)
        if text and len(text) > 100:  # Only keep substantial content
            extractions.append({
                'thread_id': tid,
                'title': post_titles.get(tid, ''),
                'url': url,
                'content': text,
                'char_count': len(text)
            })
    
    print()  # New line
    
    # Save results
    with open(os.path.join(OUTPUT_DIR, 'all_extractions.json'), 'w') as f:
        json.dump(extractions, f, indent=2, ensure_ascii=False)
    
    # Group by post for pdf_extractions.json
    by_post = {}
    for ext in extractions:
        tid = ext['thread_id']
        if tid not in by_post:
            by_post[tid] = {'post_id': tid, 'post_title': ext['title'], 'pdfs': []}
        by_post[tid]['pdfs'].append({
            'url': ext['url'],
            'text': ext['content'],
            'char_count': ext['char_count']
        })
    
    with open(os.path.join(OUTPUT_DIR, 'pdf_extractions.json'), 'w') as f:
        json.dump(list(by_post.values()), f, indent=2, ensure_ascii=False)
    
    total_chars = sum(e['char_count'] for e in extractions)
    
    print(f"\n{'='*55}")
    print(f"📊 Summary:")
    print(f"   PDFs with extractable text: {len(extractions)}")
    print(f"   Posts with PDF content: {len(by_post)}")
    print(f"   Total extracted: {total_chars:,} characters")
    print(f"   Saved to: output/all_extractions.json")


if __name__ == '__main__':
    main()
