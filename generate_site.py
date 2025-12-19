#!/usr/bin/env python3
"""
One-time script to scrape Ed forum posts and generate a static website.
Fetches posts with titles containing "special participation b" and displays them
with filtering by model and homework.
"""

import os
import re
import json
from datetime import datetime
from pathlib import Path
from collections import defaultdict

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
# MODEL AND HOMEWORK EXTRACTION
# ============================================================================

# Known model patterns (case-insensitive)
MODEL_PATTERNS = [
    # ChatGPT / GPT variants
    (r'chatgpt[\s\-]*o?[1-4]?[\s\-]*(?:mini|pro|plus)?(?:[\s\-]*thinking)?', 'ChatGPT'),
    (r'gpt[\s\-]*[4-5][\.\d]*(?:[\s\-]*o)?(?:[\s\-]*mini|turbo|thinking)?', 'GPT'),
    (r'chatgpt[\s\-]*[4-5][\.\d]*(?:[\s\-]*thinking)?', 'ChatGPT'),
    (r'o[1-4](?:[\s\-]*(?:mini|pro|preview))?', 'OpenAI o1/o3'),
    
    # Claude variants
    (r'claude[\s\-]*(?:sonnet|opus|haiku)?[\s\-]*[3-4]?[\.\d]*(?:[\s\-]*thinking)?', 'Claude'),
    (r'sonnet[\s\-]*[3-4]?[\.\d]*', 'Claude'),
    (r'opus[\s\-]*[3-4]?[\.\d]*', 'Claude'),
    (r'claude[\s\-]*code', 'Claude Code'),
    
    # Gemini variants
    (r'gemini[\s\-]*(?:pro|ultra|flash|advanced)?[\s\-]*[1-3]?[\.\d]*', 'Gemini'),
    (r'bard', 'Gemini'),
    
    # Deepseek variants
    (r'deep[\s\-]*seek[\s\-]*(?:v[\d\.]+)?(?:[\s\-]*(?:coder|r1))?', 'DeepSeek'),
    (r'deepseek[\s\-]*(?:v[\d\.]+)?(?:[\s\-]*(?:coder|r1))?', 'DeepSeek'),
    
    # Cursor / Windsurf
    (r'cursor(?:[\s\-]*(?:composer|agent))?', 'Cursor'),
    (r'windsurf(?:[\s\-]*swe[\s\-]*\d*)?', 'Windsurf'),
    (r'composer(?:[\s\-]*model)?(?:[\s\-]*\d+)?', 'Cursor'),
    
    # Codex
    (r'codex[\s\-]*[1-5]?[\.\d]*(?:[\s\-]*(?:high|low|medium))?', 'Codex'),
    
    # Qwen
    (r'qwen[\s\-]*[1-3]?[\.\d]*(?:[\s\-]*(?:max|plus|turbo))?(?:[\s\-]*(?:thinking))?', 'Qwen'),
    
    # Perplexity
    (r'perplexity(?:[\s\-]*(?:pro|sonar))?', 'Perplexity'),
    
    # Mistral
    (r'mistral(?:[\s\-]*(?:large|medium|small|nemo))?', 'Mistral'),
    (r'mixtral', 'Mistral'),
    (r'codestral', 'Mistral'),
    (r'le[\s\-]*chat', 'Mistral'),
    
    # Llama
    (r'llama[\s\-]*[1-4]?[\.\d]*', 'Llama'),
    (r'meta[\s\-]*ai', 'Llama'),
    
    # Copilot
    (r'github[\s\-]*copilot', 'Copilot'),
    (r'copilot', 'Copilot'),
    
    # Other
    (r'grok[\s\-]*[1-3]?', 'Grok'),
    (r'cohere[\s\-]*(?:command)?', 'Cohere'),
    (r'anthropic', 'Claude'),
    (r'openai', 'OpenAI'),
    (r'google[\s\-]*ai[\s\-]*studio', 'Gemini'),
    (r'aider', 'Aider'),
    (r'cline', 'Cline'),
    (r'replit[\s\-]*(?:agent|ai)?', 'Replit'),
]

# Homework pattern
HW_PATTERN = r'hw[\s\-_]*0*(\d+)|homework[\s\-_]*0*(\d+)'


def extract_model(title, content):
    """Extract model name from title and content."""
    text = f"{title} {content}".lower()
    
    for pattern, model_name in MODEL_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return model_name
    
    return "Unknown"


def extract_homework(title, content):
    """Extract homework number from title and content."""
    text = f"{title} {content}"
    
    matches = re.findall(HW_PATTERN, text, re.IGNORECASE)
    for match in matches:
        hw_num = match[0] or match[1]
        if hw_num:
            return f"HW{int(hw_num)}"
    
    return "Unknown"


def extract_failure_modes(content):
    """Extract common failure modes mentioned in the post."""
    failure_keywords = {
        'hallucination': ['hallucinate', 'hallucination', 'made up', 'fabricate', 'incorrect fact'],
        'context_loss': ['lost context', 'forgot', 'context window', 'lost track', 'context limit'],
        'wrong_algorithm': ['wrong algorithm', 'misunderstood', 'wrong approach', 'misinterpreted'],
        'syntax_error': ['syntax error', 'syntactically incorrect', 'typo', 'missing bracket'],
        'api_confusion': ['wrong api', 'api confusion', 'wrong function', 'wrong library', 'imported function'],
        'off_topic': ['off topic', 'unrelated', 'tangent', 'missed the point'],
        'incomplete': ['incomplete', 'unfinished', 'partial', 'missing part'],
        'overcomplicated': ['overcomplicated', 'over-engineered', 'too complex', 'unnecessarily complex'],
        'wrong_dimensions': ['wrong dimension', 'shape error', 'dimension mismatch', 'broadcasting'],
        'numerical_error': ['numerical error', 'precision', 'floating point', 'numerical instability'],
    }
    
    found_failures = []
    content_lower = content.lower()
    
    for failure_type, keywords in failure_keywords.items():
        for keyword in keywords:
            if keyword in content_lower:
                found_failures.append(failure_type)
                break
    
    return found_failures


def analyze_outcome(content):
    """Analyze if the model succeeded, partially succeeded, or failed."""
    content_lower = content.lower()
    
    success_indicators = ['one-shot', 'one shot', 'correctly', 'succeeded', 'worked well', 
                          'was able to', 'impressive', 'correct answer', 'passed all tests',
                          'zero-shot', 'nailed', 'spot on', 'performed well']
    failure_indicators = ['failed', 'struggled', 'incorrect', 'wrong', 'error', 'bug',
                          'did not work', 'couldn\'t', 'unable to', 'mistake']
    partial_indicators = ['eventually', 'after', 'with some', 'needed help', 'required',
                          'with guidance', 'minor', 'mostly']
    
    success_count = sum(1 for ind in success_indicators if ind in content_lower)
    failure_count = sum(1 for ind in failure_indicators if ind in content_lower)
    partial_count = sum(1 for ind in partial_indicators if ind in content_lower)
    
    if failure_count > success_count:
        return 'failed'
    elif partial_count > 0 and failure_count > 0:
        return 'partial'
    elif success_count > 0:
        return 'success'
    return 'unknown'


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
    Generate a static HTML website from the scraped threads with filtering.
    
    Args:
        threads: List of thread dictionaries
        output_dir: Directory to output the static website
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Process threads to extract metadata
    processed_threads = []
    models = set()
    homeworks = set()
    model_stats = defaultdict(lambda: {'total': 0, 'success': 0, 'partial': 0, 'failed': 0, 'unknown': 0})
    hw_stats = defaultdict(lambda: {'total': 0, 'success': 0, 'partial': 0, 'failed': 0, 'unknown': 0})
    failure_mode_counts = defaultdict(int)
    
    for thread in threads:
        title = thread.get('title', 'Untitled')
        raw_content = thread.get('document') or thread.get('content') or ''
        content = parse_thread_content(raw_content)
        
        model = extract_model(title, content)
        homework = extract_homework(title, content)
        failure_modes = extract_failure_modes(content)
        outcome = analyze_outcome(content)
        
        models.add(model)
        homeworks.add(homework)
        
        # Update stats
        model_stats[model]['total'] += 1
        model_stats[model][outcome] += 1
        hw_stats[homework]['total'] += 1
        hw_stats[homework][outcome] += 1
        
        for fm in failure_modes:
            failure_mode_counts[fm] += 1
        
        processed_threads.append({
            'title': title,
            'content': content,
            'model': model,
            'homework': homework,
            'failure_modes': failure_modes,
            'outcome': outcome,
            'author': thread.get('user', {}).get('name', 'Unknown') if isinstance(thread.get('user'), dict) else 'Unknown',
            'created_at': thread.get('created_at', ''),
            'comment_count': thread.get('comment_count', 0) or thread.get('num_comments', 0),
            'vote_count': thread.get('vote_count', 0) or thread.get('upvotes', 0) or thread.get('votes', 0),
        })
    
    # Sort threads
    sorted_threads = sorted(processed_threads, key=lambda x: x.get('created_at', ''), reverse=True)
    
    # Sort models and homeworks for display
    sorted_models = sorted([m for m in models if m != 'Unknown']) + (['Unknown'] if 'Unknown' in models else [])
    
    def hw_sort_key(hw):
        if hw == 'Unknown':
            return (1, 999)
        match = re.search(r'(\d+)', hw)
        return (0, int(match.group(1)) if match else 999)
    
    sorted_homeworks = sorted([h for h in homeworks], key=hw_sort_key)
    
    # Generate JavaScript data
    threads_json = json.dumps(sorted_threads, default=str)
    
    # Create failure mode labels
    failure_mode_labels = {
        'hallucination': 'Hallucination',
        'context_loss': 'Context Loss',
        'wrong_algorithm': 'Wrong Algorithm',
        'syntax_error': 'Syntax Error',
        'api_confusion': 'API Confusion',
        'off_topic': 'Off Topic',
        'incomplete': 'Incomplete',
        'overcomplicated': 'Overcomplicated',
        'wrong_dimensions': 'Dimension Errors',
        'numerical_error': 'Numerical Errors',
    }
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Model Failure Analysis | EECS 182 Special Participation B</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-dark: #0a0a0f;
            --bg-card: #12121a;
            --bg-card-hover: #1a1a25;
            --accent-primary: #00d4aa;
            --accent-secondary: #7c3aed;
            --accent-tertiary: #f43f5e;
            --accent-warning: #fbbf24;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --border-color: #1e293b;
            --success: #10b981;
            --partial: #f59e0b;
            --failed: #ef4444;
            --glass-bg: rgba(18, 18, 26, 0.8);
            --glass-border: rgba(255, 255, 255, 0.05);
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Outfit', sans-serif;
            line-height: 1.6;
            color: var(--text-primary);
            background: var(--bg-dark);
            min-height: 100vh;
            overflow-x: hidden;
        }}
        
        /* Animated background */
        .bg-pattern {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 0;
            background: 
                radial-gradient(ellipse 80% 50% at 50% -20%, rgba(124, 58, 237, 0.15), transparent),
                radial-gradient(ellipse 60% 40% at 100% 50%, rgba(0, 212, 170, 0.08), transparent),
                radial-gradient(ellipse 50% 30% at 0% 80%, rgba(244, 63, 94, 0.08), transparent);
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 40px 24px;
            position: relative;
            z-index: 1;
        }}
        
        /* Header */
        header {{
            text-align: center;
            margin-bottom: 48px;
            animation: fadeInDown 0.6s ease-out;
        }}
        
        @keyframes fadeInDown {{
            from {{
                opacity: 0;
                transform: translateY(-20px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}
        
        h1 {{
            font-size: clamp(2rem, 5vw, 3.5rem);
            font-weight: 700;
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 12px;
            letter-spacing: -0.02em;
        }}
        
        .subtitle {{
            color: var(--text-secondary);
            font-size: 1.1rem;
            font-weight: 300;
        }}
        
        .meta-info {{
            display: flex;
            justify-content: center;
            gap: 24px;
            margin-top: 16px;
            flex-wrap: wrap;
        }}
        
        .meta-badge {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            background: var(--glass-bg);
            border: 1px solid var(--glass-border);
            border-radius: 100px;
            font-size: 0.875rem;
            color: var(--text-secondary);
            backdrop-filter: blur(10px);
        }}
        
        .meta-badge span {{
            color: var(--accent-primary);
            font-weight: 600;
            font-family: 'JetBrains Mono', monospace;
        }}
        
        /* Stats Dashboard */
        .dashboard {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
            animation: fadeIn 0.6s ease-out 0.2s both;
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        .stat-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 24px;
            transition: all 0.3s ease;
        }}
        
        .stat-card:hover {{
            border-color: var(--accent-primary);
            transform: translateY(-2px);
            box-shadow: 0 8px 32px rgba(0, 212, 170, 0.1);
        }}
        
        .stat-card h3 {{
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--text-muted);
            margin-bottom: 16px;
        }}
        
        .stat-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
        }}
        
        .stat-item {{
            text-align: center;
            padding: 12px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 8px;
        }}
        
        .stat-value {{
            font-size: 1.5rem;
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
            color: var(--accent-primary);
        }}
        
        .stat-label {{
            font-size: 0.75rem;
            color: var(--text-muted);
            margin-top: 4px;
        }}
        
        /* Failure Modes Section */
        .failure-modes-section {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 40px;
            animation: fadeIn 0.6s ease-out 0.3s both;
        }}
        
        .failure-modes-section h2 {{
            font-size: 1.25rem;
            margin-bottom: 20px;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .failure-bars {{
            display: grid;
            gap: 12px;
        }}
        
        .failure-bar {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        
        .failure-bar-label {{
            width: 140px;
            font-size: 0.875rem;
            color: var(--text-secondary);
            flex-shrink: 0;
        }}
        
        .failure-bar-track {{
            flex: 1;
            height: 24px;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 4px;
            overflow: hidden;
        }}
        
        .failure-bar-fill {{
            height: 100%;
            background: linear-gradient(90deg, var(--accent-tertiary), var(--accent-secondary));
            border-radius: 4px;
            transition: width 0.8s ease-out;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            padding-right: 8px;
        }}
        
        .failure-bar-count {{
            font-size: 0.75rem;
            font-family: 'JetBrains Mono', monospace;
            color: white;
            font-weight: 600;
        }}
        
        /* Filters */
        .filters {{
            display: flex;
            gap: 16px;
            margin-bottom: 32px;
            flex-wrap: wrap;
            animation: fadeIn 0.6s ease-out 0.4s both;
        }}
        
        .filter-group {{
            flex: 1;
            min-width: 200px;
        }}
        
        .filter-label {{
            display: block;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--text-muted);
            margin-bottom: 8px;
        }}
        
        .filter-select {{
            width: 100%;
            padding: 12px 16px;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            color: var(--text-primary);
            font-family: 'Outfit', sans-serif;
            font-size: 0.95rem;
            cursor: pointer;
            transition: all 0.2s ease;
            appearance: none;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E");
            background-repeat: no-repeat;
            background-position: right 12px center;
            background-size: 16px;
            padding-right: 40px;
        }}
        
        .filter-select:hover {{
            border-color: var(--accent-primary);
        }}
        
        .filter-select:focus {{
            outline: none;
            border-color: var(--accent-primary);
            box-shadow: 0 0 0 3px rgba(0, 212, 170, 0.1);
        }}
        
        .filter-select option {{
            background: var(--bg-card);
            color: var(--text-primary);
        }}
        
        .search-input {{
            width: 100%;
            padding: 12px 16px;
            padding-left: 44px;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            color: var(--text-primary);
            font-family: 'Outfit', sans-serif;
            font-size: 0.95rem;
            transition: all 0.2s ease;
        }}
        
        .search-wrapper {{
            position: relative;
        }}
        
        .search-icon {{
            position: absolute;
            left: 14px;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-muted);
        }}
        
        .search-input:hover {{
            border-color: var(--accent-primary);
        }}
        
        .search-input:focus {{
            outline: none;
            border-color: var(--accent-primary);
            box-shadow: 0 0 0 3px rgba(0, 212, 170, 0.1);
        }}
        
        .results-count {{
            font-size: 0.875rem;
            color: var(--text-muted);
            margin-bottom: 20px;
        }}
        
        .results-count span {{
            color: var(--accent-primary);
            font-weight: 600;
        }}
        
        /* Posts Grid */
        .posts-grid {{
            display: grid;
            gap: 20px;
        }}
        
        .post {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 28px;
            transition: all 0.3s ease;
            animation: fadeIn 0.4s ease-out both;
        }}
        
        .post:hover {{
            border-color: var(--accent-secondary);
            background: var(--bg-card-hover);
            transform: translateY(-2px);
            box-shadow: 0 12px 40px rgba(124, 58, 237, 0.08);
        }}
        
        .post-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 16px;
            margin-bottom: 16px;
            flex-wrap: wrap;
        }}
        
        .post-title {{
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--text-primary);
            line-height: 1.4;
            flex: 1;
        }}
        
        .post-tags {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }}
        
        .tag {{
            padding: 4px 12px;
            border-radius: 100px;
            font-size: 0.75rem;
            font-weight: 500;
            font-family: 'JetBrains Mono', monospace;
        }}
        
        .tag-model {{
            background: rgba(124, 58, 237, 0.15);
            color: #a78bfa;
            border: 1px solid rgba(124, 58, 237, 0.3);
        }}
        
        .tag-hw {{
            background: rgba(0, 212, 170, 0.15);
            color: var(--accent-primary);
            border: 1px solid rgba(0, 212, 170, 0.3);
        }}
        
        .tag-outcome {{
            font-size: 0.7rem;
        }}
        
        .tag-success {{
            background: rgba(16, 185, 129, 0.15);
            color: var(--success);
            border: 1px solid rgba(16, 185, 129, 0.3);
        }}
        
        .tag-partial {{
            background: rgba(245, 158, 11, 0.15);
            color: var(--partial);
            border: 1px solid rgba(245, 158, 11, 0.3);
        }}
        
        .tag-failed {{
            background: rgba(239, 68, 68, 0.15);
            color: var(--failed);
            border: 1px solid rgba(239, 68, 68, 0.3);
        }}
        
        .post-meta {{
            display: flex;
            gap: 16px;
            flex-wrap: wrap;
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-bottom: 16px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border-color);
        }}
        
        .post-meta-item {{
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        
        .post-content {{
            color: var(--text-secondary);
            font-size: 0.95rem;
            line-height: 1.8;
            max-height: 200px;
            overflow: hidden;
            position: relative;
        }}
        
        .post-content.expanded {{
            max-height: none;
        }}
        
        .post-content::after {{
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 60px;
            background: linear-gradient(transparent, var(--bg-card));
            pointer-events: none;
        }}
        
        .post-content.expanded::after {{
            display: none;
        }}
        
        .expand-btn {{
            margin-top: 12px;
            padding: 8px 16px;
            background: transparent;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            color: var(--text-secondary);
            font-family: 'Outfit', sans-serif;
            font-size: 0.85rem;
            cursor: pointer;
            transition: all 0.2s ease;
        }}
        
        .expand-btn:hover {{
            border-color: var(--accent-primary);
            color: var(--accent-primary);
        }}
        
        .failure-tags {{
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
            margin-top: 12px;
        }}
        
        .failure-tag {{
            padding: 3px 10px;
            background: rgba(244, 63, 94, 0.1);
            border: 1px solid rgba(244, 63, 94, 0.2);
            border-radius: 4px;
            font-size: 0.7rem;
            color: var(--accent-tertiary);
            font-family: 'JetBrains Mono', monospace;
        }}
        
        .post-footer {{
            display: flex;
            gap: 16px;
            margin-top: 16px;
            padding-top: 16px;
            border-top: 1px solid var(--border-color);
            font-size: 0.85rem;
            color: var(--text-muted);
        }}
        
        .no-posts {{
            text-align: center;
            padding: 80px 20px;
            color: var(--text-muted);
        }}
        
        .no-posts h2 {{
            font-size: 1.5rem;
            margin-bottom: 8px;
            color: var(--text-secondary);
        }}
        
        /* Homework Sections */
        .homework-section {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            margin-bottom: 24px;
            overflow: hidden;
            animation: fadeIn 0.4s ease-out both;
        }}
        
        .homework-header {{
            padding: 24px 28px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: all 0.3s ease;
            background: var(--bg-card);
            border-bottom: 1px solid transparent;
        }}
        
        .homework-header:hover {{
            background: var(--bg-card-hover);
            border-bottom-color: var(--border-color);
        }}
        
        .homework-section.expanded .homework-header {{
            border-bottom-color: var(--border-color);
            background: var(--bg-card-hover);
        }}
        
        .homework-title {{
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 1.4rem;
            font-weight: 600;
            color: var(--text-primary);
        }}
        
        .homework-badge {{
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            color: white;
            padding: 6px 14px;
            border-radius: 100px;
            font-size: 0.85rem;
            font-weight: 600;
            font-family: 'JetBrains Mono', monospace;
        }}
        
        .homework-arrow {{
            font-size: 1.2rem;
            color: var(--text-muted);
            transition: transform 0.3s ease;
        }}
        
        .homework-section.expanded .homework-arrow {{
            transform: rotate(180deg);
        }}
        
        .homework-posts {{
            display: none;
            padding: 20px;
            gap: 20px;
        }}
        
        .homework-section.expanded .homework-posts {{
            display: grid;
        }}
        
        .homework-posts .post {{
            margin-bottom: 0;
        }}
        
        /* Dynamic Summary Section */
        .dynamic-summary {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 24px;
            animation: fadeIn 0.4s ease-out;
        }}
        
        .dynamic-summary.model-summary {{
            border-left: 4px solid var(--accent-secondary);
        }}
        
        .dynamic-summary.hw-summary {{
            border-left: 4px solid var(--accent-primary);
        }}
        
        .dynamic-summary.overall-summary {{
            border-left: 4px solid var(--accent-tertiary);
        }}
        
        .summary-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 20px;
        }}
        
        .summary-header h2 {{
            font-size: 1.25rem;
            color: var(--text-primary);
            margin: 0;
        }}
        
        .summary-header .summary-icon {{
            font-size: 1.5rem;
        }}
        
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 20px;
        }}
        
        .summary-metric {{
            background: rgba(0, 0, 0, 0.2);
            border-radius: 10px;
            padding: 16px;
            text-align: center;
        }}
        
        .summary-metric-value {{
            font-size: 2rem;
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
            margin-bottom: 4px;
        }}
        
        .summary-metric-label {{
            font-size: 0.8rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        
        .success-rate {{
            color: var(--success);
        }}
        
        .partial-rate {{
            color: var(--partial);
        }}
        
        .fail-rate {{
            color: var(--failed);
        }}
        
        .summary-details {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
        }}
        
        .summary-detail-card {{
            background: rgba(0, 0, 0, 0.15);
            border-radius: 10px;
            padding: 16px;
        }}
        
        .summary-detail-card h4 {{
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--text-muted);
            margin-bottom: 12px;
        }}
        
        .summary-list {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        
        .summary-list li {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid var(--border-color);
            font-size: 0.9rem;
        }}
        
        .summary-list li:last-child {{
            border-bottom: none;
        }}
        
        .summary-list-name {{
            color: var(--text-secondary);
        }}
        
        .summary-list-value {{
            font-family: 'JetBrains Mono', monospace;
            font-weight: 600;
            color: var(--accent-primary);
        }}
        
        .summary-insight {{
            background: rgba(124, 58, 237, 0.1);
            border: 1px solid rgba(124, 58, 237, 0.2);
            border-radius: 8px;
            padding: 16px;
            margin-top: 16px;
        }}
        
        .summary-insight h4 {{
            font-size: 0.85rem;
            color: #a78bfa;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .summary-insight p {{
            font-size: 0.9rem;
            color: var(--text-secondary);
            line-height: 1.6;
            margin: 0;
        }}
        
        .mini-bar {{
            display: flex;
            height: 8px;
            border-radius: 4px;
            overflow: hidden;
            background: rgba(0, 0, 0, 0.3);
            margin-top: 12px;
        }}
        
        .mini-bar-segment {{
            height: 100%;
            transition: width 0.5s ease;
        }}
        
        .mini-bar-success {{
            background: var(--success);
        }}
        
        .mini-bar-partial {{
            background: var(--partial);
        }}
        
        .mini-bar-failed {{
            background: var(--failed);
        }}
        
        .mini-bar-unknown {{
            background: var(--text-muted);
        }}
        
        /* Responsive */
        @media (max-width: 768px) {{
            .container {{
                padding: 24px 16px;
            }}
            
            .filters {{
                flex-direction: column;
            }}
            
            .filter-group {{
                min-width: 100%;
            }}
            
            .post-header {{
                flex-direction: column;
            }}
            
            .dashboard {{
                grid-template-columns: 1fr;
            }}
        }}
        
        /* Animations for posts */
        .post[data-index] {{
            animation-delay: calc(var(--index) * 0.05s);
        }}
    </style>
</head>
<body>
    <div class="bg-pattern"></div>
    <div class="container">
        <header>
            <h1>AI Model Failure Analysis</h1>
            <p class="subtitle">EECS 182 Special Participation B - Exploring LLM Performance on Homework</p>
            <div class="meta-info">
                <div class="meta-badge">
                    📊 <span>{len(threads)}</span> posts analyzed
                </div>
                <div class="meta-badge">
                    🤖 <span>{len(sorted_models)}</span> models tested
                </div>
                <div class="meta-badge">
                    📚 <span>{len([h for h in sorted_homeworks if h != 'Unknown'])}</span> homeworks covered
                </div>
            </div>
        </header>
        
        <!-- Stats Dashboard -->
        <div class="dashboard">
            <div class="stat-card">
                <h3>Overall Outcomes</h3>
                <div class="stat-grid">
                    <div class="stat-item">
                        <div class="stat-value" style="color: var(--success)">{sum(1 for t in processed_threads if t['outcome'] == 'success')}</div>
                        <div class="stat-label">Success</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" style="color: var(--partial)">{sum(1 for t in processed_threads if t['outcome'] == 'partial')}</div>
                        <div class="stat-label">Partial</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" style="color: var(--failed)">{sum(1 for t in processed_threads if t['outcome'] == 'failed')}</div>
                        <div class="stat-label">Failed</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" style="color: var(--text-muted)">{sum(1 for t in processed_threads if t['outcome'] == 'unknown')}</div>
                        <div class="stat-label">Unknown</div>
                    </div>
                </div>
            </div>
            
            <div class="stat-card">
                <h3>Top Models by Posts</h3>
                <div class="stat-grid">
                    {"".join(f'''<div class="stat-item">
                        <div class="stat-value">{stats["total"]}</div>
                        <div class="stat-label">{model[:12]}</div>
                    </div>''' for model, stats in sorted(model_stats.items(), key=lambda x: x[1]['total'], reverse=True)[:4])}
                </div>
            </div>
            
            <div class="stat-card">
                <h3>Top Homeworks</h3>
                <div class="stat-grid">
                    {"".join(f'''<div class="stat-item">
                        <div class="stat-value">{stats["total"]}</div>
                        <div class="stat-label">{hw}</div>
                    </div>''' for hw, stats in sorted(hw_stats.items(), key=lambda x: x[1]['total'], reverse=True)[:4])}
                </div>
            </div>
        </div>
        
        <!-- Failure Modes Section -->
        <div class="failure-modes-section">
            <h2>⚠️ Common Failure Modes</h2>
            <div class="failure-bars">
                {"".join(f'''<div class="failure-bar">
                    <div class="failure-bar-label">{failure_mode_labels.get(fm, fm.replace('_', ' ').title())}</div>
                    <div class="failure-bar-track">
                        <div class="failure-bar-fill" style="width: {min(100, count * 100 / max(failure_mode_counts.values()) if failure_mode_counts else 1)}%">
                            <span class="failure-bar-count">{count}</span>
                        </div>
                    </div>
                </div>''' for fm, count in sorted(failure_mode_counts.items(), key=lambda x: x[1], reverse=True)[:8]) if failure_mode_counts else '<p style="color: var(--text-muted)">No specific failure modes detected in posts.</p>'}
            </div>
        </div>
        
        <!-- Filters -->
        <div class="filters">
            <div class="filter-group" style="flex: 2;">
                <label class="filter-label">Search</label>
                <div class="search-wrapper">
                    <svg class="search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="11" cy="11" r="8"></circle>
                        <path d="m21 21-4.35-4.35"></path>
                    </svg>
                    <input type="text" class="search-input" id="searchInput" placeholder="Search posts...">
                </div>
            </div>
            <div class="filter-group">
                <label class="filter-label">Model</label>
                <select class="filter-select" id="modelFilter">
                    <option value="">All Models</option>
                    {"".join(f'<option value="{escape_html(m)}">{escape_html(m)} ({model_stats[m]["total"]})</option>' for m in sorted_models)}
                </select>
            </div>
            <div class="filter-group">
                <label class="filter-label">Homework</label>
                <select class="filter-select" id="hwFilter">
                    <option value="">All Homeworks</option>
                    {"".join(f'<option value="{escape_html(h)}">{escape_html(h)} ({hw_stats[h]["total"]})</option>' for h in sorted_homeworks)}
                </select>
            </div>
            <div class="filter-group">
                <label class="filter-label">Outcome</label>
                <select class="filter-select" id="outcomeFilter">
                    <option value="">All Outcomes</option>
                    <option value="success">✅ Success</option>
                    <option value="partial">⚠️ Partial</option>
                    <option value="failed">❌ Failed</option>
                    <option value="unknown">❓ Unknown</option>
                </select>
            </div>
        </div>
        
        <!-- Dynamic Summary -->
        <div id="dynamicSummary"></div>
        
        <div class="results-count" id="resultsCount">
            Showing <span>{len(sorted_threads)}</span> posts
        </div>
        
        <div class="posts-grid" id="postsGrid">
        </div>
    </div>
    
    <script>
        const threads = {threads_json};
        const failureModeLabels = {json.dumps(failure_mode_labels)};
        
        function escapeHtml(text) {{
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }}
        
        function formatDate(dateStr) {{
            if (!dateStr) return 'Unknown date';
            try {{
                const date = new Date(dateStr);
                return date.toLocaleDateString('en-US', {{
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                }});
            }} catch (e) {{
                return dateStr;
            }}
        }}
        
        function getOutcomeTag(outcome) {{
            const labels = {{
                'success': '✅ Success',
                'partial': '⚠️ Partial',
                'failed': '❌ Failed',
                'unknown': '❓ Unknown'
            }};
            return `<span class="tag tag-outcome tag-${{outcome}}">${{labels[outcome] || outcome}}</span>`;
        }}
        
        function computeStats(posts) {{
            const stats = {{
                total: posts.length,
                success: posts.filter(p => p.outcome === 'success').length,
                partial: posts.filter(p => p.outcome === 'partial').length,
                failed: posts.filter(p => p.outcome === 'failed').length,
                unknown: posts.filter(p => p.outcome === 'unknown').length,
                models: {{}},
                homeworks: {{}},
                failureModes: {{}}
            }};
            
            posts.forEach(post => {{
                // Count by model
                stats.models[post.model] = stats.models[post.model] || {{total: 0, success: 0, partial: 0, failed: 0}};
                stats.models[post.model].total++;
                stats.models[post.model][post.outcome] = (stats.models[post.model][post.outcome] || 0) + 1;
                
                // Count by homework
                stats.homeworks[post.homework] = stats.homeworks[post.homework] || {{total: 0, success: 0, partial: 0, failed: 0}};
                stats.homeworks[post.homework].total++;
                stats.homeworks[post.homework][post.outcome] = (stats.homeworks[post.homework][post.outcome] || 0) + 1;
                
                // Count failure modes
                post.failure_modes.forEach(fm => {{
                    stats.failureModes[fm] = (stats.failureModes[fm] || 0) + 1;
                }});
            }});
            
            return stats;
        }}
        
        function getTopItems(obj, n = 5, sortBy = 'total') {{
            return Object.entries(obj)
                .sort((a, b) => b[1][sortBy] - a[1][sortBy])
                .slice(0, n);
        }}
        
        function getTopFailures(obj, n = 5) {{
            return Object.entries(obj)
                .sort((a, b) => b[1] - a[1])
                .slice(0, n);
        }}
        
        function renderMiniBar(success, partial, failed, unknown, total) {{
            if (total === 0) return '';
            const successPct = (success / total * 100).toFixed(1);
            const partialPct = (partial / total * 100).toFixed(1);
            const failedPct = (failed / total * 100).toFixed(1);
            const unknownPct = (unknown / total * 100).toFixed(1);
            
            return `
                <div class="mini-bar">
                    <div class="mini-bar-segment mini-bar-success" style="width: ${{successPct}}%" title="Success: ${{successPct}}%"></div>
                    <div class="mini-bar-segment mini-bar-partial" style="width: ${{partialPct}}%" title="Partial: ${{partialPct}}%"></div>
                    <div class="mini-bar-segment mini-bar-failed" style="width: ${{failedPct}}%" title="Failed: ${{failedPct}}%"></div>
                    <div class="mini-bar-segment mini-bar-unknown" style="width: ${{unknownPct}}%" title="Unknown: ${{unknownPct}}%"></div>
                </div>
            `;
        }}
        
        function renderDynamicSummary(model, hw, posts) {{
            const container = document.getElementById('dynamicSummary');
            const stats = computeStats(posts);
            
            // If filtering by model
            if (model && !hw) {{
                const modelData = stats.models[model] || {{total: 0, success: 0, partial: 0, failed: 0}};
                const successRate = modelData.total > 0 ? ((modelData.success / modelData.total) * 100).toFixed(0) : 0;
                const failRate = modelData.total > 0 ? ((modelData.failed / modelData.total) * 100).toFixed(0) : 0;
                
                // Find which HWs this model did well/poorly on
                const hwPerformance = Object.entries(stats.homeworks)
                    .map(([hwName, hwStats]) => {{
                        const hwPosts = posts.filter(p => p.homework === hwName);
                        const hwSuccess = hwPosts.filter(p => p.outcome === 'success').length;
                        const hwFailed = hwPosts.filter(p => p.outcome === 'failed').length;
                        return {{ hw: hwName, total: hwPosts.length, success: hwSuccess, failed: hwFailed, 
                                 successRate: hwPosts.length > 0 ? (hwSuccess / hwPosts.length * 100) : 0 }};
                    }})
                    .filter(h => h.total > 0)
                    .sort((a, b) => b.successRate - a.successRate);
                
                const bestHWs = hwPerformance.filter(h => h.successRate >= 50).slice(0, 3);
                const worstHWs = hwPerformance.filter(h => h.failed > 0).sort((a, b) => b.failed - a.failed).slice(0, 3);
                
                // Top failure modes for this model
                const topFailures = getTopFailures(stats.failureModes, 4);
                
                container.innerHTML = `
                    <div class="dynamic-summary model-summary">
                        <div class="summary-header">
                            <span class="summary-icon">🤖</span>
                            <h2>${{escapeHtml(model)}} Performance Summary</h2>
                        </div>
                        
                        <div class="summary-grid">
                            <div class="summary-metric">
                                <div class="summary-metric-value">${{stats.total}}</div>
                                <div class="summary-metric-label">Total Tests</div>
                            </div>
                            <div class="summary-metric">
                                <div class="summary-metric-value success-rate">${{successRate}}%</div>
                                <div class="summary-metric-label">Success Rate</div>
                            </div>
                            <div class="summary-metric">
                                <div class="summary-metric-value partial-rate">${{stats.partial}}</div>
                                <div class="summary-metric-label">Partial Success</div>
                            </div>
                            <div class="summary-metric">
                                <div class="summary-metric-value fail-rate">${{stats.failed}}</div>
                                <div class="summary-metric-label">Failed</div>
                            </div>
                        </div>
                        
                        ${{renderMiniBar(stats.success, stats.partial, stats.failed, stats.unknown, stats.total)}}
                        
                        <div class="summary-details">
                            ${{bestHWs.length > 0 ? `
                            <div class="summary-detail-card">
                                <h4>✅ Strong Performance On</h4>
                                <ul class="summary-list">
                                    ${{bestHWs.map(h => `
                                        <li>
                                            <span class="summary-list-name">${{h.hw}}</span>
                                            <span class="summary-list-value" style="color: var(--success)">${{h.successRate.toFixed(0)}}% success</span>
                                        </li>
                                    `).join('')}}
                                </ul>
                            </div>
                            ` : ''}}
                            
                            ${{topFailures.length > 0 ? `
                            <div class="summary-detail-card">
                                <h4>⚠️ Common Failure Modes</h4>
                                <ul class="summary-list">
                                    ${{topFailures.map(([fm, count]) => `
                                        <li>
                                            <span class="summary-list-name">${{failureModeLabels[fm] || fm}}</span>
                                            <span class="summary-list-value" style="color: var(--accent-tertiary)">${{count}} posts</span>
                                        </li>
                                    `).join('')}}
                                </ul>
                            </div>
                            ` : ''}}
                            
                            ${{worstHWs.length > 0 ? `
                            <div class="summary-detail-card">
                                <h4>❌ Struggled With</h4>
                                <ul class="summary-list">
                                    ${{worstHWs.map(h => `
                                        <li>
                                            <span class="summary-list-name">${{h.hw}}</span>
                                            <span class="summary-list-value" style="color: var(--failed)">${{h.failed}} failed</span>
                                        </li>
                                    `).join('')}}
                                </ul>
                            </div>
                            ` : ''}}
                        </div>
                        
                        <div class="summary-insight">
                            <h4>💡 Key Insight</h4>
                            <p>${{generateModelInsight(model, stats, successRate, topFailures)}}</p>
                        </div>
                    </div>
                `;
            }}
            // If filtering by homework
            else if (hw && !model) {{
                const hwData = stats.homeworks[hw] || {{total: 0, success: 0, partial: 0, failed: 0}};
                
                // Find which models did well/poorly on this HW
                const modelPerformance = Object.entries(stats.models)
                    .map(([modelName, modelStats]) => {{
                        const modelPosts = posts.filter(p => p.model === modelName);
                        const modelSuccess = modelPosts.filter(p => p.outcome === 'success').length;
                        const modelFailed = modelPosts.filter(p => p.outcome === 'failed').length;
                        return {{ model: modelName, total: modelPosts.length, success: modelSuccess, failed: modelFailed,
                                 successRate: modelPosts.length > 0 ? (modelSuccess / modelPosts.length * 100) : 0 }};
                    }})
                    .filter(m => m.total > 0)
                    .sort((a, b) => b.successRate - a.successRate);
                
                const bestModels = modelPerformance.filter(m => m.successRate >= 50).slice(0, 4);
                const worstModels = modelPerformance.filter(m => m.failed > 0).sort((a, b) => b.failed - a.failed).slice(0, 4);
                
                // Top failure modes for this HW
                const topFailures = getTopFailures(stats.failureModes, 4);
                
                container.innerHTML = `
                    <div class="dynamic-summary hw-summary">
                        <div class="summary-header">
                            <span class="summary-icon">📚</span>
                            <h2>${{escapeHtml(hw)}} Analysis</h2>
                        </div>
                        
                        <div class="summary-grid">
                            <div class="summary-metric">
                                <div class="summary-metric-value">${{stats.total}}</div>
                                <div class="summary-metric-label">Total Attempts</div>
                            </div>
                            <div class="summary-metric">
                                <div class="summary-metric-value success-rate">${{stats.success}}</div>
                                <div class="summary-metric-label">Successes</div>
                            </div>
                            <div class="summary-metric">
                                <div class="summary-metric-value partial-rate">${{stats.partial}}</div>
                                <div class="summary-metric-label">Partial</div>
                            </div>
                            <div class="summary-metric">
                                <div class="summary-metric-value fail-rate">${{stats.failed}}</div>
                                <div class="summary-metric-label">Failed</div>
                            </div>
                        </div>
                        
                        ${{renderMiniBar(stats.success, stats.partial, stats.failed, stats.unknown, stats.total)}}
                        
                        <div class="summary-details">
                            ${{bestModels.length > 0 ? `
                            <div class="summary-detail-card">
                                <h4>🏆 Top Performing Models</h4>
                                <ul class="summary-list">
                                    ${{bestModels.map(m => `
                                        <li>
                                            <span class="summary-list-name">${{m.model}}</span>
                                            <span class="summary-list-value" style="color: var(--success)">${{m.success}}/${{m.total}} success</span>
                                        </li>
                                    `).join('')}}
                                </ul>
                            </div>
                            ` : ''}}
                            
                            ${{topFailures.length > 0 ? `
                            <div class="summary-detail-card">
                                <h4>⚠️ What Models Struggled With</h4>
                                <ul class="summary-list">
                                    ${{topFailures.map(([fm, count]) => `
                                        <li>
                                            <span class="summary-list-name">${{failureModeLabels[fm] || fm}}</span>
                                            <span class="summary-list-value" style="color: var(--accent-tertiary)">${{count}} occurrences</span>
                                        </li>
                                    `).join('')}}
                                </ul>
                            </div>
                            ` : ''}}
                            
                            ${{worstModels.length > 0 ? `
                            <div class="summary-detail-card">
                                <h4>❌ Models That Struggled</h4>
                                <ul class="summary-list">
                                    ${{worstModels.map(m => `
                                        <li>
                                            <span class="summary-list-name">${{m.model}}</span>
                                            <span class="summary-list-value" style="color: var(--failed)">${{m.failed}} failed</span>
                                        </li>
                                    `).join('')}}
                                </ul>
                            </div>
                            ` : ''}}
                        </div>
                        
                        <div class="summary-insight">
                            <h4>💡 Homework Insight</h4>
                            <p>${{generateHWInsight(hw, stats, topFailures, bestModels, worstModels)}}</p>
                        </div>
                    </div>
                `;
            }}
            // Overall summary (no specific filters)
            else if (!model && !hw) {{
                const topModels = getTopItems(stats.models, 5, 'success');
                const hardestHWs = Object.entries(stats.homeworks)
                    .map(([hwName, hwStats]) => ({{ hw: hwName, ...hwStats, failRate: hwStats.total > 0 ? hwStats.failed / hwStats.total : 0 }}))
                    .sort((a, b) => b.failRate - a.failRate)
                    .slice(0, 4);
                const topFailures = getTopFailures(stats.failureModes, 5);
                const overallSuccessRate = stats.total > 0 ? ((stats.success / stats.total) * 100).toFixed(0) : 0;
                
                container.innerHTML = `
                    <div class="dynamic-summary overall-summary">
                        <div class="summary-header">
                            <span class="summary-icon">📊</span>
                            <h2>Overall Analysis Summary</h2>
                        </div>
                        
                        <div class="summary-grid">
                            <div class="summary-metric">
                                <div class="summary-metric-value">${{stats.total}}</div>
                                <div class="summary-metric-label">Total Posts</div>
                            </div>
                            <div class="summary-metric">
                                <div class="summary-metric-value success-rate">${{overallSuccessRate}}%</div>
                                <div class="summary-metric-label">Success Rate</div>
                            </div>
                            <div class="summary-metric">
                                <div class="summary-metric-value">${{Object.keys(stats.models).length}}</div>
                                <div class="summary-metric-label">Models Tested</div>
                            </div>
                            <div class="summary-metric">
                                <div class="summary-metric-value">${{Object.keys(stats.homeworks).filter(h => h !== 'Unknown').length}}</div>
                                <div class="summary-metric-label">HWs Covered</div>
                            </div>
                        </div>
                        
                        ${{renderMiniBar(stats.success, stats.partial, stats.failed, stats.unknown, stats.total)}}
                        
                        <div class="summary-details">
                            ${{topModels.length > 0 ? `
                            <div class="summary-detail-card">
                                <h4>🏆 Most Successful Models</h4>
                                <ul class="summary-list">
                                    ${{topModels.map(([modelName, modelStats]) => `
                                        <li>
                                            <span class="summary-list-name">${{modelName}}</span>
                                            <span class="summary-list-value">${{modelStats.success}}/${{modelStats.total}} wins</span>
                                        </li>
                                    `).join('')}}
                                </ul>
                            </div>
                            ` : ''}}
                            
                            ${{topFailures.length > 0 ? `
                            <div class="summary-detail-card">
                                <h4>⚠️ Top Failure Modes Across All Models</h4>
                                <ul class="summary-list">
                                    ${{topFailures.map(([fm, count]) => `
                                        <li>
                                            <span class="summary-list-name">${{failureModeLabels[fm] || fm}}</span>
                                            <span class="summary-list-value" style="color: var(--accent-tertiary)">${{count}}</span>
                                        </li>
                                    `).join('')}}
                                </ul>
                            </div>
                            ` : ''}}
                            
                            ${{hardestHWs.length > 0 ? `
                            <div class="summary-detail-card">
                                <h4>📈 Most Challenging Homeworks</h4>
                                <ul class="summary-list">
                                    ${{hardestHWs.filter(h => h.hw !== 'Unknown').map(h => `
                                        <li>
                                            <span class="summary-list-name">${{h.hw}}</span>
                                            <span class="summary-list-value" style="color: var(--failed)">${{(h.failRate * 100).toFixed(0)}}% fail rate</span>
                                        </li>
                                    `).join('')}}
                                </ul>
                            </div>
                            ` : ''}}
                        </div>
                        
                        <div class="summary-insight">
                            <h4>💡 Overall Insight</h4>
                            <p>${{generateOverallInsight(stats, topModels, topFailures, hardestHWs)}}</p>
                        </div>
                    </div>
                `;
            }}
            // Both model and hw filtered - show combined view
            else {{
                container.innerHTML = `
                    <div class="dynamic-summary">
                        <div class="summary-header">
                            <span class="summary-icon">🔍</span>
                            <h2>${{escapeHtml(model)}} on ${{escapeHtml(hw)}}</h2>
                        </div>
                        
                        <div class="summary-grid">
                            <div class="summary-metric">
                                <div class="summary-metric-value">${{stats.total}}</div>
                                <div class="summary-metric-label">Posts</div>
                            </div>
                            <div class="summary-metric">
                                <div class="summary-metric-value success-rate">${{stats.success}}</div>
                                <div class="summary-metric-label">Success</div>
                            </div>
                            <div class="summary-metric">
                                <div class="summary-metric-value partial-rate">${{stats.partial}}</div>
                                <div class="summary-metric-label">Partial</div>
                            </div>
                            <div class="summary-metric">
                                <div class="summary-metric-value fail-rate">${{stats.failed}}</div>
                                <div class="summary-metric-label">Failed</div>
                            </div>
                        </div>
                        
                        ${{renderMiniBar(stats.success, stats.partial, stats.failed, stats.unknown, stats.total)}}
                    </div>
                `;
            }}
        }}
        
        function generateModelInsight(model, stats, successRate, topFailures) {{
            const failureText = topFailures.length > 0 
                ? `The most common issue was ${{failureModeLabels[topFailures[0][0]] || topFailures[0][0]}} (${{topFailures[0][1]}} occurrences).`
                : '';
            
            if (parseInt(successRate) >= 70) {{
                return `${{model}} demonstrated strong performance with a ${{successRate}}% success rate across ${{stats.total}} tests. ${{failureText}}`;
            }} else if (parseInt(successRate) >= 40) {{
                return `${{model}} showed mixed results with a ${{successRate}}% success rate. ${{failureText}} Consider providing more context or breaking tasks into smaller steps.`;
            }} else {{
                return `${{model}} struggled with these tasks, achieving only a ${{successRate}}% success rate. ${{failureText}} This model may need significant guidance for similar problems.`;
            }}
        }}
        
        function generateHWInsight(hw, stats, topFailures, bestModels, worstModels) {{
            const successRate = stats.total > 0 ? ((stats.success / stats.total) * 100).toFixed(0) : 0;
            const failureText = topFailures.length > 0 
                ? `Common struggles included ${{topFailures.map(([fm]) => failureModeLabels[fm] || fm).slice(0, 2).join(' and ')}}.`
                : '';
            const bestModelText = bestModels.length > 0 
                ? `Top performers: ${{bestModels.slice(0, 2).map(m => m.model).join(', ')}}.`
                : '';
            
            return `${{hw}} had a ${{successRate}}% overall success rate across ${{stats.total}} attempts. ${{bestModelText}} ${{failureText}}`;
        }}
        
        function generateOverallInsight(stats, topModels, topFailures, hardestHWs) {{
            const successRate = stats.total > 0 ? ((stats.success / stats.total) * 100).toFixed(0) : 0;
            const topModel = topModels.length > 0 ? topModels[0][0] : 'Unknown';
            const topFailure = topFailures.length > 0 ? failureModeLabels[topFailures[0][0]] || topFailures[0][0] : 'none detected';
            const hardestHW = hardestHWs.filter(h => h.hw !== 'Unknown')[0];
            
            return `Across all ${{stats.total}} participation posts, models achieved a ${{successRate}}% success rate. ${{topModel}} led in successful completions. The most common failure mode was "${{topFailure}}". ${{hardestHW ? `${{hardestHW.hw}} proved most challenging with a ${{(hardestHW.failRate * 100).toFixed(0)}}% failure rate.` : ''}}`;
        }}
        
        function groupByHomework(posts) {{
            const groups = {{}};
            posts.forEach(post => {{
                const hw = post.homework || 'Unknown';
                if (!groups[hw]) groups[hw] = [];
                groups[hw].push(post);
            }});
            return groups;
        }}
        
        function sortHomeworks(homeworks) {{
            return homeworks.sort((a, b) => {{
                if (a === 'Unknown') return 1;
                if (b === 'Unknown') return -1;
                const numA = parseInt(a.match(/\\d+/)?.[0] || '999');
                const numB = parseInt(b.match(/\\d+/)?.[0] || '999');
                return numA - numB;
            }});
        }}
        
        function renderPosts(posts) {{
            const grid = document.getElementById('postsGrid');
            const count = document.getElementById('resultsCount');
            
            count.innerHTML = `Showing <span>${{posts.length}}</span> posts`;
            
            if (posts.length === 0) {{
                grid.innerHTML = `
                    <div class="no-posts">
                        <h2>No posts found</h2>
                        <p>Try adjusting your filters or search query.</p>
                    </div>
                `;
                return;
            }}
            
            // Group posts by homework
            const grouped = groupByHomework(posts);
            const sortedHWs = sortHomeworks(Object.keys(grouped));
            
            grid.innerHTML = sortedHWs.map(hw => {{
                const hwPosts = grouped[hw];
                const hwStats = computeStats(hwPosts);
                const successRate = hwStats.total > 0 ? ((hwStats.success / hwStats.total) * 100).toFixed(0) : 0;
                
                return `
                    <div class="homework-section" id="hw-section-${{hw.replace(/\\s+/g, '-')}}">
                        <div class="homework-header" onclick="toggleHomeworkSection('${{hw.replace(/\\s+/g, '-')}}')">
                            <div class="homework-title">
                                <span>📚 ${{escapeHtml(hw)}}</span>
                                <span class="homework-badge">${{hwPosts.length}} post${{hwPosts.length !== 1 ? 's' : ''}}</span>
                                <span style="font-size: 0.85rem; color: var(--text-muted); font-weight: 400;">
                                    ✅ ${{hwStats.success}} | ⚠️ ${{hwStats.partial}} | ❌ ${{hwStats.failed}}
                                </span>
                            </div>
                            <div class="homework-arrow">▼</div>
                        </div>
                        <div class="homework-posts">
                            ${{hwPosts.map((post, idx) => {{
                                const globalIdx = posts.indexOf(post);
                                return `
                                    <div class="post" style="--index: ${{idx}}">
                                        <div class="post-header">
                                            <h3 class="post-title">${{escapeHtml(post.title)}}</h3>
                                            <div class="post-tags">
                                                <span class="tag tag-model">${{escapeHtml(post.model)}}</span>
                                                ${{getOutcomeTag(post.outcome)}}
                                            </div>
                                        </div>
                                        <div class="post-meta">
                                            <span class="post-meta-item">👤 ${{escapeHtml(post.author)}}</span>
                                            <span class="post-meta-item">📅 ${{formatDate(post.created_at)}}</span>
                                        </div>
                                        <div class="post-content" id="content-${{globalIdx}}">
                                            ${{escapeHtml(post.content).replace(/\\n/g, '<br>')}}
                                        </div>
                                        <button class="expand-btn" onclick="toggleExpand(${{globalIdx}})">Show more</button>
                                        ${{post.failure_modes.length > 0 ? `
                                            <div class="failure-tags">
                                                ${{post.failure_modes.map(fm => `<span class="failure-tag">${{failureModeLabels[fm] || fm}}</span>`).join('')}}
                                            </div>
                                        ` : ''}}
                                        <div class="post-footer">
                                            <span>💬 ${{post.comment_count}} comments</span>
                                            <span>👍 ${{post.vote_count}} votes</span>
                                        </div>
                                    </div>
                                `;
                            }}).join('')}}
                        </div>
                    </div>
                `;
            }}).join('');
        }}
        
        function toggleHomeworkSection(hwId) {{
            const section = document.getElementById(`hw-section-${{hwId}}`);
            section.classList.toggle('expanded');
        }}
        
        function toggleExpand(index) {{
            const content = document.getElementById(`content-${{index}}`);
            const btn = content.nextElementSibling;
            content.classList.toggle('expanded');
            btn.textContent = content.classList.contains('expanded') ? 'Show less' : 'Show more';
        }}
        
        function filterPosts() {{
            const search = document.getElementById('searchInput').value.toLowerCase();
            const model = document.getElementById('modelFilter').value;
            const hw = document.getElementById('hwFilter').value;
            const outcome = document.getElementById('outcomeFilter').value;
            
            const filtered = threads.filter(post => {{
                const matchesSearch = !search || 
                    post.title.toLowerCase().includes(search) || 
                    post.content.toLowerCase().includes(search);
                const matchesModel = !model || post.model === model;
                const matchesHw = !hw || post.homework === hw;
                const matchesOutcome = !outcome || post.outcome === outcome;
                
                return matchesSearch && matchesModel && matchesHw && matchesOutcome;
            }});
            
            renderDynamicSummary(model, hw, filtered);
            renderPosts(filtered);
        }}
        
        // Event listeners
        document.getElementById('searchInput').addEventListener('input', filterPosts);
        document.getElementById('modelFilter').addEventListener('change', filterPosts);
        document.getElementById('hwFilter').addEventListener('change', filterPosts);
        document.getElementById('outcomeFilter').addEventListener('change', filterPosts);
        
        // Initial render
        renderDynamicSummary('', '', threads);
        renderPosts(threads);
    </script>
</body>
</html>
"""
    
    # Write the HTML file
    output_path = os.path.join(output_dir, 'index.html')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Static website generated successfully at {output_path}")
    print(f"\n📊 Stats:")
    print(f"   - Total posts: {len(processed_threads)}")
    print(f"   - Models detected: {len(sorted_models)}")
    print(f"   - Homeworks covered: {len(sorted_homeworks)}")
    print(f"   - Failure modes tracked: {len(failure_mode_counts)}")
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
    
    # Save raw data to JSON for analysis
    print("💾 Saving raw post data to JSON...")
    import json
    
    # Process and save (including attachment info)
    posts_data = []
    for thread in detailed_threads:
        title = thread.get('title', 'Untitled')
        raw_content = thread.get('document') or thread.get('content') or ''
        content = parse_thread_content(raw_content)
        
        # Extract attachment/file information
        attachments = []
        
        # Check for document files in the thread
        if 'files' in thread:
            for f in thread.get('files', []):
                attachments.append({
                    'id': f.get('id'),
                    'name': f.get('name', ''),
                    'url': f.get('url', ''),
                    'type': f.get('type', ''),
                    'size': f.get('size', 0)
                })
        
        # Also check in comments for attached files
        for comment in thread.get('comments', []):
            if 'files' in comment:
                for f in comment.get('files', []):
                    attachments.append({
                        'id': f.get('id'),
                        'name': f.get('name', ''),
                        'url': f.get('url', ''),
                        'type': f.get('type', ''),
                        'size': f.get('size', 0),
                        'from_comment': True
                    })
        
        posts_data.append({
            'id': thread.get('id'),
            'title': title,
            'content': content,
            'raw_content': raw_content,  # Keep raw for debugging
            'author': thread.get('user', {}).get('name', 'Unknown') if isinstance(thread.get('user'), dict) else 'Unknown',
            'created_at': thread.get('created_at', ''),
            'comment_count': thread.get('comment_count', 0) or thread.get('num_comments', 0),
            'vote_count': thread.get('vote_count', 0) or thread.get('upvotes', 0) or thread.get('votes', 0),
            'attachments': attachments,
            'raw_keys': list(thread.keys()),  # Debug: see all available keys
        })
    
    with open(os.path.join(OUTPUT_DIR, 'posts_raw.json'), 'w', encoding='utf-8') as f:
        json.dump(posts_data, f, indent=2, ensure_ascii=False)
    
    # Also save full raw thread data for debugging
    with open(os.path.join(OUTPUT_DIR, 'threads_full_raw.json'), 'w', encoding='utf-8') as f:
        json.dump(detailed_threads, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"✅ Saved {len(posts_data)} posts to {OUTPUT_DIR}/posts_raw.json")
    print(f"   Also saved full raw data to {OUTPUT_DIR}/threads_full_raw.json")
    
    # Generate static website
    print("🌐 Generating static website...")
    generate_static_website(detailed_threads, OUTPUT_DIR)
    
    print(f"\n🎉 Done! Your static website is ready in the '{OUTPUT_DIR}' directory")
    print(f"   Open {OUTPUT_DIR}/index.html in your browser to view it")
    print(f"   You can deploy the '{OUTPUT_DIR}' directory to any static hosting service")


if __name__ == '__main__':
    main()
