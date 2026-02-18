# SPDX-FileCopyrightText: Copyright (c) 2025, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Prompt optimization utilities for MAS workflow.

This module provides utilities to optimize prompts by:
- Compressing SOP templates and long text sections
- Using structured data instead of verbose text
- Chunking large prompts when needed
- Reducing redundancy in prompt construction
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Maximum prompt length before chunking (in characters)
MAX_PROMPT_LENGTH = 8000  # Conservative limit for most LLMs
CHUNK_OVERLAP = 200  # Characters to overlap between chunks


def compress_sop_summary(summary: str) -> str:
    """Compress SOP summary by removing redundancy and using abbreviations.
    
    Args:
        summary: Full SOP summary text
        
    Returns:
        Compressed version with key information preserved
    """
    # Replace verbose phrases with shorter equivalents
    replacements = {
        "MUST appear on EVERY HTML page with IDENTICAL structure": "ALL pages: identical structure",
        "localStorage-based with add/remove/update quantity": "localStorage: add/remove/update qty",
        "Updates header cart display": "Updates header cart",
        "must be called after every cart operation": "call after cart ops",
        "If \"products.json\" is in SHARED_ASSETS": "If products.json in SHARED_ASSETS",
        "Engineer MUST generate products.json file": "Generate products.json",
        "HTML has empty container": "HTML: empty container",
        "JavaScript loads from JSON": "JS: load from JSON",
        "Products loaded from products.json": "Load from JSON",
        "JavaScript MUST handle fetch errors": "JS: handle fetch errors",
        "Must attach event listeners": "Attach event listeners",
        "Works with active filter": "Works with filter",
        "Searches product names (case-insensitive, partial match)": "Search: names (case-insensitive)",
        "Debounced (300ms recommended)": "Debounced ~300ms",
        "ALL pages share IDENTICAL": "ALL pages: identical",
        "JavaScript detects current page": "JS: detect current page",
        "All event listeners check if elements exist": "Check elements exist before attach",
    }
    
    compressed = summary
    for old, new in replacements.items():
        compressed = compressed.replace(old, new)
    
    # Remove excessive whitespace
    lines = [line.strip() for line in compressed.split('\n') if line.strip()]
    compressed = '\n'.join(lines)
    
    return compressed


def compress_component_snippets(snippets: str) -> str:
    """Compress component snippets by removing verbose comments.
    
    Args:
        snippets: Full component snippets text
        
    Returns:
        Compressed version with essential information
    """
    # Remove verbose comments, keep essential structure
    lines = snippets.split('\n')
    compressed_lines = []
    skip_comment = False
    
    for line in lines:
        stripped = line.strip()
        # Skip verbose comment lines
        if stripped.startswith('<!--') and 'Copy to EVERY' in stripped:
            skip_comment = True
            continue
        if skip_comment and stripped.endswith('-->'):
            skip_comment = False
            continue
        if skip_comment:
            continue
        
        # Keep essential lines
        if stripped and not (stripped.startswith('<!--') and len(stripped) > 50):
            compressed_lines.append(line)
    
    return '\n'.join(compressed_lines)


def structure_prompt_data(data: dict[str, Any]) -> str:
    """Convert structured data to compact prompt format.
    
    Instead of verbose text descriptions, use structured format that's
    easier for LLMs to parse and more token-efficient.
    
    Args:
        data: Dictionary with structured data
        
    Returns:
        Compact string representation
    """
    parts = []
    
    for key, value in data.items():
        if isinstance(value, dict):
            parts.append(f"{key}:")
            for sub_key, sub_value in value.items():
                parts.append(f"  {sub_key}: {sub_value}")
        elif isinstance(value, list):
            parts.append(f"{key}: {', '.join(str(v) for v in value)}")
        else:
            parts.append(f"{key}: {value}")
    
    return "\n".join(parts)


def chunk_prompt(prompt: str, max_length: int = MAX_PROMPT_LENGTH, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split large prompt into chunks if it exceeds max_length.
    
    Args:
        prompt: Full prompt text
        max_length: Maximum length per chunk
        overlap: Number of characters to overlap between chunks
        
    Returns:
        List of prompt chunks (or single chunk if prompt is short enough)
    """
    if len(prompt) <= max_length:
        return [prompt]
    
    logger.warning(f"Prompt length {len(prompt)} exceeds max {max_length}, chunking...")
    
    chunks = []
    start = 0
    
    # Try to split at section boundaries first
    section_markers = ['===', '##', '---', '\n\n\n']
    
    while start < len(prompt):
        end = start + max_length
        
        if end >= len(prompt):
            # Last chunk
            chunks.append(prompt[start:])
            break
        
        # Try to find a good split point
        best_split = end
        for marker in section_markers:
            # Look for marker before end
            marker_pos = prompt.rfind(marker, start, end)
            if marker_pos > start:
                best_split = marker_pos
                break
        
        # If no marker found, split at last newline
        if best_split == end:
            newline_pos = prompt.rfind('\n', start, end)
            if newline_pos > start:
                best_split = newline_pos
        
        chunk = prompt[start:best_split].strip()
        if chunk:
            chunks.append(chunk)
        
        # Move start back by overlap to maintain context
        start = max(start + 1, best_split - overlap)
    
    logger.info(f"Split prompt into {len(chunks)} chunks")
    return chunks


def optimize_engineer_brief(
    sop_summary: str,
    component_snippets: str,
    structured_rules: str,
    compress: bool = True,
) -> str:
    """Optimize engineer brief by compressing sections and using structured format.
    
    Args:
        sop_summary: SOP summary text
        component_snippets: Component snippets text
        structured_rules: Structured rules text
        compress: Whether to compress sections
        
    Returns:
        Optimized brief
    """
    if compress:
        sop_summary = compress_sop_summary(sop_summary)
        component_snippets = compress_component_snippets(component_snippets)
    
    # Build optimized brief
    brief_parts = [
        "=== SOFTWARE ENGINEER BRIEF ===",
        "Phase 4 Software Engineer. Follow strict ReAct format.",
        "",
        "=== SOP SUMMARY (COMPRESSED) ===",
        sop_summary,
        "",
        "=== COMPONENT SNIPPETS ===",
        component_snippets,
        "",
        "=== STRUCTURED RULES ===",
        structured_rules,
        "",
        "CRITICAL: Follow SOP templates above. Reference full SOPs if needed.",
        "",
        "CODE QUALITY: Production-ready, modern practices, error handling, accessible, responsive.",
        "",
        "TASK: Generate files from STEPS in structured handoff below.",
        "",
        "WORKFLOW per STEP:",
        "1. Thought: Plan implementation",
        "2. Action: code_generation_tool (with enhanced query)",
        "3. Observation: Review code quality",
        "4. [Optional] Action: code_generation_tool (refine if needed)",
        "5. Action: save_file_code",
        "6. Verify and continue",
        "",
        "After all files: Final Answer confirming completion.",
    ]
    
    optimized = "\n".join(brief_parts)
    
    # Check if needs chunking
    if len(optimized) > MAX_PROMPT_LENGTH:
        logger.warning("Optimized brief still exceeds max length, consider further compression")
    
    return optimized


def create_structured_handoff_prompt(handoff_data: dict[str, Any]) -> str:
    """Create prompt from structured handoff data in compact format.
    
    Args:
        handoff_data: Structured handoff dictionary
        
    Returns:
        Compact prompt representation
    """
    parts = ["=== STRUCTURED HANDOFF ==="]
    
    # Use compact format for each section
    if "project_name" in handoff_data:
        parts.append(f"PROJECT: {handoff_data['project_name']}")
    
    if "files" in handoff_data:
        file_list = [f.get("name", "") for f in handoff_data["files"]]
        parts.append(f"FILES: {', '.join(file_list)}")
    
    if "tasks" in handoff_data:
        parts.append(f"TASKS: {len(handoff_data['tasks'])} steps")
        for i, task in enumerate(handoff_data["tasks"][:5], 1):  # Show first 5
            filename = task.get("filename", "")
            constraints_preview = task.get("constraints", "")[:100]
            parts.append(f"  Step {i}: {filename} - {constraints_preview}...")
        if len(handoff_data["tasks"]) > 5:
            parts.append(f"  ... and {len(handoff_data['tasks']) - 5} more steps")
    
    if "products" in handoff_data:
        product_count = len(handoff_data["products"])
        parts.append(f"PRODUCTS: {product_count} items")
        # Show first 3 products as examples
        for product in handoff_data["products"][:3]:
            name = product.get("name", "")
            price = product.get("price", 0)
            parts.append(f"  - {name}: ${price:.2f}")
        if product_count > 3:
            parts.append(f"  ... and {product_count - 3} more")
    
    if "categories" in handoff_data:
        parts.append(f"CATEGORIES: {', '.join(handoff_data['categories'][:10])}")
    
    if "shared_assets" in handoff_data:
        assets = [a.get("name", "") for a in handoff_data["shared_assets"]]
        parts.append(f"SHARED_ASSETS: {', '.join(assets)}")
    
    return "\n".join(parts)


def estimate_token_count(text: str) -> int:
    """Estimate token count for text (rough approximation).
    
    Args:
        text: Text to estimate
        
    Returns:
        Estimated token count (using ~4 chars per token approximation)
    """
    return len(text) // 4


def get_prompt_stats(prompt: str) -> dict[str, Any]:
    """Get statistics about a prompt.
    
    Args:
        prompt: Prompt text
        
    Returns:
        Dictionary with stats (length, estimated_tokens, sections, etc.)
    """
    sections = prompt.count("===")
    lines = len(prompt.split('\n'))
    words = len(prompt.split())
    
    return {
        "length": len(prompt),
        "estimated_tokens": estimate_token_count(prompt),
        "lines": lines,
        "words": words,
        "sections": sections,
        "needs_chunking": len(prompt) > MAX_PROMPT_LENGTH,
    }

