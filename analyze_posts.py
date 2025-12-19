#!/usr/bin/env python3
"""
Analyze posts and create enriched data with proper categorization.
Incorporates PDF content when available.
"""

import json
import re
import os
from collections import defaultdict

# Load raw posts
with open('output/posts_raw.json', 'r') as f:
    posts = json.load(f)

# Load all extracted content (PDFs, Google Docs, etc.) and merge with posts
external_content_map = {}

# Try the comprehensive extraction first
all_extractions_path = 'output/all_extractions.json'
pdf_extractions_path = 'output/pdf_extractions.json'

if os.path.exists(all_extractions_path):
    with open(all_extractions_path, 'r') as f:
        all_data = json.load(f)
    
    for item in all_data:
        post_id = item['thread_id']
        content = item.get('content', '')
        if post_id in external_content_map:
            external_content_map[post_id] += "\n\n" + content
        else:
            external_content_map[post_id] = content
    
    print(f"📄 Loaded external content for {len(external_content_map)} posts ({sum(len(v) for v in external_content_map.values()):,} chars)")

elif os.path.exists(pdf_extractions_path):
    with open(pdf_extractions_path, 'r') as f:
        pdf_data = json.load(f)
    
    for item in pdf_data:
        post_id = item['post_id']
        combined_pdf_text = "\n\n".join(pdf['text'] for pdf in item['pdfs'])
        external_content_map[post_id] = combined_pdf_text
    
    print(f"📄 Loaded PDF content for {len(external_content_map)} posts")
else:
    print("⚠️  No external content found - run extract_all_content.py for richer analysis")

# Alias for backwards compatibility
pdf_content_map = external_content_map

# ============================================================================
# MODEL EXTRACTION - More precise patterns
# ============================================================================

def extract_model(title, content):
    """Extract the specific model name from title and content."""
    text = f"{title} {content}"
    
    # Ordered from most specific to least specific
    model_patterns = [
        # OpenAI Models
        (r'chatgpt[\s\-]*5\.1[\s\-]*pro', 'ChatGPT 5.1 Pro'),
        (r'chatgpt[\s\-]*5\.1[\s\-]*(?:extended[\s\-]*)?thinking', 'ChatGPT 5.1 Thinking'),
        (r'chatgpt[\s\-]*5\.1[\s\-]*standard', 'ChatGPT 5.1'),
        (r'chatgpt[\s\-]*5\.1', 'ChatGPT 5.1'),
        (r'gpt[\s\-]*5\.1[\s\-]*pro', 'GPT 5.1 Pro'),
        (r'gpt[\s\-]*5\.1[\s\-]*thinking', 'GPT 5.1 Thinking'),
        (r'gpt[\s\-]*5\.1', 'GPT 5.1'),
        (r'gpt[\s\-]*5[\s\-]*pro', 'GPT 5 Pro'),
        (r'gpt[\s\-]*5[\s\-]*thinking', 'GPT 5 Thinking'),
        (r'chatgpt[\s\-]*5', 'ChatGPT 5'),
        (r'gpt[\s\-]*5', 'GPT 5'),
        (r'chatgpt', 'ChatGPT'),
        (r'codex[\s\-]*5\.1[\s\-]*high', 'Codex 5.1 High'),
        (r'codex[\s\-]*5\.1', 'Codex 5.1'),
        (r'codex', 'Codex'),
        
        # Claude Models
        (r'claude[\s\-]*code[\s\-]*(?:with[\s\-]*)?opus[\s\-]*4\.5', 'Claude Code (Opus 4.5)'),
        (r'claude[\s\-]*opus[\s\-]*4\.5[\s\-]*(?:extended[\s\-]*)?thinking', 'Claude Opus 4.5 Thinking'),
        (r'opus[\s\-]*4\.5[\s\-]*(?:extended[\s\-]*)?thinking', 'Claude Opus 4.5 Thinking'),
        (r'claude[\s\-]*opus[\s\-]*4\.5', 'Claude Opus 4.5'),
        (r'opus[\s\-]*4\.5', 'Claude Opus 4.5'),
        (r'claude[\s\-]*sonnet[\s\-]*4\.5', 'Claude Sonnet 4.5'),
        (r'sonnet[\s\-]*4\.5', 'Claude Sonnet 4.5'),
        (r'haiku[\s\-]*4\.5', 'Claude Haiku 4.5'),
        (r'claude[\s\-]*code', 'Claude Code'),
        (r'claude', 'Claude'),
        
        # Gemini Models
        (r'gemini[\s\-]*(?:thinking[\s\-]*with[\s\-]*)?pro[\s\-]*3', 'Gemini Pro 3'),
        (r'gemini[\s\-]*3[\s\-]*pro', 'Gemini Pro 3'),
        (r'gemini[\s\-]*pro[\s\-]*2\.5', 'Gemini Pro 2.5'),
        (r'gemini[\s\-]*2\.5[\s\-]*pro', 'Gemini Pro 2.5'),
        (r'google[\s\-]*ai[\s\-]*studio.*gemini[\s\-]*2\.5[\s\-]*pro', 'Gemini Pro 2.5'),
        (r'gemini[\s\-]*pro', 'Gemini Pro'),
        (r'gemini[\s\-]*(?:in[\s\-]*)?colla?b', 'Gemini (Colab)'),
        (r'gemini', 'Gemini'),
        
        # DeepSeek Models
        (r'deepseek[\s\-]*v3\.2', 'DeepSeek V3.2'),
        (r'deep[\s\-]*seek[\s\-]*v3\.2', 'DeepSeek V3.2'),
        (r'deepseek[\s\-]*r1', 'DeepSeek R1'),
        (r'deep[\s\-]*seek', 'DeepSeek'),
        (r'deepseek', 'DeepSeek'),
        
        # Cursor/IDE Models
        (r'cursor[\s\-]*(?:auto[\s\-]*)?agent', 'Cursor Agent'),
        (r'cursor[\s\-]*composer', 'Cursor Composer'),
        (r'cursor[\s\-]*\(?opus[\s\-]*4\.5\)?', 'Cursor (Opus 4.5)'),
        (r'cursor', 'Cursor'),
        (r'windsurf[\s\-]*swe[\s\-]*1', 'Windsurf SWE-1'),
        (r'windsurf', 'Windsurf'),
        
        # Qwen Models
        (r'qwen3[\s\-]*max', 'Qwen3-Max'),
        (r'qwen[\s\-]*3[\s\-]*max', 'Qwen3-Max'),
        (r'qwen', 'Qwen'),
        
        # Mistral Models
        (r'mistral[\s\-]*(?:ai\'?s?[\s\-]*)?le[\s\-]*chat', 'Mistral Le Chat'),
        (r'mistral[\s\-]*ai', 'Mistral'),
        (r'mistral', 'Mistral'),
        
        # Grok Models
        (r'grok[\s\-]*4\.1', 'Grok 4.1'),
        (r'grok[\s\-]*(?:with[\s\-]*)?fast[\s\-]*mode', 'Grok (Fast Mode)'),
        (r'gork', 'Grok'),  # typo in one post
        (r'grok', 'Grok'),
        
        # Kimi Models
        (r'kimi[\s\-]*k2', 'Kimi K2'),
        (r'kimi[\s\-]*1\.5', 'Kimi 1.5'),
        (r'kimi', 'Kimi'),
        
        # Perplexity
        (r'perplexity[\s\-]*pro', 'Perplexity Pro'),
        (r'perplexity', 'Perplexity'),
        
        # Llama
        (r'llama[\s\-]*4[\s\-]*maverick', 'Llama 4 Maverick'),
        (r'llama', 'Llama'),
        
        # Other
        (r'seed[\s\-]*1\.6', 'Seed 1.6 (ByteDance)'),
        (r'aider', 'Aider'),
        (r'cline', 'Cline'),
        (r'replit', 'Replit'),
    ]
    
    for pattern, model_name in model_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return model_name
    
    return "Unknown"


def extract_homework(title, content):
    """Extract homework number from title and content."""
    text = f"{title}"  # Prioritize title for HW number
    
    # Look for HW patterns
    matches = re.findall(r'hw[\s\-_]*0*(\d+)|homework[\s\-_]*0*(\d+)', text, re.IGNORECASE)
    for match in matches:
        hw_num = match[0] or match[1]
        if hw_num:
            return f"HW{int(hw_num)}"
    
    # Also check content if not in title
    text = content
    matches = re.findall(r'hw[\s\-_]*0*(\d+)|homework[\s\-_]*0*(\d+)', text, re.IGNORECASE)
    for match in matches:
        hw_num = match[0] or match[1]
        if hw_num:
            return f"HW{int(hw_num)}"
    
    return "Unknown"


# ============================================================================
# FAILURE MODE ANALYSIS - Based on actual post content analysis
# ============================================================================

FAILURE_PATTERNS = {
    'hallucination': {
        'keywords': [
            'hallucinate', 'hallucination', 'hallucinated', 'made up', 'fabricate',
            'invented', 'imagined', 'claims.*not.*true', 'confidently.*wrong',
            'described patterns that did not match', 'hallucinations'
        ],
        'label': 'Hallucination',
        'short_description': 'Model generated plausible but incorrect information',
        'detailed_description': '''Models frequently generated confident but incorrect outputs across several categories. **Visual hallucinations** were particularly common: when asked to interpret attention visualizations or graphs, models like Claude and Qwen would describe patterns that didn't exist—claiming strong attention between specific tokens when the actual visualization showed weak or no connection. **Solution drift** was another pattern where models would subtly shift what a function was supposed to do mid-debugging, even suggesting "fixes" they had already tried as if they didn't remember previous attempts. Models also exhibited **documentation hallucinations**, writing confident claims about code being "highly optimized" or "production-ready" when the actual implementation didn't match these claims. This was especially problematic in GPU optimization tasks where models would claim their convolution implementations were equivalent to reference solutions despite numerical differences of 0.3+.'''
    },
    'context_loss': {
        'keywords': [
            'lost context', 'forgot', 'context window', 'lost track', 
            'didn\'t remember', 'context limit', 'large context',
            'long context', 'context.*struggle'
        ],
        'label': 'Context Loss',
        'short_description': 'Model lost track of earlier conversation or code',
        'detailed_description': '''Models struggled to maintain coherent understanding across long interactions and complex codebases. In multi-step debugging sessions, models would sometimes suggest the same incorrect fix multiple times, appearing to "forget" they had already tried it. When working with large Jupyter notebooks, models would lose track of variable definitions from earlier cells or ignore function signatures defined pages ago. This was particularly problematic for HW8's SSM implementations and HW10's transformer notebooks, where understanding the full context was essential. Some models also exhibited **echo chamber behavior**, reinforcing their own incorrect conclusions from earlier in the conversation rather than reconsidering when presented with contradictory evidence.'''
    },
    'wrong_algorithm': {
        'keywords': [
            'wrong algorithm', 'misunderstood', 'wrong approach', 'misinterpreted',
            'missed the point', 'completely wrong', 'fundamentally.*wrong',
            'proposed.*different.*solution', 'instead.*proposed'
        ],
        'label': 'Wrong Algorithm/Approach',
        'short_description': 'Model used incorrect algorithm or methodology',
        'detailed_description': '''Models occasionally proposed fundamentally incorrect approaches that revealed a misunderstanding of the problem requirements. A notable example from HW7: when asked to implement classical spectral clustering (adjacency matrix → normalize → SVD → K-Means), Windsurf instead proposed a deep learning solution using PyTorch Geometric's GCNConv layers and a graph autoencoder with KL divergence loss—completely missing the point of the assignment. Similarly, models sometimes inverted mathematical relationships (using exp(+γ) instead of exp(-γ) in RBF kernels) or applied the wrong scaling factors in optimization algorithms. These errors often stemmed from pattern-matching to familiar problems rather than carefully reading the specific requirements.'''
    },
    'api_confusion': {
        'keywords': [
            'wrong api', 'api confusion', 'wrong function', 'wrong library',
            'imported function', 'couldn\'t find.*function', 'niche function',
            'unfamiliar.*package', 'didn\'t use.*helper'
        ],
        'label': 'API/Library Confusion',
        'short_description': 'Model struggled with specific library functions or APIs',
        'detailed_description': '''Models frequently failed to properly utilize helper functions and library APIs provided in the assignment context. When functions from imported packages weren't explicitly shown in the code, models would avoid using them or guess at their signatures incorrectly. DeepSeek, for example, required "goading" to actually use imported functions and often got them wrong on first attempts. Models also confused similar APIs (using numpy functions when PyTorch was expected), created their own implementations instead of using provided utilities, or used deprecated/non-existent function parameters. This suggests models rely heavily on their training data for API knowledge and struggle with project-specific or recently-updated libraries.'''
    },
    'dimension_errors': {
        'keywords': [
            'dimension', 'shape error', 'shape mismatch', 'broadcasting',
            'tensor.*shape', 'wrong.*dimension', 'RuntimeError.*dimension',
            'size mismatch'
        ],
        'label': 'Dimension/Shape Errors',
        'short_description': 'Model made errors with tensor dimensions or shapes',
        'detailed_description': '''Tensor dimension mismatches were among the most common implementation bugs. Models would treat diagonal matrices as 2D tensors instead of 1D vectors, leading to RuntimeErrors during broadcasting. In attention implementations, models frequently miscalculated the output shapes after matrix multiplications or failed to properly handle the batch dimension. Convolution-based SSM implementations were particularly problematic—models would set up kernels and apply them in ways that didn't correspond to the actual mathematical formulas, confusing per-channel elementwise operations with full matrix multiplications. Many of these errors only surfaced when running sanity checks against reference implementations, revealing differences of 0.3+ rather than the expected ~1e-8.'''
    },
    'instruction_violation': {
        'keywords': [
            'didn\'t follow', 'ignored.*instruction', 'violated.*constraint',
            'despite.*explicit', 'even though.*asked', 'failed to follow',
            'didn\'t stick to', 'changed.*unrelated', 'modified.*shouldn\'t'
        ],
        'label': 'Instruction Violation',
        'short_description': 'Model didn\'t follow explicit instructions or constraints',
        'detailed_description': '''Models frequently ignored explicit constraints or modified code outside the designated TODO regions. When asked to "adjust the two previous functions," Claude created entirely new functions instead of modifying existing ones. Models would change hyperparameters, learning rates, or initialization schemes without being asked—making "silent modifications" without explanation. One particularly frustrating pattern: when constrained to modify only the faster optimizer's learning rate, Mistral changed both optimizers despite the asymmetrical constraint being clearly stated. Models also sometimes claimed to have run notebook cells when they actually hadn't, or stated they had "looked at" visualizations without actually processing them.'''
    },
    'hyperparameter_tuning': {
        'keywords': [
            'hyperparameter', 'learning rate', 'couldn\'t.*tune', 'parameter.*tuning',
            'trial.*error', 'grid search', 'couldn\'t find.*parameters',
            'parameters.*didn\'t work'
        ],
        'label': 'Hyperparameter Tuning',
        'short_description': 'Model struggled with finding correct hyperparameters',
        'detailed_description': '''Finding optimal hyperparameters was a consistent weakness across all models. When asked to suggest learning rates, weight scales, or training configurations, models would propose values that either diverged or underperformed significantly. GPT 5 Pro took 40+ minutes of thinking for hyperparameter suggestions that still didn't work, requiring multiple rounds of re-prompting. Models showed reluctance to make "large jumps" in hyperparameter space, preferring small conservative changes even when dramatic adjustments were needed. Without the ability to actually run code and observe results, models essentially had to guess—and their guesses were often based on general heuristics that didn't apply to the specific problem. Some models even proposed configurations that performed worse than their previous suggestions.'''
    },
    'visual_reasoning': {
        'keywords': [
            'couldn\'t.*see', 'visual.*reasoning', 'couldn\'t.*interpret.*image',
            'vision.*unreliable', 'couldn\'t.*read.*graph', 'image.*understanding',
            'plot.*interpretation', 'visual.*blind'
        ],
        'label': 'Visual Reasoning Issues',
        'short_description': 'Model struggled to interpret images or visualizations',
        'detailed_description': '''Visual understanding emerged as a major limitation, particularly for HW9's attention visualization tasks. Claude's vision was described as "extremely unreliable"—it would confidently describe attention patterns that didn't match the actual visualizations, requiring users to manually describe images in text form. Qwen frequently claimed strong connections between tokens when the graph showed barely visible lines. Models struggled with complex attention diagrams that had 12 layers × 12 heads = 144 possible views, often defaulting to general knowledge about transformer behavior rather than actually interpreting the specific plots. When models couldn't see images, they would answer conceptual questions based on theoretical expectations rather than empirical observations, leading to plausible but ungrounded responses.'''
    },
    'conceptual_gap': {
        'keywords': [
            'conceptual.*gap', 'didn\'t understand', 'misconception',
            'theoretical.*weak', 'conceptual.*error', 'wrong.*intuition',
            'misunderstand.*concept'
        ],
        'label': 'Conceptual Understanding Gap',
        'short_description': 'Model lacked deep understanding of underlying concepts',
        'detailed_description': '''While models excelled at pattern-matching familiar code structures, they sometimes revealed gaps in deeper conceptual understanding. Gemini initially claimed convolution was strictly faster on CPU without considering the O(H³) cost of kernel generation. Models would apply formulas correctly but fail to understand why—for instance, implementing correct attention code but then providing wrong interpretations of what the attention weights signified. When problems required "outside the box" thinking (like modifying a computation graph in novel ways), models struggled significantly compared to straightforward implementation tasks. This suggests models may be better at translating explicit mathematical formulas into code than reasoning about novel adaptations of known concepts.'''
    },
    'debugging_struggles': {
        'keywords': [
            'couldn\'t.*debug', 'stuck.*loop', 'repeated.*same.*error',
            'couldn\'t.*fix', 'debugging.*difficult', 'multiple.*tries',
            'iteration.*still.*wrong', 'couldn\'t.*recover'
        ],
        'label': 'Debugging Struggles',
        'short_description': 'Model had difficulty identifying and fixing errors',
        'detailed_description': '''When initial implementations failed tests, models often struggled to identify root causes and implement correct fixes. Kimi K2 exhibited a pattern of proposing small modifications to broken code rather than reconsidering the fundamental approach—when one idea wasn't working, it kept trying variations instead of stepping back. Models would sometimes enter "debugging loops" where they cycled through the same few attempted fixes. Claude Haiku showed "drift" behavior where, after fixing code to use correct nested loops, later documentation still referenced earlier incorrect implementations. Interestingly, providing explicit error traces and sanity check outputs significantly improved debugging success—models performed much better when they could see exactly how their output differed from expected values rather than just knowing something was wrong.'''
    },
    'verbosity': {
        'keywords': [
            'too verbose', 'verbose', 'unnecessarily.*long', 'chatty',
            'too.*explanation', 'overly.*detailed'
        ],
        'label': 'Excessive Verbosity',
        'short_description': 'Model produced unnecessarily long or wordy responses',
        'detailed_description': '''Several models, particularly those with "thinking" modes enabled, produced unnecessarily lengthy responses that made review tedious. GPT-5.1 was described as "chatty," using more "human-friendly" language and attempting to be conversational when directness would have been more useful. Thinking-mode models would sometimes take 40+ minutes to generate responses for simple problems. DeepSeek was noted as "occasionally verbose" even when providing correct solutions. For conceptual questions, models would repeat the same idea in different words multiple times rather than stating it once clearly. This verbosity wasn't just about length—it often obscured the key information students needed, requiring them to parse through explanations to find the actual answer.'''
    },
    'overcomplicated': {
        'keywords': [
            'overcomplicate', 'over-engineer', 'too complex', 'unnecessarily complex',
            'could have simply', 'simple.*fix', 'overcomplicat'
        ],
        'label': 'Overcomplicated Solution',
        'short_description': 'Model made simple problems unnecessarily complex',
        'detailed_description': '''Models sometimes proposed elaborate solutions when simple ones would suffice. When facing an "adam" vs "sgd" update_rule error, GPT 5 Pro spent over a minute generating a "much more complex" corrected version when simply changing one string would have worked. Models would create new variables and functions instead of reusing existing code, breaking downstream dependencies. In HW2's optimization tasks, Grok wrote entirely new variable names for the momentum implementation rather than tweaking the existing parameters—both approaches work, but the new variables caused later graph-comparison code to fail. This tendency toward complexity over simplicity made the code harder to integrate with existing notebooks and introduced unnecessary failure points.'''
    }
}


def extract_failure_modes(content):
    """Extract failure modes from post content."""
    content_lower = content.lower()
    found_failures = []
    
    for failure_id, failure_info in FAILURE_PATTERNS.items():
        for keyword in failure_info['keywords']:
            if re.search(keyword, content_lower):
                found_failures.append(failure_id)
                break
    
    return found_failures


# ============================================================================
# SUCCESS/OUTCOME ANALYSIS
# ============================================================================

def analyze_outcome(content):
    """Analyze the overall outcome: success, partial, or failed."""
    content_lower = content.lower()
    
    # Strong success indicators
    strong_success = [
        'one-shot', 'one shot', 'oneshot', 'zero-shot', 'zero shot',
        'one-shotted', 'correctly solved', 'perfectly', 'flawless',
        'all.*correct', '100%', 'excellent', 'exceptional', 'impressive',
        'very strong', 'very well', 'no issues', 'no errors',
        'without.*correction', 'without.*debugging'
    ]
    
    # Partial success indicators
    partial_indicators = [
        'eventually', 'after.*prompting', 'with.*hint', 'needed.*help',
        'required.*guidance', 'with.*nudge', 'after.*feedback',
        'minor.*error', 'small.*mistake', 'mostly.*correct',
        'almost.*correct', 'close', 'nearly'
    ]
    
    # Failure indicators
    failure_indicators = [
        'failed', 'couldn\'t', 'unable to', 'struggled significantly',
        'did not work', 'incorrect', 'wrong', 'disappointed',
        'poor performance', 'multiple.*error', 'kept.*failing'
    ]
    
    success_score = sum(1 for ind in strong_success if re.search(ind, content_lower))
    partial_score = sum(1 for ind in partial_indicators if re.search(ind, content_lower))
    failure_score = sum(1 for ind in failure_indicators if re.search(ind, content_lower))
    
    # Weight the scores
    if failure_score > success_score + 2:
        return 'failed'
    elif success_score > 0 and partial_score > success_score:
        return 'partial'
    elif success_score >= 2:
        return 'success'
    elif partial_score > 0:
        return 'partial'
    elif failure_score > 0:
        return 'failed'
    return 'unknown'


def extract_key_observations(content):
    """Extract key observations and insights from the post and PDF annotations."""
    observations = []
    
    # Look for explicit strengths
    strength_patterns = [
        (r'strength[s]?:?\s*([^.!?]+[.!?])', 'Strength'),
        (r'worked well:?\s*([^.!?]+[.!?])', 'Worked Well'),
        (r'excelled at:?\s*([^.!?]+[.!?])', 'Excelled At'),
        (r'strong at:?\s*([^.!?]+[.!?])', 'Strong At'),
        (r'impressive[ly]?\s+([^.!?]+[.!?])', 'Impressive'),
        (r'correctly\s+([^.!?]+[.!?])', 'Correct'),
        (r'one[- ]?shot(?:ted|ting)?\s*([^.!?]*[.!?])?', 'One-Shot'),
        (r'nailed\s+([^.!?]+[.!?])', 'Nailed'),
        (r'perfect(?:ly)?\s+([^.!?]+[.!?])', 'Perfect'),
    ]
    
    # Look for explicit weaknesses
    weakness_patterns = [
        (r'weakness[es]?:?\s*([^.!?]+[.!?])', 'Weakness'),
        (r'struggled with:?\s*([^.!?]+[.!?])', 'Struggled With'),
        (r'failed to:?\s*([^.!?]+[.!?])', 'Failed To'),
        (r'limitation[s]?:?\s*([^.!?]+[.!?])', 'Limitation'),
        (r'incorrect(?:ly)?\s+([^.!?]+[.!?])', 'Incorrect'),
        (r'error:?\s*([^.!?]+[.!?])', 'Error'),
        (r'bug:?\s*([^.!?]+[.!?])', 'Bug'),
        (r'wrong\s+([^.!?]+[.!?])', 'Wrong'),
        (r'confused\s+([^.!?]+[.!?])', 'Confused'),
    ]
    
    # Look for specific annotations (common in PDF annotations)
    annotation_patterns = [
        (r'\[annotation\]:?\s*([^.!?\n]+)', 'Annotation'),
        (r'comment:?\s*([^.!?\n]+)', 'Comment'),
        (r'note:?\s*([^.!?\n]+)', 'Note'),
        (r'fix(?:ed)?:?\s*([^.!?\n]+)', 'Fix'),
        (r'issue:?\s*([^.!?\n]+)', 'Issue'),
    ]
    
    for pattern, label in strength_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches[:3]:  # Limit to 3 per pattern
            if match and len(match.strip()) > 10:  # Minimum length filter
                observations.append({'type': 'strength', 'label': label, 'text': match.strip()[:200]})
    
    for pattern, label in weakness_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches[:3]:
            if match and len(match.strip()) > 10:
                observations.append({'type': 'weakness', 'label': label, 'text': match.strip()[:200]})
    
    for pattern, label in annotation_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches[:5]:  # More annotations allowed
            if match and len(match.strip()) > 5:
                observations.append({'type': 'annotation', 'label': label, 'text': match.strip()[:200]})
    
    # Extract bullet-pointed observations (common in PDFs)
    bullet_patterns = [
        r'[•●○◦▪▸]\s*([^\n•●○◦▪▸]{20,200})',  # Bullet points
        r'^\s*[-–—]\s+([^\n]{20,200})',  # Dashes
        r'^\s*\d+[.)]\s+([^\n]{20,200})',  # Numbered lists
    ]
    
    for pattern in bullet_patterns:
        matches = re.findall(pattern, content, re.MULTILINE)
        for match in matches[:5]:
            text = match.strip()
            # Classify the bullet based on content
            if any(w in text.lower() for w in ['good', 'correct', 'success', 'well', 'proper']):
                observations.append({'type': 'strength', 'label': 'Observation', 'text': text[:200]})
            elif any(w in text.lower() for w in ['wrong', 'error', 'fail', 'issue', 'bug', 'incorrect']):
                observations.append({'type': 'weakness', 'label': 'Observation', 'text': text[:200]})
    
    # Deduplicate by text similarity
    unique_observations = []
    seen_texts = set()
    for obs in observations:
        text_key = obs['text'][:50].lower()
        if text_key not in seen_texts:
            seen_texts.add(text_key)
            unique_observations.append(obs)
    
    return unique_observations[:20]  # Cap at 20 observations


# ============================================================================
# PROCESS ALL POSTS
# ============================================================================

enriched_posts = []

for post in posts:
    title = post['title']
    content = post['content']
    post_id = post.get('id')
    
    # Merge PDF content if available (PDF annotations are more detailed)
    pdf_text = pdf_content_map.get(post_id, '')
    full_content = content + "\n\n--- PDF ANNOTATIONS ---\n" + pdf_text if pdf_text else content
    
    model = extract_model(title, full_content)
    homework = extract_homework(title, full_content)
    failure_modes = extract_failure_modes(full_content)
    outcome = analyze_outcome(full_content)
    observations = extract_key_observations(full_content)
    
    # Track if this post has PDF annotations
    has_pdf = bool(pdf_text)
    
    enriched_posts.append({
        **post,
        'model': model,
        'homework': homework,
        'failure_modes': failure_modes,
        'outcome': outcome,
        'observations': observations,
        'has_pdf': has_pdf,
        'pdf_char_count': len(pdf_text) if pdf_text else 0
    })

# ============================================================================
# GENERATE STATISTICS
# ============================================================================

model_stats = defaultdict(lambda: {
    'total': 0, 
    'success': 0, 
    'partial': 0, 
    'failed': 0, 
    'unknown': 0,
    'homeworks': defaultdict(int),
    'failure_modes': defaultdict(int)
})

hw_stats = defaultdict(lambda: {
    'total': 0,
    'success': 0,
    'partial': 0,
    'failed': 0,
    'unknown': 0,
    'models': defaultdict(int),
    'failure_modes': defaultdict(int)
})

failure_mode_stats = defaultdict(lambda: {
    'total': 0,
    'by_model': defaultdict(int),
    'by_homework': defaultdict(int)
})

for post in enriched_posts:
    model = post['model']
    hw = post['homework']
    outcome = post['outcome']
    failure_modes = post['failure_modes']
    
    # Model stats
    model_stats[model]['total'] += 1
    model_stats[model][outcome] += 1
    model_stats[model]['homeworks'][hw] += 1
    for fm in failure_modes:
        model_stats[model]['failure_modes'][fm] += 1
    
    # HW stats
    hw_stats[hw]['total'] += 1
    hw_stats[hw][outcome] += 1
    hw_stats[hw]['models'][model] += 1
    for fm in failure_modes:
        hw_stats[hw]['failure_modes'][fm] += 1
    
    # Failure mode stats
    for fm in failure_modes:
        failure_mode_stats[fm]['total'] += 1
        failure_mode_stats[fm]['by_model'][model] += 1
        failure_mode_stats[fm]['by_homework'][hw] += 1

# Convert defaultdicts to regular dicts for JSON serialization
def convert_defaultdict(d):
    if isinstance(d, defaultdict):
        d = {k: convert_defaultdict(v) for k, v in d.items()}
    return d

analysis_output = {
    'posts': enriched_posts,
    'model_stats': convert_defaultdict(dict(model_stats)),
    'hw_stats': convert_defaultdict(dict(hw_stats)),
    'failure_mode_stats': convert_defaultdict(dict(failure_mode_stats)),
    'failure_mode_definitions': {
        fm_id: {
            'label': fm_info['label'],
            'description': fm_info['short_description'],
            'detailed_description': fm_info['detailed_description']
        }
        for fm_id, fm_info in FAILURE_PATTERNS.items()
    },
    'summary': {
        'total_posts': len(enriched_posts),
        'total_models': len(model_stats),
        'total_homeworks': len([h for h in hw_stats if h != 'Unknown']),
        'overall_success_rate': round(
            sum(1 for p in enriched_posts if p['outcome'] == 'success') / len(enriched_posts) * 100, 1
        ),
        'outcomes': {
            'success': sum(1 for p in enriched_posts if p['outcome'] == 'success'),
            'partial': sum(1 for p in enriched_posts if p['outcome'] == 'partial'),
            'failed': sum(1 for p in enriched_posts if p['outcome'] == 'failed'),
            'unknown': sum(1 for p in enriched_posts if p['outcome'] == 'unknown')
        },
        'posts_with_pdf': sum(1 for p in enriched_posts if p.get('has_pdf')),
        'top_failure_mode': max(
            [(FAILURE_PATTERNS[fm]['label'], stats['total']) for fm, stats in failure_mode_stats.items()],
            key=lambda x: x[1]
        ) if failure_mode_stats else None,
        'top_model': max(
            [(m, stats['total']) for m, stats in model_stats.items() if m != 'Unknown'],
            key=lambda x: x[1]
        ) if model_stats else None
    }
}

# Save enriched data
with open('output/posts_analyzed.json', 'w', encoding='utf-8') as f:
    json.dump(analysis_output, f, indent=2, ensure_ascii=False)

print(f"✅ Analyzed {len(enriched_posts)} posts")
print(f"   - Models detected: {len(model_stats)}")
print(f"   - Homeworks covered: {len([h for h in hw_stats if h != 'Unknown'])}")
print(f"   - Failure modes tracked: {len(failure_mode_stats)}")
print(f"\n📊 Outcome distribution:")
print(f"   - Success: {analysis_output['summary']['outcomes']['success']}")
print(f"   - Partial: {analysis_output['summary']['outcomes']['partial']}")
print(f"   - Failed: {analysis_output['summary']['outcomes']['failed']}")
print(f"   - Unknown: {analysis_output['summary']['outcomes']['unknown']}")

print(f"\n🤖 Top models by posts:")
for model, stats in sorted(model_stats.items(), key=lambda x: x[1]['total'], reverse=True)[:10]:
    print(f"   - {model}: {stats['total']} posts")

print(f"\n⚠️  Top failure modes:")
for fm, stats in sorted(failure_mode_stats.items(), key=lambda x: x[1]['total'], reverse=True)[:8]:
    print(f"   - {FAILURE_PATTERNS[fm]['label']}: {stats['total']} occurrences")

print(f"\n💾 Saved to output/posts_analyzed.json")

