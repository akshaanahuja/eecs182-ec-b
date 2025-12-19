#!/usr/bin/env python3
"""
Build the static website from analyzed post data.
"""

import json
import os
from datetime import datetime

# Load analyzed data
with open('output/posts_analyzed.json', 'r') as f:
    data = json.load(f)

posts = data['posts']
model_stats = data['model_stats']
hw_stats = data['hw_stats']
failure_mode_stats = data['failure_mode_stats']
failure_mode_defs = data['failure_mode_definitions']
summary = data['summary']

# Sort models and homeworks
sorted_models = sorted(
    [m for m in model_stats.keys() if m != 'Unknown'],
    key=lambda m: model_stats[m]['total'],
    reverse=True
) + (['Unknown'] if 'Unknown' in model_stats else [])

def hw_sort_key(hw):
    if hw == 'Unknown':
        return (1, 999)
    import re
    match = re.search(r'(\d+)', hw)
    return (0, int(match.group(1)) if match else 999)

sorted_homeworks = sorted(hw_stats.keys(), key=hw_sort_key)

# Helper functions
def escape_html(text):
    if not text:
        return ""
    return (str(text)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#x27;'))

# Sort threads by date (newest first)
sorted_posts = sorted(posts, key=lambda x: x.get('created_at', ''), reverse=True)

# Generate JavaScript data
posts_json = json.dumps(sorted_posts, default=str)
failure_defs_json = json.dumps(failure_mode_defs)

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
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Outfit', sans-serif;
            line-height: 1.6;
            color: var(--text-primary);
            background: var(--bg-dark);
            min-height: 100vh;
        }}
        
        .bg-pattern {{
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            pointer-events: none; z-index: 0;
            background: 
                radial-gradient(ellipse 80% 50% at 50% -20%, rgba(124, 58, 237, 0.15), transparent),
                radial-gradient(ellipse 60% 40% at 100% 50%, rgba(0, 212, 170, 0.08), transparent),
                radial-gradient(ellipse 50% 30% at 0% 80%, rgba(244, 63, 94, 0.08), transparent);
        }}
        
        .container {{ max-width: 1400px; margin: 0 auto; padding: 40px 24px; position: relative; z-index: 1; }}
        
        header {{ text-align: center; margin-bottom: 48px; animation: fadeInDown 0.6s ease-out; }}
        
        @keyframes fadeInDown {{ from {{ opacity: 0; transform: translateY(-20px); }} to {{ opacity: 1; transform: translateY(0); }} }}
        @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
        
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
        
        .subtitle {{ color: var(--text-secondary); font-size: 1.1rem; font-weight: 300; }}
        
        .meta-info {{ display: flex; justify-content: center; gap: 24px; margin-top: 16px; flex-wrap: wrap; }}
        
        .meta-badge {{
            display: inline-flex; align-items: center; gap: 8px;
            padding: 8px 16px;
            background: var(--glass-bg);
            border: 1px solid var(--glass-border);
            border-radius: 100px;
            font-size: 0.875rem;
            color: var(--text-secondary);
            backdrop-filter: blur(10px);
        }}
        
        .meta-badge span {{ color: var(--accent-primary); font-weight: 600; font-family: 'JetBrains Mono', monospace; }}
        
        /* Dashboard */
        .dashboard {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-bottom: 40px; animation: fadeIn 0.6s ease-out 0.2s both; }}
        
        .stat-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 24px;
            transition: all 0.3s ease;
        }}
        
        .stat-card:hover {{ border-color: var(--accent-primary); transform: translateY(-2px); box-shadow: 0 8px 32px rgba(0, 212, 170, 0.1); }}
        
        .stat-card h3 {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-muted); margin-bottom: 16px; }}
        
        .stat-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }}
        
        .stat-item {{ text-align: center; padding: 12px; background: rgba(0, 0, 0, 0.2); border-radius: 8px; }}
        
        .stat-value {{ font-size: 1.5rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; color: var(--accent-primary); }}
        
        .stat-label {{ font-size: 0.75rem; color: var(--text-muted); margin-top: 4px; }}
        
        /* Dynamic Summary */
        .dynamic-summary {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 24px;
            animation: fadeIn 0.4s ease-out;
        }}
        
        .dynamic-summary.model-summary {{ border-left: 4px solid var(--accent-secondary); }}
        .dynamic-summary.hw-summary {{ border-left: 4px solid var(--accent-primary); }}
        .dynamic-summary.overall-summary {{ border-left: 4px solid var(--accent-tertiary); }}
        
        .summary-header {{ display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }}
        .summary-header h2 {{ font-size: 1.25rem; color: var(--text-primary); margin: 0; }}
        .summary-header .summary-icon {{ font-size: 1.5rem; }}
        
        .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 20px; }}
        
        .summary-metric {{ background: rgba(0, 0, 0, 0.2); border-radius: 10px; padding: 16px; text-align: center; }}
        .summary-metric-value {{ font-size: 2rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; margin-bottom: 4px; }}
        .summary-metric-label {{ font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }}
        
        .success-rate {{ color: var(--success); }}
        .partial-rate {{ color: var(--partial); }}
        .fail-rate {{ color: var(--failed); }}
        
        .summary-details {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; }}
        
        .summary-detail-card {{ background: rgba(0, 0, 0, 0.15); border-radius: 10px; padding: 16px; }}
        .summary-detail-card h4 {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-muted); margin-bottom: 12px; }}
        
        .summary-list {{ list-style: none; padding: 0; margin: 0; }}
        .summary-list li {{ display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--border-color); font-size: 0.9rem; }}
        .summary-list li:last-child {{ border-bottom: none; }}
        .summary-list-name {{ color: var(--text-secondary); }}
        .summary-list-value {{ font-family: 'JetBrains Mono', monospace; font-weight: 600; color: var(--accent-primary); }}
        
        .summary-insight {{ background: rgba(124, 58, 237, 0.1); border: 1px solid rgba(124, 58, 237, 0.2); border-radius: 8px; padding: 16px; margin-top: 16px; }}
        .summary-insight h4 {{ font-size: 0.85rem; color: #a78bfa; margin-bottom: 8px; display: flex; align-items: center; gap: 8px; }}
        .summary-insight p {{ font-size: 0.9rem; color: var(--text-secondary); line-height: 1.6; margin: 0; }}
        
        .mini-bar {{ display: flex; height: 8px; border-radius: 4px; overflow: hidden; background: rgba(0, 0, 0, 0.3); margin-top: 12px; }}
        .mini-bar-segment {{ height: 100%; transition: width 0.5s ease; }}
        .mini-bar-success {{ background: var(--success); }}
        .mini-bar-partial {{ background: var(--partial); }}
        .mini-bar-failed {{ background: var(--failed); }}
        .mini-bar-unknown {{ background: var(--text-muted); }}
        
        /* Filters */
        .filters {{ display: flex; gap: 16px; margin-bottom: 32px; flex-wrap: wrap; animation: fadeIn 0.6s ease-out 0.4s both; }}
        
        .filter-group {{ flex: 1; min-width: 200px; }}
        
        .filter-label {{ display: block; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-muted); margin-bottom: 8px; }}
        
        .filter-select {{
            width: 100%; padding: 12px 16px;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            color: var(--text-primary);
            font-family: 'Outfit', sans-serif;
            font-size: 0.95rem;
            cursor: pointer;
            transition: all 0.2s ease;
            appearance: none;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E");
            background-repeat: no-repeat;
            background-position: right 12px center;
            background-size: 16px;
            padding-right: 40px;
        }}
        
        .filter-select:hover {{ border-color: var(--accent-primary); }}
        .filter-select:focus {{ outline: none; border-color: var(--accent-primary); box-shadow: 0 0 0 3px rgba(0, 212, 170, 0.1); }}
        .filter-select option {{ background: var(--bg-card); color: var(--text-primary); }}
        
        .search-input {{
            width: 100%; padding: 12px 16px 12px 44px;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            color: var(--text-primary);
            font-family: 'Outfit', sans-serif;
            font-size: 0.95rem;
            transition: all 0.2s ease;
        }}
        
        .search-wrapper {{ position: relative; }}
        .search-icon {{ position: absolute; left: 14px; top: 50%; transform: translateY(-50%); color: var(--text-muted); }}
        .search-input:hover {{ border-color: var(--accent-primary); }}
        .search-input:focus {{ outline: none; border-color: var(--accent-primary); box-shadow: 0 0 0 3px rgba(0, 212, 170, 0.1); }}
        
        .results-count {{ font-size: 0.875rem; color: var(--text-muted); margin-bottom: 20px; }}
        .results-count span {{ color: var(--accent-primary); font-weight: 600; }}
        
        /* Posts */
        .posts-grid {{ display: grid; gap: 20px; }}
        
        .post {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 28px;
            transition: all 0.3s ease;
            animation: fadeIn 0.4s ease-out both;
        }}
        
        .post:hover {{ border-color: var(--accent-secondary); background: var(--bg-card-hover); transform: translateY(-2px); box-shadow: 0 12px 40px rgba(124, 58, 237, 0.08); }}
        
        .post-header {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 16px; flex-wrap: wrap; }}
        .post-title {{ font-size: 1.25rem; font-weight: 600; color: var(--text-primary); line-height: 1.4; flex: 1; }}
        .post-tags {{ display: flex; gap: 8px; flex-wrap: wrap; }}
        
        .tag {{ padding: 4px 12px; border-radius: 100px; font-size: 0.75rem; font-weight: 500; font-family: 'JetBrains Mono', monospace; }}
        .tag-model {{ background: rgba(124, 58, 237, 0.15); color: #a78bfa; border: 1px solid rgba(124, 58, 237, 0.3); }}
        .tag-hw {{ background: rgba(0, 212, 170, 0.15); color: var(--accent-primary); border: 1px solid rgba(0, 212, 170, 0.3); }}
        .tag-outcome {{ font-size: 0.7rem; }}
        .tag-success {{ background: rgba(16, 185, 129, 0.15); color: var(--success); border: 1px solid rgba(16, 185, 129, 0.3); }}
        .tag-partial {{ background: rgba(245, 158, 11, 0.15); color: var(--partial); border: 1px solid rgba(245, 158, 11, 0.3); }}
        .tag-failed {{ background: rgba(239, 68, 68, 0.15); color: var(--failed); border: 1px solid rgba(239, 68, 68, 0.3); }}
        .tag-unknown {{ background: rgba(100, 116, 139, 0.15); color: var(--text-muted); border: 1px solid rgba(100, 116, 139, 0.3); }}
        
        .post-meta {{ display: flex; gap: 16px; flex-wrap: wrap; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 16px; padding-bottom: 16px; border-bottom: 1px solid var(--border-color); }}
        .post-meta-item {{ display: flex; align-items: center; gap: 6px; }}
        
        .post-content {{ color: var(--text-secondary); font-size: 0.95rem; line-height: 1.8; max-height: 200px; overflow: hidden; position: relative; }}
        .post-content.expanded {{ max-height: none; }}
        .post-content::after {{ content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 60px; background: linear-gradient(transparent, var(--bg-card)); pointer-events: none; }}
        .post-content.expanded::after {{ display: none; }}
        
        .expand-btn {{ margin-top: 12px; padding: 8px 16px; background: transparent; border: 1px solid var(--border-color); border-radius: 8px; color: var(--text-secondary); font-family: 'Outfit', sans-serif; font-size: 0.85rem; cursor: pointer; transition: all 0.2s ease; }}
        .expand-btn:hover {{ border-color: var(--accent-primary); color: var(--accent-primary); }}
        
        .failure-tags {{ display: flex; gap: 6px; flex-wrap: wrap; margin-top: 12px; }}
        .failure-tag {{ padding: 3px 10px; background: rgba(244, 63, 94, 0.1); border: 1px solid rgba(244, 63, 94, 0.2); border-radius: 4px; font-size: 0.7rem; color: var(--accent-tertiary); font-family: 'JetBrains Mono', monospace; }}
        
        .post-footer {{ display: flex; gap: 16px; margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--border-color); font-size: 0.85rem; color: var(--text-muted); }}
        
        .no-posts {{ text-align: center; padding: 80px 20px; color: var(--text-muted); }}
        .no-posts h2 {{ font-size: 1.5rem; margin-bottom: 8px; color: var(--text-secondary); }}
        
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
        
        /* Failure Deep Dive Section */
        .failure-deep-dive {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 28px;
            margin-bottom: 32px;
            animation: fadeIn 0.6s ease-out 0.3s both;
        }}
        
        .failure-deep-dive h2 {{
            font-size: 1.5rem;
            margin-bottom: 8px;
            color: var(--text-primary);
        }}
        
        .section-intro {{
            color: var(--text-secondary);
            margin-bottom: 24px;
            font-size: 0.95rem;
        }}
        
        .failure-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 16px;
        }}
        
        .failure-card {{
            background: rgba(0, 0, 0, 0.2);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
            cursor: pointer;
            transition: all 0.3s ease;
        }}
        
        .failure-card:hover {{
            border-color: var(--accent-tertiary);
            background: rgba(244, 63, 94, 0.05);
        }}
        
        .failure-card.expanded {{
            grid-column: 1 / -1;
            border-color: var(--accent-tertiary);
        }}
        
        .failure-card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }}
        
        .failure-card-title {{
            font-size: 1rem;
            font-weight: 600;
            color: var(--accent-tertiary);
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .failure-card-count {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            color: var(--text-muted);
            background: rgba(0, 0, 0, 0.3);
            padding: 4px 10px;
            border-radius: 100px;
        }}
        
        .failure-card-short {{
            color: var(--text-secondary);
            font-size: 0.875rem;
            line-height: 1.5;
        }}
        
        .failure-card-detailed {{
            display: none;
            margin-top: 16px;
            padding-top: 16px;
            border-top: 1px solid var(--border-color);
            color: var(--text-secondary);
            font-size: 0.9rem;
            line-height: 1.8;
        }}
        
        .failure-card.expanded .failure-card-detailed {{
            display: block;
        }}
        
        .failure-card-detailed strong {{
            color: var(--accent-primary);
        }}
        
        .failure-card-models {{
            margin-top: 16px;
            padding-top: 12px;
            border-top: 1px solid var(--border-color);
        }}
        
        .failure-card-models h5 {{
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--text-muted);
            margin-bottom: 8px;
        }}
        
        .model-chips {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }}
        
        .model-chip {{
            padding: 3px 10px;
            background: rgba(124, 58, 237, 0.1);
            border: 1px solid rgba(124, 58, 237, 0.2);
            border-radius: 100px;
            font-size: 0.7rem;
            color: #a78bfa;
            font-family: 'JetBrains Mono', monospace;
        }}
        
        .expand-indicator {{
            color: var(--text-muted);
            font-size: 0.8rem;
            transition: transform 0.2s ease;
        }}
        
        .failure-card.expanded .expand-indicator {{
            transform: rotate(180deg);
        }}
        
        /* Observations Section */
        .observations {{
            background: rgba(0, 0, 0, 0.2);
            border-radius: 8px;
            padding: 16px;
            margin-top: 16px;
        }}
        
        .observations h5 {{
            font-size: 0.85rem;
            color: var(--text-secondary);
            margin-bottom: 12px;
            font-weight: 500;
        }}
        
        .observations ul {{
            list-style: none;
            padding: 0;
            margin: 0;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}
        
        .observations li {{
            font-size: 0.85rem;
            color: var(--text-secondary);
            display: flex;
            gap: 8px;
            align-items: flex-start;
            line-height: 1.5;
        }}
        
        .observations li.obs-strength {{
            color: var(--success);
        }}
        
        .observations li.obs-weakness {{
            color: var(--failed);
        }}
        
        .observations li.obs-annotation {{
            color: var(--info);
        }}
        
        .obs-icon {{
            flex-shrink: 0;
        }}
        
        .pdf-badge {{
            background: linear-gradient(135deg, #f59e0b, #d97706);
            color: white;
            padding: 4px 10px;
            border-radius: 100px;
            font-size: 0.7rem;
            font-weight: 600;
        }}
        
        /* Executive Summary */
        .executive-summary {{
            background: linear-gradient(135deg, rgba(0, 212, 170, 0.1), rgba(124, 58, 237, 0.1));
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 32px;
            margin-bottom: 32px;
        }}
        
        .executive-summary h2 {{
            font-size: 1.5rem;
            margin-bottom: 20px;
            color: var(--text-primary);
        }}
        
        .exec-intro {{
            font-size: 1.1rem;
            line-height: 1.8;
            color: var(--text-secondary);
            margin-bottom: 24px;
        }}
        
        .exec-intro strong {{
            color: var(--accent-primary);
        }}
        
        .exec-highlights {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-bottom: 28px;
        }}
        
        .exec-highlight {{
            background: rgba(0, 0, 0, 0.2);
            border-radius: 12px;
            padding: 20px;
            display: flex;
            gap: 16px;
        }}
        
        .exec-highlight-icon {{
            font-size: 2rem;
            flex-shrink: 0;
        }}
        
        .exec-highlight-stat {{
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--text-primary);
        }}
        
        .exec-highlight-label {{
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-bottom: 8px;
        }}
        
        .exec-highlight-detail {{
            font-size: 0.85rem;
            color: var(--text-secondary);
            line-height: 1.5;
        }}
        
        .success-highlight .exec-highlight-stat {{ color: var(--success); }}
        .failure-highlight .exec-highlight-stat {{ color: var(--accent-tertiary); }}
        .model-highlight .exec-highlight-stat {{ color: var(--accent-secondary); }}
        
        .exec-key-findings {{
            background: rgba(0, 0, 0, 0.15);
            border-radius: 12px;
            padding: 20px;
        }}
        
        .exec-key-findings h3 {{
            font-size: 1.1rem;
            margin-bottom: 16px;
            color: var(--text-primary);
        }}
        
        .exec-key-findings ul {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        
        .exec-key-findings li {{
            padding: 10px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            color: var(--text-secondary);
            line-height: 1.6;
        }}
        
        .exec-key-findings li:last-child {{
            border-bottom: none;
        }}
        
        .exec-key-findings li strong {{
            color: var(--accent-primary);
        }}
        
        /* Enhanced Summary Insights */
        .summary-insight {{
            background: rgba(0, 0, 0, 0.15);
            border-radius: 12px;
            padding: 20px;
            margin-top: 20px;
            border-left: 4px solid var(--accent-primary);
        }}
        
        .summary-insight h4 {{
            font-size: 1rem;
            margin-bottom: 12px;
            color: var(--accent-primary);
        }}
        
        .summary-insight p {{
            color: var(--text-secondary);
            line-height: 1.8;
            margin-bottom: 12px;
            font-size: 0.95rem;
        }}
        
        .summary-insight p:last-child {{
            margin-bottom: 0;
        }}
        
        .summary-insight strong {{
            color: var(--text-primary);
        }}
        
        @media (max-width: 768px) {{
            .container {{ padding: 24px 16px; }}
            .filters {{ flex-direction: column; }}
            .filter-group {{ min-width: 100%; }}
            .post-header {{ flex-direction: column; }}
            .dashboard {{ grid-template-columns: 1fr; }}
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
                <div class="meta-badge">📊 <span>{summary['total_posts']}</span> posts analyzed</div>
                <div class="meta-badge">🤖 <span>{summary['total_models']}</span> models tested</div>
                <div class="meta-badge">📚 <span>{summary['total_homeworks']}</span> homeworks covered</div>
                <div class="meta-badge">✅ <span>{summary['overall_success_rate']}%</span> success rate</div>
                <div class="meta-badge">📄 <span>{summary.get('posts_with_pdf', 0)}</span> with PDF annotations</div>
            </div>
        </header>
        
        <!-- Executive Summary -->
        <div class="executive-summary">
            <h2>📋 Executive Summary</h2>
            <div class="exec-summary-content">
                <p class="exec-intro">
                    This analysis examines <strong>{summary['total_posts']} student reports</strong> on using AI models to complete 
                    EECS 182 homework assignments. Students tested <strong>{summary['total_models']} different AI models</strong> 
                    across <strong>{summary['total_homeworks']} homework assignments</strong>, documenting both successes and failures 
                    with detailed annotations.
                </p>
                
                <div class="exec-highlights">
                    <div class="exec-highlight success-highlight">
                        <div class="exec-highlight-icon">✅</div>
                        <div class="exec-highlight-content">
                            <div class="exec-highlight-stat">{summary['overall_success_rate']}%</div>
                            <div class="exec-highlight-label">Overall Success Rate</div>
                            <p class="exec-highlight-detail">Of {summary['total_posts']} attempts, {summary['outcomes']['success']} were fully successful, 
                            {summary['outcomes']['partial']} had partial success, and {summary['outcomes']['failed']} failed.</p>
                        </div>
                    </div>
                    
                    <div class="exec-highlight failure-highlight">
                        <div class="exec-highlight-icon">⚠️</div>
                        <div class="exec-highlight-content">
                            <div class="exec-highlight-stat">{summary['top_failure_mode'][0] if summary.get('top_failure_mode') else 'N/A'}</div>
                            <div class="exec-highlight-label">Most Common Failure</div>
                            <p class="exec-highlight-detail">{summary['top_failure_mode'][1] if summary.get('top_failure_mode') else 0} occurrences. 
                            Models frequently made errors with tensor dimensions, shape mismatches, and broadcasting issues.</p>
                        </div>
                    </div>
                    
                    <div class="exec-highlight model-highlight">
                        <div class="exec-highlight-icon">🤖</div>
                        <div class="exec-highlight-content">
                            <div class="exec-highlight-stat">{summary['top_model'][0] if summary.get('top_model') else 'N/A'}</div>
                            <div class="exec-highlight-label">Most Tested Model</div>
                            <p class="exec-highlight-detail">Tested {summary['top_model'][1] if summary.get('top_model') else 0} times. 
                            Other popular choices included Claude, DeepSeek, Grok, and ChatGPT variants.</p>
                        </div>
                    </div>
                </div>
                
                <div class="exec-key-findings">
                    <h3>🔑 Key Findings</h3>
                    <ul>
                        <li><strong>Dimension errors dominate:</strong> Shape mismatches and tensor dimension issues were by far the most common failure mode, appearing in nearly half of all failure cases.</li>
                        <li><strong>Hyperparameter tuning is hard:</strong> AI models struggle to find optimal learning rates, weight scales, and training configurations without the ability to run code and observe results.</li>
                        <li><strong>Visual reasoning is unreliable:</strong> When interpreting attention visualizations or graphs, models frequently hallucinated patterns that didn't exist in the actual images.</li>
                        <li><strong>Debugging loops occur:</strong> Models often get stuck proposing the same incorrect fixes repeatedly, unable to step back and reconsider their approach.</li>
                        <li><strong>PDF annotations reveal more:</strong> {summary.get('posts_with_pdf', 0)} posts had detailed PDF annotations that significantly enriched the analysis with specific examples.</li>
                    </ul>
                </div>
            </div>
        </div>
        
        <!-- Failure Modes Deep Dive -->
        <div class="failure-deep-dive" id="failureDeepDive">
            <h2>⚠️ Common Failure Modes Analysis</h2>
            <p class="section-intro">Click on any failure mode to learn more about how models struggled:</p>
            <div class="failure-cards" id="failureCards"></div>
        </div>
        
        <!-- Filters -->
        <div class="filters">
            <div class="filter-group" style="flex: 2;">
                <label class="filter-label">Search</label>
                <div class="search-wrapper">
                    <svg class="search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><path d="m21 21-4.35-4.35"></path></svg>
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
                    <option value="success">✅ Success ({summary['outcomes']['success']})</option>
                    <option value="partial">⚠️ Partial ({summary['outcomes']['partial']})</option>
                    <option value="failed">❌ Failed ({summary['outcomes']['failed']})</option>
                    <option value="unknown">❓ Unknown ({summary['outcomes']['unknown']})</option>
                </select>
            </div>
        </div>
        
        <!-- Dynamic Summary -->
        <div id="dynamicSummary"></div>
        
        <div class="results-count" id="resultsCount">Showing <span>{len(sorted_posts)}</span> posts</div>
        
        <div class="posts-grid" id="postsGrid"></div>
    </div>
    
    <script>
        const threads = {posts_json};
        const failureModeDefs = {failure_defs_json};
        const modelStats = {json.dumps(model_stats)};
        const hwStats = {json.dumps(hw_stats)};
        const failureModeStats = {json.dumps(failure_mode_stats)};
        
        function escapeHtml(text) {{ const div = document.createElement('div'); div.textContent = text; return div.innerHTML; }}
        
        function formatDate(dateStr) {{
            if (!dateStr) return 'Unknown date';
            try {{ return new Date(dateStr).toLocaleDateString('en-US', {{ year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' }}); }}
            catch (e) {{ return dateStr; }}
        }}
        
        function getOutcomeTag(outcome) {{
            const labels = {{ 'success': '✅ Success', 'partial': '⚠️ Partial', 'failed': '❌ Failed', 'unknown': '❓ Unknown' }};
            return `<span class="tag tag-outcome tag-${{outcome}}">${{labels[outcome] || outcome}}</span>`;
        }}
        
        function computeStats(posts) {{
            const stats = {{ total: posts.length, success: 0, partial: 0, failed: 0, unknown: 0, models: {{}}, homeworks: {{}}, failureModes: {{}} }};
            posts.forEach(post => {{
                stats[post.outcome]++;
                stats.models[post.model] = stats.models[post.model] || {{total: 0, success: 0, partial: 0, failed: 0, unknown: 0}};
                stats.models[post.model].total++;
                stats.models[post.model][post.outcome]++;
                stats.homeworks[post.homework] = stats.homeworks[post.homework] || {{total: 0, success: 0, partial: 0, failed: 0, unknown: 0}};
                stats.homeworks[post.homework].total++;
                stats.homeworks[post.homework][post.outcome]++;
                post.failure_modes.forEach(fm => {{ stats.failureModes[fm] = (stats.failureModes[fm] || 0) + 1; }});
            }});
            return stats;
        }}
        
        function renderMiniBar(success, partial, failed, unknown, total) {{
            if (total === 0) return '';
            return `<div class="mini-bar"><div class="mini-bar-segment mini-bar-success" style="width: ${{(success/total*100).toFixed(1)}}%"></div><div class="mini-bar-segment mini-bar-partial" style="width: ${{(partial/total*100).toFixed(1)}}%"></div><div class="mini-bar-segment mini-bar-failed" style="width: ${{(failed/total*100).toFixed(1)}}%"></div><div class="mini-bar-segment mini-bar-unknown" style="width: ${{(unknown/total*100).toFixed(1)}}%"></div></div>`;
        }}
        
        function getTopItems(obj, n=5) {{ return Object.entries(obj).sort((a,b) => b[1].total - a[1].total).slice(0, n); }}
        function getTopFailures(obj, n=5) {{ return Object.entries(obj).sort((a,b) => b[1] - a[1]).slice(0, n); }}
        
        function generateModelInsight(model, stats, successRate, topFailures, hwPerf) {{
            let insight = `<strong>${{model}}</strong> was tested across <strong>${{stats.total}} homework assignments</strong>, achieving a <strong>${{successRate}}% success rate</strong> (${{stats.success}} successes, ${{stats.partial}} partial, ${{stats.failed}} failed). `;
            
            if (parseInt(successRate) >= 70) {{
                insight += `This places it among the <strong>stronger performers</strong> in the class, demonstrating reliable capability across diverse coding tasks. `;
            }} else if (parseInt(successRate) >= 50) {{
                insight += `This represents <strong>moderate performance</strong>, with the model handling straightforward tasks well but requiring more guidance on complex problems. `;
            }} else if (parseInt(successRate) >= 30) {{
                insight += `This indicates <strong>mixed results</strong>, suggesting the model may benefit from more structured prompting, explicit context, or iterative refinement. `;
            }} else if (parseInt(successRate) > 0) {{
                insight += `This suggests the model <strong>struggled significantly</strong> with these tasks and may require substantial human oversight or alternative approaches. `;
            }}
            
            // Add paragraph break for failure analysis
            insight += `</p><p>`;
            
            if (topFailures.length > 0) {{
                const mainFailure = failureModeDefs[topFailures[0][0]];
                insight += `<strong>Primary failure mode:</strong> ${{mainFailure?.label || topFailures[0][0]}} (${{topFailures[0][1]}} occurrences)`;
                if (mainFailure?.description) {{
                    insight += ` — ${{mainFailure.description.toLowerCase()}}`;
                }}
                if (topFailures.length > 1) {{
                    const secondFailure = failureModeDefs[topFailures[1][0]];
                    insight += ` Additionally, <strong>${{secondFailure?.label || topFailures[1][0]}}</strong> appeared ${{topFailures[1][1]}} times`;
                    if (secondFailure?.description) {{
                        insight += ` (${{secondFailure.description.toLowerCase()}})`;
                    }}
                }}
                insight += `. `;
            }}
            
            // Add paragraph break for homework analysis
            insight += `</p><p>`;
            
            const bestHW = hwPerf.filter(h => h.success > 0)[0];
            const worstHW = [...hwPerf].sort((a,b) => a.rate - b.rate).filter(h => h.failed > 0)[0];
            const hwCount = hwPerf.filter(h => h.total > 0).length;
            
            insight += `<strong>Homework coverage:</strong> Tested on ${{hwCount}} different assignments. `;
            
            if (bestHW) {{
                insight += `Best performance on <strong>${{bestHW.hw}}</strong> with ${{bestHW.success}}/${{bestHW.total}} successful attempts (${{Math.round(bestHW.rate)}}% success rate). `;
            }}
            if (worstHW && worstHW.hw !== bestHW?.hw) {{
                insight += `Most challenging: <strong>${{worstHW.hw}}</strong> with ${{worstHW.failed}} failed attempt${{worstHW.failed > 1 ? 's' : ''}}. `;
            }}
            
            // Recommendations
            insight += `</p><p><strong>Recommendation:</strong> `;
            if (parseInt(successRate) >= 60) {{
                insight += `This model is a reliable choice for similar tasks. Consider using it for initial code generation with human review for edge cases.`;
            }} else if (topFailures.length > 0 && topFailures[0][0] === 'dimension_errors') {{
                insight += `Provide explicit tensor shape annotations and consider asking the model to trace through dimensions step-by-step before writing code.`;
            }} else if (topFailures.length > 0 && topFailures[0][0] === 'hyperparameter_tuning') {{
                insight += `Use the model for code structure but rely on human intuition or grid search for hyperparameter selection.`;
            }} else {{
                insight += `Break complex tasks into smaller steps and provide explicit intermediate checkpoints for the model to verify its work.`;
            }}
            
            return insight;
        }}
        
        function generateHWInsight(hw, stats, topFailures, topModels, struggleModels) {{
            const successRate = stats.total > 0 ? ((stats.success / stats.total) * 100).toFixed(0) : 0;
            const modelCount = Object.keys(stats.models).length;
            
            let insight = `<strong>${{hw}}</strong> was attempted by <strong>${{modelCount}} different AI models</strong> across ${{stats.total}} total attempts, achieving an overall success rate of <strong>${{successRate}}%</strong> (${{stats.success}} successes, ${{stats.partial}} partial, ${{stats.failed}} failed). `;
            
            if (parseInt(successRate) >= 70) {{
                insight += `This homework is <strong>well-suited for AI assistance</strong> — most models handled it effectively with minimal human intervention. `;
            }} else if (parseInt(successRate) >= 50) {{
                insight += `This homework is <strong>moderately accessible</strong> for AI models, though some prompting refinement or human guidance may be needed. `;
            }} else if (parseInt(successRate) >= 30) {{
                insight += `This homework <strong>presents a significant challenge</strong> for AI models, often requiring iterative debugging and careful prompt engineering. `;
            }} else {{
                insight += `This homework <strong>proved particularly difficult</strong> for AI models, frequently requiring substantial human intervention to complete. `;
            }}
            
            // Failure analysis paragraph
            insight += `</p><p><strong>Common challenges:</strong> `;
            
            if (topFailures.length > 0) {{
                const mainFailure = failureModeDefs[topFailures[0][0]];
                insight += `The primary issue was <strong>${{mainFailure?.label || topFailures[0][0]}}</strong> (${{topFailures[0][1]}} occurrences)`;
                if (mainFailure?.description) {{
                    insight += ` — ${{mainFailure.description.toLowerCase()}}`;
                }}
                insight += `. `;
                
                if (topFailures.length > 1) {{
                    const otherFailures = topFailures.slice(1, 3).map(([fm, count]) => {{
                        const def = failureModeDefs[fm];
                        return `${{def?.label || fm}} (${{count}})`;
                    }}).join(', ');
                    insight += `Other issues included: ${{otherFailures}}. `;
                }}
            }} else {{
                insight += `No specific failure patterns were identified. `;
            }}
            
            // Model performance paragraph
            insight += `</p><p><strong>Model performance breakdown:</strong> `;
            
            if (topModels.length > 0) {{
                const perfectModels = topModels.filter(m => m.success > 0 && m.failed === 0 && m.partial === 0);
                const goodModels = topModels.filter(m => m.rate >= 60 && m.total >= 1);
                
                if (perfectModels.length > 0) {{
                    insight += `Models with 100% success: ${{perfectModels.slice(0,3).map(m => `<strong>${{m.model}}</strong>`).join(', ')}}. `;
                }}
                
                if (topModels[0].success > 0) {{
                    insight += `Top performer: <strong>${{topModels[0].model}}</strong> with ${{topModels[0].success}}/${{topModels[0].total}} successful (${{Math.round(topModels[0].rate)}}%). `;
                }}
            }}
            
            if (struggleModels.length > 0) {{
                const worstModels = struggleModels.slice(0, 2);
                const worstList = worstModels.map(m => `<strong>${{m.model}}</strong> (${{m.failed}} failed)`).join(', ');
                insight += `Models that struggled: ${{worstList}}. `;
            }}
            
            // Recommendations
            insight += `</p><p><strong>Recommendation:</strong> `;
            if (parseInt(successRate) >= 60) {{
                insight += `This homework is a good candidate for AI-assisted completion. Use any of the top-performing models with standard prompting techniques.`;
            }} else if (topFailures.length > 0 && topFailures[0][0] === 'dimension_errors') {{
                insight += `This homework involves complex tensor operations. Provide shape annotations and ask models to verify dimensions at each step.`;
            }} else if (topFailures.length > 0 && topFailures[0][0] === 'hyperparameter_tuning') {{
                insight += `This homework requires experimental tuning. Use AI for code structure but determine hyperparameters through systematic search.`;
            }} else {{
                insight += `Break this homework into smaller sub-tasks and verify each step before proceeding. Consider using a model from the top performers list.`;
            }}
            
            return insight;
        }}
        
        function generateOverallInsight(stats, topModels, topFailures, overallRate) {{
            const hwCount = Object.keys(stats.homeworks).filter(h => h !== 'Unknown').length;
            const modelCount = Object.keys(stats.models).length;
            
            let insight = `This comprehensive analysis examines <strong>${{stats.total}} student reports</strong> documenting the use of <strong>${{modelCount}} different AI models</strong> across <strong>${{hwCount}} homework assignments</strong>. The overall success rate of <strong>${{overallRate}}%</strong> (${{stats.success}} successes, ${{stats.partial}} partial, ${{stats.failed}} failures) reveals both the impressive capabilities and significant limitations of current AI coding assistants.`;
            
            // Failure analysis paragraph
            insight += `</p><p><strong>Failure Pattern Analysis:</strong> `;
            
            if (topFailures.length >= 1) {{
                const f1 = failureModeDefs[topFailures[0][0]];
                insight += `The dominant failure mode was <strong>${{f1?.label || topFailures[0][0]}}</strong> with ${{topFailures[0][1]}} occurrences`;
                if (f1?.description) {{
                    insight += ` — ${{f1.description.toLowerCase()}}`;
                }}
                insight += `. `;
                
                if (topFailures.length >= 2) {{
                    const f2 = failureModeDefs[topFailures[1][0]];
                    insight += `This was followed by <strong>${{f2?.label || topFailures[1][0]}}</strong> (${{topFailures[1][1]}} occurrences)`;
                    if (f2?.description) {{
                        insight += ` — ${{f2.description.toLowerCase()}}`;
                    }}
                    insight += `. `;
                }}
                
                if (topFailures.length >= 3) {{
                    const otherCount = topFailures.slice(2).reduce((sum, [, count]) => sum + count, 0);
                    insight += `${{topFailures.length - 2}} other failure modes accounted for ${{otherCount}} additional occurrences. `;
                }}
            }}
            
            // Model performance paragraph
            insight += `</p><p><strong>Model Performance:</strong> `;
            
            if (topModels.length > 0) {{
                // Calculate best performing model by success rate (min 3 tests)
                const qualifiedModels = topModels.filter(([m, s]) => s.total >= 3);
                const bySuccessRate = [...qualifiedModels].sort((a, b) => {{
                    const rateA = a[1].total > 0 ? a[1].success / a[1].total : 0;
                    const rateB = b[1].total > 0 ? b[1].success / b[1].total : 0;
                    return rateB - rateA;
                }});
                
                const mostTested = topModels[0];
                const mostTestedRate = mostTested[1].total > 0 ? ((mostTested[1].success / mostTested[1].total) * 100).toFixed(0) : 0;
                insight += `The most frequently tested model was <strong>${{mostTested[0]}}</strong> with ${{mostTested[1].total}} attempts and a ${{mostTestedRate}}% success rate. `;
                
                if (bySuccessRate.length > 0 && bySuccessRate[0][0] !== mostTested[0]) {{
                    const bestRate = bySuccessRate[0];
                    const rate = bestRate[1].total > 0 ? ((bestRate[1].success / bestRate[1].total) * 100).toFixed(0) : 0;
                    insight += `The highest success rate (among models with 3+ tests) was <strong>${{bestRate[0]}}</strong> at ${{rate}}%. `;
                }}
                
                // Mention variety
                insight += `Students tested a diverse range of AI assistants including GPT variants, Claude, Gemini, DeepSeek, and specialized coding tools like Cursor and Codex. `;
            }}
            
            // Key takeaways
            insight += `</p><p><strong>Key Takeaways:</strong> `;
            insight += `AI models excel at <strong>well-defined coding tasks</strong> with clear specifications and straightforward implementations. `;
            insight += `However, they consistently struggle with <strong>hyperparameter selection</strong> (lacking ability to run experiments), <strong>visual reasoning</strong> (misinterpreting graphs and attention visualizations), and <strong>debugging loops</strong> (repeating the same failed fixes). `;
            insight += `For optimal results, provide explicit context, verify intermediate outputs, and use human judgment for experimental parameters.`;
            
            return insight;
        }}
        
        function renderDynamicSummary(model, hw, posts) {{
            const container = document.getElementById('dynamicSummary');
            const stats = computeStats(posts);
            
            if (model && !hw) {{
                // Model-specific summary
                const successRate = stats.total > 0 ? ((stats.success / stats.total) * 100).toFixed(0) : 0;
                const topFailures = getTopFailures(stats.failureModes, 4);
                const hwPerf = Object.entries(stats.homeworks).map(([hw, s]) => ({{hw, ...s, rate: s.total > 0 ? s.success/s.total*100 : 0}})).filter(h => h.total > 0).sort((a,b) => b.rate - a.rate);
                
                container.innerHTML = `<div class="dynamic-summary model-summary">
                    <div class="summary-header"><span class="summary-icon">🤖</span><h2>${{escapeHtml(model)}} Performance Summary</h2></div>
                    <div class="summary-grid">
                        <div class="summary-metric"><div class="summary-metric-value">${{stats.total}}</div><div class="summary-metric-label">Total Tests</div></div>
                        <div class="summary-metric"><div class="summary-metric-value success-rate">${{successRate}}%</div><div class="summary-metric-label">Success Rate</div></div>
                        <div class="summary-metric"><div class="summary-metric-value partial-rate">${{stats.partial}}</div><div class="summary-metric-label">Partial</div></div>
                        <div class="summary-metric"><div class="summary-metric-value fail-rate">${{stats.failed}}</div><div class="summary-metric-label">Failed</div></div>
                    </div>
                    ${{renderMiniBar(stats.success, stats.partial, stats.failed, stats.unknown, stats.total)}}
                    <div class="summary-details">
                        ${{hwPerf.length > 0 ? `<div class="summary-detail-card"><h4>📚 Performance by Homework</h4><ul class="summary-list">${{hwPerf.slice(0,5).map(h => `<li><span class="summary-list-name">${{h.hw}}</span><span class="summary-list-value">${{h.success}}/${{h.total}} success</span></li>`).join('')}}</ul></div>` : ''}}
                        ${{topFailures.length > 0 ? `<div class="summary-detail-card"><h4>⚠️ Common Issues</h4><ul class="summary-list">${{topFailures.map(([fm, count]) => `<li><span class="summary-list-name">${{failureModeDefs[fm]?.label || fm}}</span><span class="summary-list-value" style="color: var(--accent-tertiary)">${{count}}</span></li>`).join('')}}</ul></div>` : ''}}
                    </div>
                    <div class="summary-insight"><h4>💡 Model Insight</h4><p>${{generateModelInsight(model, stats, successRate, topFailures, hwPerf)}}</p></div>
                </div>`;
            }} else if (hw && !model) {{
                // Homework-specific summary
                const topModels = Object.entries(stats.models).map(([m, s]) => ({{model: m, ...s, rate: s.total > 0 ? s.success/s.total*100 : 0}})).filter(m => m.total > 0).sort((a,b) => b.rate - a.rate);
                const struggleModels = topModels.filter(m => m.failed > 0).sort((a,b) => b.failed - a.failed);
                const topFailures = getTopFailures(stats.failureModes, 4);
                
                container.innerHTML = `<div class="dynamic-summary hw-summary">
                    <div class="summary-header"><span class="summary-icon">📚</span><h2>${{escapeHtml(hw)}} Analysis</h2></div>
                    <div class="summary-grid">
                        <div class="summary-metric"><div class="summary-metric-value">${{stats.total}}</div><div class="summary-metric-label">Attempts</div></div>
                        <div class="summary-metric"><div class="summary-metric-value success-rate">${{stats.success}}</div><div class="summary-metric-label">Success</div></div>
                        <div class="summary-metric"><div class="summary-metric-value partial-rate">${{stats.partial}}</div><div class="summary-metric-label">Partial</div></div>
                        <div class="summary-metric"><div class="summary-metric-value fail-rate">${{stats.failed}}</div><div class="summary-metric-label">Failed</div></div>
                    </div>
                    ${{renderMiniBar(stats.success, stats.partial, stats.failed, stats.unknown, stats.total)}}
                    <div class="summary-details">
                        ${{topModels.length > 0 ? `<div class="summary-detail-card"><h4>🏆 Top Performing Models</h4><ul class="summary-list">${{topModels.slice(0,4).map(m => `<li><span class="summary-list-name">${{m.model}}</span><span class="summary-list-value">${{m.success}}/${{m.total}}</span></li>`).join('')}}</ul></div>` : ''}}
                        ${{topFailures.length > 0 ? `<div class="summary-detail-card"><h4>⚠️ What Models Struggled With</h4><ul class="summary-list">${{topFailures.map(([fm, count]) => `<li><span class="summary-list-name">${{failureModeDefs[fm]?.label || fm}}</span><span class="summary-list-value" style="color: var(--accent-tertiary)">${{count}}</span></li>`).join('')}}</ul></div>` : ''}}
                        ${{struggleModels.length > 0 ? `<div class="summary-detail-card"><h4>❌ Models That Struggled</h4><ul class="summary-list">${{struggleModels.slice(0,4).map(m => `<li><span class="summary-list-name">${{m.model}}</span><span class="summary-list-value" style="color: var(--failed)">${{m.failed}} failed</span></li>`).join('')}}</ul></div>` : ''}}
                    </div>
                    <div class="summary-insight"><h4>💡 Homework Insight</h4><p>${{generateHWInsight(hw, stats, topFailures, topModels, struggleModels)}}</p></div>
                </div>`;
            }} else if (!model && !hw) {{
                // Overall summary
                const topModels = getTopItems(stats.models, 5);
                const topFailures = getTopFailures(stats.failureModes, 5);
                const overallRate = stats.total > 0 ? ((stats.success / stats.total) * 100).toFixed(0) : 0;
                
                container.innerHTML = `<div class="dynamic-summary overall-summary">
                    <div class="summary-header"><span class="summary-icon">📊</span><h2>Overall Analysis Summary</h2></div>
                    <div class="summary-grid">
                        <div class="summary-metric"><div class="summary-metric-value">${{stats.total}}</div><div class="summary-metric-label">Posts</div></div>
                        <div class="summary-metric"><div class="summary-metric-value success-rate">${{overallRate}}%</div><div class="summary-metric-label">Success Rate</div></div>
                        <div class="summary-metric"><div class="summary-metric-value">${{Object.keys(stats.models).length}}</div><div class="summary-metric-label">Models</div></div>
                        <div class="summary-metric"><div class="summary-metric-value">${{Object.keys(stats.homeworks).filter(h => h !== 'Unknown').length}}</div><div class="summary-metric-label">HWs</div></div>
                    </div>
                    ${{renderMiniBar(stats.success, stats.partial, stats.failed, stats.unknown, stats.total)}}
                    <div class="summary-details">
                        ${{topModels.length > 0 ? `<div class="summary-detail-card"><h4>🏆 Most Tested Models</h4><ul class="summary-list">${{topModels.map(([m, s]) => `<li><span class="summary-list-name">${{m}}</span><span class="summary-list-value">${{s.success}}/${{s.total}} wins</span></li>`).join('')}}</ul></div>` : ''}}
                        ${{topFailures.length > 0 ? `<div class="summary-detail-card"><h4>⚠️ Top Failure Modes</h4><ul class="summary-list">${{topFailures.map(([fm, count]) => `<li><span class="summary-list-name">${{failureModeDefs[fm]?.label || fm}}</span><span class="summary-list-value" style="color: var(--accent-tertiary)">${{count}}</span></li>`).join('')}}</ul></div>` : ''}}
                    </div>
                    <div class="summary-insight"><h4>💡 Key Insights</h4><p>${{generateOverallInsight(stats, topModels, topFailures, overallRate)}}</p></div>
                </div>`;
            }} else {{
                // Both filters active
                container.innerHTML = `<div class="dynamic-summary">
                    <div class="summary-header"><span class="summary-icon">🔍</span><h2>${{escapeHtml(model)}} on ${{escapeHtml(hw)}}</h2></div>
                    <div class="summary-grid">
                        <div class="summary-metric"><div class="summary-metric-value">${{stats.total}}</div><div class="summary-metric-label">Posts</div></div>
                        <div class="summary-metric"><div class="summary-metric-value success-rate">${{stats.success}}</div><div class="summary-metric-label">Success</div></div>
                        <div class="summary-metric"><div class="summary-metric-value partial-rate">${{stats.partial}}</div><div class="summary-metric-label">Partial</div></div>
                        <div class="summary-metric"><div class="summary-metric-value fail-rate">${{stats.failed}}</div><div class="summary-metric-label">Failed</div></div>
                    </div>
                    ${{renderMiniBar(stats.success, stats.partial, stats.failed, stats.unknown, stats.total)}}
                </div>`;
            }}
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
            document.getElementById('resultsCount').innerHTML = `Showing <span>${{posts.length}}</span> posts`;
            
            if (posts.length === 0) {{ 
                grid.innerHTML = `<div class="no-posts"><h2>No posts found</h2><p>Try adjusting your filters.</p></div>`; 
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
                                        <div class="post-content" id="content-${{globalIdx}}">${{escapeHtml(post.content).replace(/\\n/g, '<br>')}}</div>
                                        <button class="expand-btn" onclick="toggleExpand(${{globalIdx}})">Show more</button>
                                        ${{post.failure_modes.length > 0 ? `<div class="failure-tags">${{post.failure_modes.map(fm => `<span class="failure-tag">${{failureModeDefs[fm]?.label || fm}}</span>`).join('')}}</div>` : ''}}
                                        ${{post.observations && post.observations.length > 0 ? `
                                            <div class="observations">
                                                <h5>📋 Key Observations</h5>
                                                <ul>
                                                    ${{post.observations.slice(0, 5).map(obs => `
                                                        <li class="obs-${{obs.type}}">
                                                            <span class="obs-icon">${{obs.type === 'strength' ? '✅' : obs.type === 'weakness' ? '❌' : '📝'}}</span>
                                                            ${{escapeHtml(obs.text)}}
                                                        </li>
                                                    `).join('')}}
                                                </ul>
                                            </div>
                                        ` : ''}}
                                        <div class="post-footer">
                                            ${{post.has_pdf ? '<span class="pdf-badge">📄 PDF Analyzed</span>' : ''}}
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
        
        function toggleExpand(idx) {{
            const content = document.getElementById(`content-${{idx}}`);
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
                const matchesSearch = !search || post.title.toLowerCase().includes(search) || post.content.toLowerCase().includes(search);
                const matchesModel = !model || post.model === model;
                const matchesHw = !hw || post.homework === hw;
                const matchesOutcome = !outcome || post.outcome === outcome;
                return matchesSearch && matchesModel && matchesHw && matchesOutcome;
            }});
            
            renderDynamicSummary(model, hw, filtered);
            renderPosts(filtered);
        }}
        
        document.getElementById('searchInput').addEventListener('input', filterPosts);
        document.getElementById('modelFilter').addEventListener('change', filterPosts);
        document.getElementById('hwFilter').addEventListener('change', filterPosts);
        document.getElementById('outcomeFilter').addEventListener('change', filterPosts);
        
        // Render failure mode cards
        function renderFailureCards() {{
            const container = document.getElementById('failureCards');
            const sortedModes = Object.entries(failureModeStats)
                .sort((a, b) => b[1].total - a[1].total);
            
            container.innerHTML = sortedModes.map(([fmId, stats]) => {{
                const def = failureModeDefs[fmId] || {{}};
                const topModels = Object.entries(stats.by_model || {{}})
                    .sort((a, b) => b[1] - a[1])
                    .slice(0, 5);
                
                return `
                    <div class="failure-card" onclick="toggleFailureCard(this)">
                        <div class="failure-card-header">
                            <span class="failure-card-title">
                                ⚠️ ${{def.label || fmId}}
                            </span>
                            <span class="failure-card-count">${{stats.total}} occurrences</span>
                        </div>
                        <p class="failure-card-short">${{def.description || ''}}</p>
                        <div class="failure-card-detailed">
                            ${{formatDetailedDescription(def.detailed_description || '')}}
                            ${{topModels.length > 0 ? `
                            <div class="failure-card-models">
                                <h5>Models Most Affected</h5>
                                <div class="model-chips">
                                    ${{topModels.map(([model, count]) => 
                                        `<span class="model-chip">${{model}} (${{count}})</span>`
                                    ).join('')}}
                                </div>
                            </div>
                            ` : ''}}
                        </div>
                        <div style="text-align: center; margin-top: 12px;">
                            <span class="expand-indicator">▼ Click to expand</span>
                        </div>
                    </div>
                `;
            }}).join('');
        }}
        
        function formatDetailedDescription(text) {{
            if (!text) return '';
            // Convert markdown-style bold to HTML
            return text
                .replace(/[*][*](.*?)[*][*]/g, '<strong>$1</strong>')
                .split('\\n').join('<br>');
        }}
        
        function toggleFailureCard(card) {{
            const wasExpanded = card.classList.contains('expanded');
            // Close all cards
            document.querySelectorAll('.failure-card').forEach(c => c.classList.remove('expanded'));
            // Toggle this one
            if (!wasExpanded) {{
                card.classList.add('expanded');
                card.querySelector('.expand-indicator').textContent = '▲ Click to collapse';
            }} else {{
                card.querySelector('.expand-indicator').textContent = '▼ Click to expand';
            }}
        }}
        
        // Initial render
        renderFailureCards();
        renderDynamicSummary('', '', threads);
        renderPosts(threads);
    </script>
</body>
</html>
"""

# Write the HTML file
os.makedirs('output', exist_ok=True)
output_path = 'output/index.html'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"✅ Website built successfully at {output_path}")
print(f"\n📊 Summary:")
print(f"   - Total posts: {summary['total_posts']}")
print(f"   - Models: {summary['total_models']}")
print(f"   - Homeworks: {summary['total_homeworks']}")
print(f"   - Overall success rate: {summary['overall_success_rate']}%")

