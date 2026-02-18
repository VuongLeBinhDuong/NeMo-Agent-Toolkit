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

"""Coordinator that orchestrates the MAS multi-agent workflow via Python."""

import json
import logging
import re
import textwrap
from pathlib import Path
from typing import Awaitable, Callable

from nat.builder.builder import Builder
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.component_ref import FunctionRef
from nat.data_models.function import FunctionBaseConfig

from .cache import cached_read_file
from .code_quality_enhancements import (
    build_enhanced_code_generation_query,
    get_relevant_examples,
)
from .config import get_config
from .prompt_sections import SOP_REFERENCE_TEXT, render_prompt_sections
from .sop_templates import get_component_snippets_text, get_sop_summary
from .structured_handoff import (
    format_handoff_for_agent,
    load_handoff_json,
    parse_project_manager_output_to_handoff,
    save_handoff_json,
)


def _map_filename_to_programming_language(filename: str) -> str:
    """Map filename extension to programming language format accepted by code_generation_tool."""
    filename_lower = filename.lower()
    
    # Extension to language mapping
    extension_map = {
        ".html": "HTML",
        ".htm": "HTML",
        ".css": "CSS",
        ".js": "JavaScript",
        ".javascript": "JavaScript",
        ".ts": "TypeScript",
        ".typescript": "TypeScript",
        ".py": "Python",
        ".python": "Python",
        ".java": "Java",
        ".cpp": "C++",
        ".cxx": "C++",
        ".cc": "C++",
        ".c": "C",
        ".cs": "C#",
        ".go": "Go",
        ".rs": "Rust",
        ".swift": "Swift",
        ".kt": "Kotlin",
        ".php": "PHP",
        ".rb": "Ruby",
        ".scala": "Scala",
        ".hs": "Haskell",
        ".clj": "Clojure",
        ".r": "R",
        ".m": "MATLAB",
        ".jl": "Julia",
        ".dart": "Dart",
        ".lua": "Lua",
        ".pl": "Perl",
        ".sh": "Shell",
        ".bash": "Bash",
        ".ps1": "PowerShell",
        ".sql": "SQL",
        ".xml": "XML",
        ".yaml": "YAML",
        ".yml": "YAML",
        ".json": "JSON",
    }
    
    # Check if filename has extension
    if "." in filename_lower:
        ext = "." + filename_lower.split(".")[-1]
        if ext in extension_map:
            return extension_map[ext]
    
    # Direct language name mapping (case-insensitive)
    language_map = {
        "html": "HTML",
        "css": "CSS",
        "javascript": "JavaScript",
        "js": "JavaScript",
        "typescript": "TypeScript",
        "ts": "TypeScript",
        "python": "Python",
        "py": "Python",
        "java": "Java",
        "c++": "C++",
        "cpp": "C++",
        "c#": "C#",
        "csharp": "C#",
        "go": "Go",
        "rust": "Rust",
        "swift": "Swift",
        "kotlin": "Kotlin",
        "php": "PHP",
        "ruby": "Ruby",
        "scala": "Scala",
        "haskell": "Haskell",
        "clojure": "Clojure",
        "r": "R",
        "matlab": "MATLAB",
        "julia": "Julia",
        "dart": "Dart",
        "lua": "Lua",
        "perl": "Perl",
        "shell": "Shell",
        "bash": "Bash",
        "powershell": "PowerShell",
        "sql": "SQL",
        "xml": "XML",
        "yaml": "YAML",
        "json": "JSON",
    }
    
    # Try direct match
    if filename_lower in language_map:
        return language_map[filename_lower]
    
    # Default: capitalize first letter
    return filename.capitalize()


def _get_information_site_checklist(filename: str) -> str:
    """Get information_site-specific checklist for a given filename.
    
    Args:
        filename: Name of the file being generated
        
    Returns:
        Checklist string if applicable, empty string otherwise
    """
    file_type = filename.split(".")[-1].lower() if "." in filename else ""
    
    if file_type == "html":
        return (
            "MANDATORY CHECKLIST FOR information_site HTML FILES:\n"
            "□ Header nav: MUST NOT include shop.html, cart.html, checkout.html links\n"
            "□ Header nav: MUST ONLY include pages from FILES list (e.g., index.html, matches.html, results.html, about.html)\n"
            "□ Header: MUST NOT include <div class=\"header__cart\"> or any cart-related elements\n"
            "□ Header: MUST NOT include id=\"cart-count\", id=\"cart-subtotal\", or cart-icon\n"
            "□ Container IDs: MUST NOT use id=\"products-container\"\n"
            "□ Container IDs: MUST use domain-appropriate IDs (e.g., id=\"matches-container\", id=\"results-list\")\n"
            "VERIFY ALL ITEMS BEFORE GENERATING CODE. If any item is violated, regenerate the code.\n"
        )
    elif file_type in ("js", "javascript"):
        return (
            "MANDATORY CHECKLIST FOR information_site JavaScript FILES:\n"
            "□ Classes: MUST NOT use ProductManager or CartManager\n"
            "□ Classes: MUST use domain-appropriate classes (e.g., MatchManager, ResultsManager)\n"
            "□ Data loading: MUST NOT use fetch('products.json')\n"
            "□ Data loading: MUST use fetch paths from SHARED_ASSETS (e.g., fetch('matches.json'), fetch('results.json'))\n"
            "□ Container selectors: MUST NOT use getElementById('products-container')\n"
            "□ Container selectors: MUST use domain-appropriate IDs (e.g., getElementById('matches-container'), getElementById('results-list'))\n"
            "VERIFY ALL ITEMS BEFORE GENERATING CODE. If any item is violated, regenerate the code.\n"
        )
    elif file_type == "json":
        # For JSON files, check if it's matches.json or results.json
        if "match" in filename.lower():
            return (
                "MANDATORY CHECKLIST FOR information_site matches.json:\n"
                "□ Structure: MUST use { \"matches\": [...] } format, NOT { \"products\": [...] }\n"
                "□ Data fields: MUST include match-specific fields (e.g., home_team, away_team, date, venue, league)\n"
            )
        elif "result" in filename.lower():
            return (
                "MANDATORY CHECKLIST FOR information_site results.json:\n"
                "□ Structure: MUST use { \"results\": [...] } format, NOT { \"products\": [...] }\n"
                "□ Data fields: MUST include result-specific fields (e.g., home_team, away_team, home_score, away_score, date)\n"
            )
    
    return ""


def _get_engineer_brief(website_type: str = "") -> str:
    """Get engineer brief with SOP templates included.
    
    Args:
        website_type: Optional website type to customize SOPs. If not provided, returns generic version.
    """
    sop_summary = get_sop_summary(website_type)
    structured_rules = render_prompt_sections()
    component_snippets = get_component_snippets_text(website_type)
    
    return f"""
=== SOFTWARE ENGINEER BRIEF ===
You are Phase 4 Software Engineer. You MUST follow strict ReAct format.

NOTE: This prompt is used when automatic code generation is not available. Follow the instructions below to generate and save all files.

{sop_summary}
{component_snippets}
{structured_rules}

CRITICAL: When generating code, you MUST follow the SOP templates summarized above for default component behaviors.
DO NOT invent or guess implementations - use the standardized specifications exactly as specified. Reference the SOP module when you need the full text.

CODE QUALITY MANDATE:
- Generate PRODUCTION-READY code, not prototypes or demos
- Follow modern best practices and coding standards
- Ensure code is maintainable, accessible, and performant
- Include proper error handling and edge case coverage
- Use semantic HTML, modern CSS, and ES6+ JavaScript
- Add comments for complex logic
- Ensure code integrates seamlessly with other files

CRITICAL REQUIREMENTS:
- When saving code, extract ONLY the actual code content - remove ALL markdown fences (```language and ```)
- For CSS files: Use ONLY pure CSS - NO SCSS/SASS functions (darken(), lighten(), @mixin, @include)
- For products.json: Verify it matches requirements from project manager (correct number of products, correct categories)
- For filter/sort logic: Ensure filter values match product categories exactly
- NAMING CONTRACT (CRITICAL): All shared layout components MUST use the following BEM-style class names consistently across EVERY HTML file and in styles.css. You MUST NOT generate CSS selectors like ".site-header", ".primary-nav", ".top-nav", etc. for the shared header/footer/product grid; instead, you MUST style the canonical classes below, which the HTML must also use:
  * Header (shared on all pages): header, header__container, header__logo, header__nav, header__nav-list, header__nav-item, header__nav-link, header__search, header__search-input (id="search-input"), header__cart, header__cart-link, header__cart-icon, header__cart-count (id="cart-count"), header__cart-subtotal (id="cart-subtotal").
  * Footer (shared on all pages): footer, footer__container, footer__about, footer__about-title, footer__about-text, footer__nav, footer__nav-list, footer__nav-item, footer__nav-link, footer__social, footer__social-list, footer__social-item, footer__social-link, footer__social-icon, footer__bottom, footer__bottom-text.
  * Product listing: products, products__title, products__container (id="products-container"), product-card, product-card__image, product-card__info, product-card__title, product-card__price, product-card__category, product-card__description, product-card__badge, product-card__actions, product-card__button (e.g., .add-to-cart-btn).
  * Shop controls: shop-controls, shop-controls__filter, shop-controls__sort, shop-controls__label, shop-controls__select (with ids filter-select/category-filter and sort-select/sort-by as defined in SOPs).
  For every shared component above, ensure that:
  - HTML files use these exact class names, and
  - styles.css defines the visual design primarily using these same class selectors (you may add modifier classes, but you must not ignore or rename the base classes).

Your task: Generate and save all files listed in STEPS from the structured handoff data below.

For each STEP (in order from EXTRACTED_PROJECT_MANAGER_CONTENT):

Thought: Analyze requirements for [filename] and plan high-quality, production-ready implementation following modern best practices
Action: code_generation_tool
Action Input: {{"query": "[BUILD ENHANCED QUERY with quality guidelines, requirements, related files context, and code examples]", "programming_language": "[LANGUAGE]"}}
Observation: [The tool will return code, possibly wrapped in markdown code fences like ```html or ```javascript. The actual code is between the fences.]
Thought: Review the generated code. Does it meet quality standards? Is it production-ready? Check for: proper error handling, modern syntax, accessibility, responsive design, and integration with related files.
[If code needs improvement, call code_generation_tool again with refinement request]
Thought: Code is production-ready. CRITICAL: Extract the actual code content by removing ALL markdown fences (```language and ```). The code_content must be pure code without any markdown syntax. For CSS files, ensure NO SCSS/SASS functions (darken, lighten, @mixin, etc.) - use only pure CSS.
Action: save_file_code
Action Input: {{"file_path": "output/[PROJECT_NAME]/[filename]", "code_content": "[EXTRACTED PURE CODE - NO markdown fences, NO ```css or ```javascript, just the actual code content]"}}
Observation: [Wait for confirmation that file was saved]

After all files saved:
Thought: confirm completion
Final Answer: All files have been successfully generated and saved to output/[PROJECT_NAME]/.

All execution guardrails (naming, HTML/CSS/JS rules, products.json handling, SOP adherence, tool usage, verification, and final reporting) are already enumerated within the structured sections above. Follow those sections exactly once—do not restate or reinterpret them.

{SOP_REFERENCE_TEXT}
"""

# ENGINEER_BRIEF will be generated dynamically with website_type in _response_fn
# This is a fallback for backward compatibility
ENGINEER_BRIEF = _get_engineer_brief()

logger = logging.getLogger(__name__)

DEFAULT_AGENT_STATUSES = {
    "product_manager": "Product specification saved",
    "architect": "Architecture design saved",
    "project_manager": "Project plan saved",
}


class MASWorkflowEngineerPhaseConfig(FunctionBaseConfig, name="engineer_phase"):
    """Configuration for the MAS workflow engineer phase."""

    engineer: FunctionRef


def _extract_status(agent_name: str, output_text: str) -> str:
    """Extract STATUS line from an agent's output."""

    for line in output_text.splitlines():
        stripped_line = line.strip()
        if stripped_line.startswith("STATUS:"):
            status = stripped_line.split("STATUS:", 1)[1].strip()
            if status:
                return status
    json_match = re.search(r'"STATUS"\s*:\s*"([^"]+)"', output_text)
    if json_match:
        return json_match.group(1).strip()
    single_quote_match = re.search(r"'STATUS'\s*:\s*'([^']+)'", output_text)
    if single_quote_match:
        return single_quote_match.group(1).strip()
    recovered_status = _recover_status_from_tool_call(agent_name, output_text)
    if recovered_status:
        return recovered_status
    raise ValueError(f"{agent_name} did not return a STATUS line")


def _recover_status_from_tool_call(agent_name: str, output_text: str) -> str | None:
    """Attempt to recover STATUS by executing the agent's intended tool call."""

    triple_double = re.search(r'"code_content"\s*:\s*"""(.*?)"""', output_text, re.DOTALL)
    triple_single = re.search(r"'code_content'\s*:\s*'''(.*?)'''", output_text, re.DOTALL)
    code_match = triple_double or triple_single
    if not code_match:
        return None

    file_path_match = re.search(r'"file_path"\s*:\s*"([^"]+)"', output_text)
    if not file_path_match:
        file_path_match = re.search(r"'file_path'\s*:\s*'([^']+)'", output_text)
    if not file_path_match:
        return None

    code_content = textwrap.dedent(code_match.group(1))
    normalized_content = (
        code_content.replace("\r\n", "\n")
        .replace("\u2022", "-")
        .replace("•", "-")
        .strip("\n")
    )

    file_path = Path(file_path_match.group(1))
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(f"{normalized_content}\n", encoding="utf-8")

    for expected_status in DEFAULT_AGENT_STATUSES.values():
        if expected_status in output_text:
            status = expected_status
            break
    else:
        status = DEFAULT_AGENT_STATUSES.get(agent_name, "Completed")

    logger.warning(
        "Recovered %s output by writing %s due to missing STATUS line",
        agent_name,
        file_path,
    )
    return status


async def _invoke_agent(
    agent_name: str,
    agent_call: Callable[[str], Awaitable[str]],
    payload: str,
) -> str:
    """Invoke an agent tool and return its string output."""

    result = await agent_call(payload)
    if not isinstance(result, str):
        raise TypeError(f"Expected {agent_name} output to be a string")
    return result


def _extract_content_from_file_reader_response(response: str) -> str:
    """Extract actual content from file_reader response."""
    content_marker = "Content:"
    content_idx = response.find(content_marker)
    
    if content_idx == -1:
        logger.warning("No 'Content:' marker found in file_reader response, returning as-is")
        return response
    
    # Extract everything after "Content:" and the newline
    extracted = response[content_idx + len(content_marker):].lstrip('\n\r')
    logger.info(f'Successfully extracted content (length: {len(extracted)} chars)')
    return extracted


def _verify_products_json_requirements(
    products_json_path: Path,
    handoff,
    pm_content: str
) -> None:
    """Verify products.json matches requirements from project manager.
    
    Args:
        products_json_path: Path to products.json file
        handoff: StructuredHandoff object with project info
        pm_content: Raw project manager output text for parsing requirements
        
    Raises:
        ValueError: If products.json doesn't match requirements
    """
    if not products_json_path.exists():
        return  # Will be caught by other validation
    
    try:
        products_data = json.loads(products_json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return  # Will be caught by other validation
    
    if isinstance(products_data, dict) and "products" in products_data:
        product_list = products_data["products"]
    elif isinstance(products_data, list):
        product_list = products_data
    else:
        return  # Will be caught by other validation
    
    if not isinstance(product_list, list):
        return
    
    # Try to extract requirements from PM content
    # Look for PRODUCTS section with product count
    products_section = re.search(r'PRODUCTS:\s*\n(.*?)(?=\n[A-Z_]+:|$)', pm_content, re.DOTALL)
    if products_section:
        products_text = products_section.group(1)
        # Count products listed (lines starting with number)
        required_count = len(re.findall(r'^\d+\.', products_text, re.MULTILINE))
        if required_count > 0 and len(product_list) < required_count:
            logger.warning(
                f"Products.json has {len(product_list)} products, but requirements specify {required_count} products"
            )
    
    # Check categories match requirements
    categories_section = re.search(r'CATEGORIES:\s*\n(.*?)(?=\n[A-Z_]+:|$)', pm_content, re.DOTALL)
    if categories_section:
        categories_text = categories_section.group(1)
        # Extract category names (lines starting with -)
        required_categories = set(
            line.strip().lstrip('- ').strip()
            for line in categories_text.split('\n')
            if line.strip().startswith('-')
        )
        
        if required_categories:
            actual_categories = set(p.get('category', '') for p in product_list if p.get('category'))
            missing_categories = required_categories - actual_categories
            if missing_categories:
                logger.warning(
                    f"Products.json missing required categories: {', '.join(missing_categories)}"
                )


def _extract_website_type(pm_content: str) -> str | None:
    """Extract WEBSITE_TYPE from the project manager content, if present.

    Expected format (case-insensitive on key, but not on value):
        WEBSITE_TYPE: information_site|ecommerce_site|web_app
    """
    if not pm_content:
        return None

    match = re.search(r"WEBSITE_TYPE\s*:\s*([a-zA-Z_]+)", pm_content)
    if not match:
        return None

    return match.group(1).strip()


def _validate_code_before_save(filename: str, code_content: str) -> list[str]:
    """Validate code content before saving and return list of warnings/errors.
    
    Args:
        filename: Name of the file being saved
        code_content: The code content to validate
        
    Returns:
        List of validation error/warning messages (empty if no issues)
    """
    errors = []
    
    if not code_content or not code_content.strip():
        errors.append("Code content is empty")
        return errors
    
    # Check for markdown fences (should have been removed by extract function)
    if code_content.strip().startswith('```'):
        errors.append("CRITICAL: Code still contains markdown fence at start - extraction may have failed")
    
    if code_content.strip().endswith('```'):
        errors.append("CRITICAL: Code still contains markdown fence at end - extraction may have failed")
    
    # Check for CSS-specific issues
    if filename.endswith('.css'):
        # Check for SCSS/SASS functions that don't work in pure CSS
        scss_functions = ['darken(', 'lighten(', '@mixin', '@include', '@import']
        for func in scss_functions:
            if func in code_content:
                errors.append(f"CRITICAL: CSS contains SCSS/SASS function '{func}' - this will not work in pure CSS")
        
        # Check for balanced braces (basic syntax check)
        open_braces = code_content.count('{')
        close_braces = code_content.count('}')
        if open_braces != close_braces:
            errors.append(f"CRITICAL: Unbalanced CSS braces ({open_braces} open, {close_braces} close)")
    
    # Check for HTML-specific issues
    if filename.endswith(('.html', '.htm')):
        # Basic HTML structure check
        if '<!DOCTYPE' not in code_content and '<html' not in code_content:
            # Might be a fragment, that's okay
            pass
        else:
            # Should have closing tags
            if code_content.count('<html') > code_content.count('</html'):
                errors.append("WARNING: HTML may be missing closing </html> tag")
    
    # Check for JavaScript-specific issues
    if filename.endswith(('.js', '.javascript')):
        # Check for balanced braces and parentheses
        open_braces = code_content.count('{')
        close_braces = code_content.count('}')
        if open_braces != close_braces:
            errors.append(f"WARNING: Unbalanced JavaScript braces ({open_braces} open, {close_braces} close)")
    
    return errors


def _extract_code_from_markdown(code_text: str) -> str:
    """Extract code from markdown code fences if present.
    
    This function handles multiple cases:
    - Code wrapped in ```language ... ```
    - Code starting with ```css or ```javascript
    - Code with multiple code blocks (takes the first/largest one)
    - Plain code without fences
    """
    if not code_text or not code_text.strip():
        return ""
    
    # Remove leading/trailing whitespace
    code_text = code_text.strip()
    
    # Check if content starts with markdown fence (common issue)
    if code_text.startswith('```'):
        # Extract everything after the first fence
        lines = code_text.split('\n')
        # Skip the first line (```css or ```)
        if len(lines) > 1:
            code_text = '\n'.join(lines[1:])
    
    # Try to find code blocks with language tags (```language ... ```)
    code_block_pattern = r'```(?:\w+)?\s*\n(.*?)```'
    matches = re.findall(code_block_pattern, code_text, re.DOTALL)
    if matches:
        # Take the largest match (most likely the actual code)
        code = max(matches, key=len).strip()
        logger.info("Extracted code from markdown fences")
        return code
    
    # Try to find code blocks without language tag (``` ... ```)
    simple_block_pattern = r'```\s*\n(.*?)```'
    simple_matches = re.findall(simple_block_pattern, code_text, re.DOTALL)
    if simple_matches:
        code = max(simple_matches, key=len).strip()
        logger.info("Extracted code from simple markdown fences")
        return code
    
    # Remove any trailing markdown fence
    if code_text.endswith('```'):
        code_text = code_text[:-3].rstrip()
    
    # If no markdown fences found, return as-is (but cleaned)
    return code_text.strip()


async def _call_code_generation_tool(
    code_gen_fn,
    filename: str,
    project_name: str,
    constraints: str,
    programming_language: str,
    related_files: list[str] | None = None,
    all_files: list[str] | None = None,
) -> str:
    """Helper function to call code_generation_tool with enhanced quality guidelines.
    
    Args:
        code_gen_fn: The code generation tool function
        filename: Name of the file to generate
        project_name: Name of the project
        constraints: Requirements and constraints from project manager
        programming_language: Programming language for the file
        related_files: List of related files for context (e.g., if generating CSS, related HTML files)
        all_files: List of all files in the project for context
    """
    # Determine file type from filename
    file_type = filename.split(".")[-1] if "." in filename else filename
    
    # Get relevant code examples based on filename and type
    code_examples = get_relevant_examples(filename, file_type)
    
    # Build enhanced query with quality guidelines
    enhanced_query = build_enhanced_code_generation_query(
        filename=filename,
        project_name=project_name,
        constraints=constraints,
        file_type=file_type,
        related_files=related_files,
        code_examples=code_examples if code_examples else None,
    )
    
    logger.info(f"Calling code_generation_tool for {filename} with language {programming_language}")
    logger.debug(f"Enhanced query length: {len(enhanced_query)} characters")
    
    # code_generation_tool expects a dict with 'query' and 'programming_language' keys
    tool_input = {
        "query": enhanced_query,
        "programming_language": programming_language
    }
    result = await code_gen_fn.ainvoke(tool_input)
    logger.info(f"Code generation completed for {filename}")
    return result


async def _call_save_file_code(
    save_file_fn,
    file_path: str,
    code_content: str,
) -> str:
    """Helper function to call save_file_code."""
    from nat.tool.save_file_code import SaveFileCodeInput
    
    logger.info(f"Calling save_file_code to save {file_path}")
    
    save_input = SaveFileCodeInput(
        file_path=file_path,
        code_content=code_content,
        execution_result=""
    )
    result = await save_file_fn.ainvoke(save_input)
    logger.info(f"File saved successfully: {file_path}")
    return result


def _validate_generated_site(project_name: str, website_type: str = "") -> None:
    """Ensure generated site includes required dynamic hooks based on website_type.
    
    Args:
        project_name: Name of the project
        website_type: Type of website (ecommerce_site, information_site, web_app)
                     If empty, defaults to ecommerce_site for backward compatibility
    """

    base_path = Path(f"output/{project_name}")
    errors: list[str] = []
    website_type = website_type.lower() if website_type else "ecommerce_site"

    def _load_text(rel_path: str) -> str:
        file_path = base_path / rel_path
        if not file_path.exists():
            # Only report missing files for ecommerce_site
            if website_type == "ecommerce_site":
                errors.append(f"Missing required file: {file_path}")
            return ""
        return file_path.read_text(encoding="utf-8")

    def _require_substring(source: str, needle: str, message: str) -> None:
        if source and needle not in source:
            errors.append(message)

    # Determine which HTML files to validate based on website_type
    if website_type == "ecommerce_site":
        html_files_to_check = ("index.html", "shop.html", "cart.html", "checkout.html", "about.html")
    else:
        # For information_site/web_app, only check files that exist
        html_files_to_check = ("index.html", "about.html")  # Base files that should exist

    for html_file in html_files_to_check:
        html_content = _load_text(html_file)
        if not html_content:
            continue

        # Enforce required shared header search (all website types)
        _require_substring(
            html_content,
            'id="search-input"',
            f"{html_file} must include the shared header search input id=\"search-input\".",
        )
        
        # Only enforce cart hooks for ecommerce_site
        if website_type == "ecommerce_site":
            _require_substring(
                html_content,
                'id="cart-count"',
                f"{html_file} must expose <span id=\"cart-count\"> for CartManager.",
            )
            _require_substring(
                html_content,
                'id="cart-subtotal"',
                f"{html_file} must expose <span id=\"cart-subtotal\"> for CartManager.",
            )

        # Enforce external CSS/JS linkage for all pages
        if '<link rel="stylesheet"' not in html_content or "styles.css" not in html_content:
            errors.append(
                f"{html_file} must link the shared stylesheet via "
                '<link rel="stylesheet" href="styles.css"> (no inline <style> blocks).'
            )
        if '<script' not in html_content or "script.js" not in html_content:
            errors.append(
                f"{html_file} should include the shared script bundle via "
                '<script src="script.js"></script> before </body>.'
            )

        # Forbid inline <style> blocks and style="" attributes on core pages
        if "<style" in html_content:
            errors.append(
                f"{html_file} must not contain inline <style> tags. Move all CSS into styles.css."
            )
        if ' style="' in html_content or " style='" in html_content:
            errors.append(
                f"{html_file} must not use inline style=\"...\" attributes for layout/styling. "
                "Use CSS classes defined in styles.css instead."
            )

        # Only validate products-container for ecommerce_site
        if website_type == "ecommerce_site" and html_file in ("index.html", "shop.html"):
            _require_substring(
                html_content,
                'id="products-container"',
                f"{html_file} must contain an empty container id=\"products-container\" for dynamic product rendering.",
            )

        # Only validate ecommerce links for ecommerce_site
        if website_type == "ecommerce_site":
            for required_link in ("shop.html", "cart.html", "checkout.html", "about.html"):
                if required_link not in html_content:
                    errors.append(f"{html_file} header nav must include a link to {required_link}.")

    # Only validate checkout for ecommerce_site
    if website_type == "ecommerce_site":
        checkout_content = _load_text("checkout.html")
        if checkout_content:
            _require_substring(
                checkout_content,
                'id="checkout-summary"',
                "checkout.html must include an order summary container with id=\"checkout-summary\".",
            )
            _require_substring(
                checkout_content,
                'id="checkout-form"',
                "checkout.html must include a checkout form with id=\"checkout-form\".",
            )
            _require_substring(
                checkout_content,
                'id="place-order-button"',
                "checkout.html must include a submission button with id=\"place-order-button\".",
            )

    about_content = _load_text("about.html")
    if about_content:
        if "mission" not in about_content.lower() and "story" not in about_content.lower():
            errors.append("about.html should include a mission or brand story section.")
        # Only require shop/cart CTAs for ecommerce_site
        if website_type == "ecommerce_site":
            if "shop.html" not in about_content and "cart.html" not in about_content:
                errors.append("about.html should include CTAs linking back to shop.html or cart.html.")

    # Only validate shop.html for ecommerce_site
    if website_type == "ecommerce_site":
        shop_html = (base_path / "shop.html")
        if shop_html.exists():
            shop_content = shop_html.read_text(encoding="utf-8")
            if shop_content:
                if 'id="filter-select"' not in shop_content and 'id="category-filter"' not in shop_content:
                    errors.append(
                        "shop.html must include a filter select (id=\"filter-select\" or id=\"category-filter\")."
                    )
                if 'id="sort-select"' not in shop_content and 'id="sort-by"' not in shop_content:
                    errors.append(
                        "shop.html must include a sort select (id=\"sort-select\" or id=\"sort-by\")."
                    )

    products_path = base_path / "products.json"
    if not products_path.exists():
        errors.append(f"Missing required file: {products_path}")
    else:
        try:
            products_data = json.loads(products_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"products.json is not valid JSON: {exc}")
            products_data = []

        if isinstance(products_data, dict) and "products" in products_data:
            product_list = products_data["products"]
        elif isinstance(products_data, list):
            product_list = products_data
        else:
            product_list = None
            errors.append("products.json must be an array or an object with a \"products\" list.")

        if isinstance(product_list, list):
            if not product_list:
                errors.append("products.json must include at least one product entry.")
            else:
                sample = product_list[0]
                for field in ("id", "name", "price", "category", "description", "image"):
                    if field not in sample:
                        errors.append(f"products.json entries must include \"{field}\".")

    if errors:
        joined = "\n - ".join(errors)
        raise ValueError(f"Dynamic storefront validation failed:\n - {joined}")


@register_function(config_type=MASWorkflowEngineerPhaseConfig)
async def mas_engineer_phase(config: MASWorkflowEngineerPhaseConfig, builder: Builder):
    """Register the MAS workflow engineer phase as a NAT function."""

    engineer_fn = builder.get_function(config.engineer)
    
    # Get tools
    try:
        file_reader_fn = builder.get_function("file_reader")
    except Exception as e:
        logger.warning(f"Could not get file_reader function: {e}. Will let agent handle file reading.")
        file_reader_fn = None
    
    try:
        code_gen_fn = builder.get_function("code_generation_tool")
    except Exception as e:
        logger.warning(f"Could not get code_generation_tool: {e}. Will use agent instead.")
        code_gen_fn = None
    
    try:
        save_file_fn = builder.get_function("save_file_code")
    except Exception as e:
        logger.warning(f"Could not get save_file_code: {e}. Will use agent instead.")
        save_file_fn = None

    async def _response_fn(user_request: str) -> str:
        logger.info("Starting MAS workflow for request: %s", user_request)

        # STEP 1: Read project manager output file
        pm_file_path = "output/doc/project_manager_output.txt"
        pm_content = None
        
        if file_reader_fn:
            try:
                logger.info(f"Step 1: Reading project manager output from {pm_file_path}")
                from nat.tool.file_reader import FileReaderInput
                file_reader_input = FileReaderInput(file_path=pm_file_path)
                file_reader_response = await file_reader_fn.ainvoke(file_reader_input)
                
                # STEP 2: Extract content from file_reader response
                logger.info("Step 2: Extracting content from file_reader response")
                pm_content = _extract_content_from_file_reader_response(file_reader_response)
                logger.info(f"Extracted project manager content (length: {len(pm_content)} chars)")
            except Exception as e:
                logger.warning(f"Error reading project manager file directly: {e}. Will let agent handle it.")
                pm_content = None
        else:
            logger.info("file_reader not available, will let agent handle file reading")

        if not pm_content:
            raise FileNotFoundError(
                "Project manager output could not be read. Ensure output/doc/project_manager_output.txt exists."
            )

        architect_handoff = None
        try:
            architect_handoff = load_handoff_json("output/doc/architect_handoff.json")
            logger.info("Loaded architect structured handoff")
        except Exception as exc:
            logger.warning("Could not load architect handoff JSON: %s", exc)

        try:
            project_manager_handoff = parse_project_manager_output_to_handoff(pm_content, architect_handoff)
            save_handoff_json(project_manager_handoff, "output/doc/project_manager_handoff.json")
            logger.info("Parsed and saved project manager structured handoff JSON")
        except Exception as exc:
            logger.error("Failed to parse project manager output into structured handoff: %s", exc)
            raise ValueError(
                "Unable to parse project manager output into structured handoff. "
                "Please ensure the PM document follows the required format."
            ) from exc

        structured_handoff_text = format_handoff_for_agent(project_manager_handoff)

        # STEP 3: Use helper functions if available, otherwise fallback to agent
        if code_gen_fn and save_file_fn:
            try:
                from nat_mas_agents.config import normalize_project_name
                project_name = normalize_project_name(project_manager_handoff.project_name)
                if not project_name:
                    raise ValueError("Structured handoff missing project_name.")

                steps = sorted(project_manager_handoff.tasks, key=lambda t: t.get("step", 0))
                if not steps:
                    raise ValueError("Structured handoff missing tasks section.")

                logger.info("Found %d structured steps for project: %s", len(steps), project_name)

                # Get list of all filenames for context
                all_filenames = [step.get("filename", "").strip() for step in steps if step.get("filename")]
                
                # Get website_type for enforcement
                website_type = project_manager_handoff.website_type.lower() if project_manager_handoff.website_type else ""
                if not website_type:
                    website_type = _extract_website_type(pm_content or "") or ""
                    website_type = website_type.lower() if website_type else ""
                
                # Process each step
                results = []
                for i, step in enumerate(steps, 1):
                    filename = step.get("filename", "").strip()
                    constraints = step.get("constraints", "").strip()
                    if not filename or not constraints:
                        raise ValueError(f"Structured handoff step {i} missing filename or constraints.")

                    # Add information_site checklist to constraints if applicable
                    if website_type == "information_site":
                        info_site_checklist = _get_information_site_checklist(filename)
                        if info_site_checklist:
                            constraints = f"{constraints}\n\n{info_site_checklist}"

                    programming_language = _map_filename_to_programming_language(filename)
                    
                    # Determine related files based on file type
                    related_files = []
                    file_type = filename.split(".")[-1].lower() if "." in filename else ""
                    
                    if file_type == "css":
                        # For CSS, relate to HTML files
                        related_files = [f for f in all_filenames if f.endswith((".html", ".htm"))]
                    elif file_type in ("js", "javascript"):
                        # For JS, relate to HTML files
                        related_files = [f for f in all_filenames if f.endswith((".html", ".htm"))]
                    elif file_type in ("html", "htm"):
                        # For HTML, relate to CSS and JS files
                        related_files = [f for f in all_filenames if f.endswith((".css", ".js"))]
                    
                    logger.info(f"Processing step {i}/{len(steps)}: {filename}")
                    if related_files:
                        logger.debug(f"Related files for {filename}: {', '.join(related_files)}")
                    
                    # Generate code with enhanced query
                    generated_code = await _call_code_generation_tool(
                        code_gen_fn,
                        filename,
                        project_name,
                        constraints,
                        programming_language,
                        related_files=related_files if related_files else None,
                        all_files=all_filenames,
                    )
                    
                    # Extract code from markdown if needed
                    extracted_code = _extract_code_from_markdown(generated_code)
                    
                    # Validate code before saving
                    validation_errors = _validate_code_before_save(filename, extracted_code)
                    if validation_errors:
                        logger.warning(f"Validation warnings for {filename}: {validation_errors}")
                        # Log but continue - let tester catch these issues
                    
                    # Save file
                    file_path = f"output/{project_name}/{filename}"
                    save_result = await _call_save_file_code(
                        save_file_fn,
                        file_path,
                        extracted_code
                    )
                    
                    # If this is products.json, verify it matches requirements
                    if filename == "products.json":
                        try:
                            _verify_products_json_requirements(
                                Path(file_path),
                                project_manager_handoff,
                                pm_content
                            )
                        except ValueError as e:
                            logger.warning(f"Products.json requirements check failed: {e}")
                            # Log warning but continue - tester will catch this
                    
                    results.append(f"Step {i}: {filename} - Generated and saved to {file_path}")
                    logger.info(f"Completed step {i}/{len(steps)}: {filename}")
                
                # Validation disabled - skip post-generation validation
                # (Previously validated dynamic storefront expectations here)
                logger.info("Skipping post-generation validation (disabled)")

                # Return summary
                summary = f"All files have been successfully generated and saved to output/{project_name}/.\n\n"
                summary += "\n".join(results)
                logger.info("MAS workflow completed using helper functions")
                return summary
                
            except Exception as e:
                logger.error(f"Error using helper functions: {e}. Falling back to agent.")
                # Fall through to agent-based approach
        
        # Fallback to agent-based approach with structured handoff context
        logger.info("Invoking engineer agent with structured handoff data")
        
        # Use website_type from structured handoff (more reliable than parsing pm_content)
        website_type = project_manager_handoff.website_type.lower() if project_manager_handoff.website_type else ""
        if not website_type:
            # Fallback to extracting from pm_content if not in handoff
            website_type = _extract_website_type(pm_content or "") or ""
            website_type = website_type.lower() if website_type else ""
        
        shared_assets_reminder = ""
        if not website_type or website_type == "ecommerce_site":
            # For ecommerce_site projects, attach strong storefront reminder
            shared_assets_reminder = (
                "\n\nCRITICAL REMINDER (ECOMMERCE ONLY): products.json is ALWAYS in SHARED_ASSETS. You MUST:\n"
                "- HTML: Use the shared header/footer with #search-input, #cart-count, and #cart-subtotal on EVERY page.\n"
                "- HTML: Create an empty product container id=\"products-container\" on listing pages (NO hardcoded product <article> markup).\n"
                "- HTML: Header nav must include clickable links to shop.html, cart.html, checkout.html, and about.html on every page.\n"
                "- HTML: Shop page must expose filter select (id=\"filter-select\"/\"category-filter\") and sort select (id=\"sort-select\"/\"sort-by\").\n"
                "- HTML: Generate checkout.html with order summary containers (#checkout-summary, #checkout-subtotal, #checkout-total), a checkout form (#checkout-form), and a primary CTA id=\"place-order-button\" that aligns with CartManager/localStorage data.\n"
                "- HTML: Generate about.html that tells the brand story (mission, sustainability, team/contact) and includes CTAs back to shop/cart while reusing the shared header/footer.\n"
                "- JavaScript: Load products from products.json via fetch('products.json') on DOMContentLoaded and render cards dynamically.\n"
                "- JavaScript: Ensure add-to-cart buttons use class \"add-to-cart-btn\" so CartManager updates shared counters.\n"
                "- Data: Populate products.json with real products (id, name, price, category, description, image) referenced by the PM brief.\n"
                "- Absolutely NO hardcoded product lists or cart line items in HTML—everything reflects products.json/localStorage state.\n\n"
            )
        elif website_type == "information_site":
            # For information_site, provide guidance specific to content sites with MANDATORY checklist
            shared_assets_reminder = (
                "\n\n"
                "=" * 80 + "\n"
                "CRITICAL REMINDER (INFORMATION SITE) - MANDATORY CHECKLIST\n"
                "=" * 80 + "\n"
                "BEFORE GENERATING ANY CODE, YOU MUST VERIFY EACH ITEM BELOW:\n\n"
                "□ HEADER NAVIGATION:\n"
                "  - MUST NOT include shop.html, cart.html, or checkout.html links\n"
                "  - MUST ONLY include pages from FILES list (e.g., index.html, matches.html, results.html, about.html)\n"
                "  - Example CORRECT nav: <a href=\"index.html\">Home</a> <a href=\"matches.html\">Matches</a> <a href=\"results.html\">Results</a> <a href=\"about.html\">About</a>\n"
                "  - Example WRONG nav: <a href=\"shop.html\">Shop</a> <a href=\"cart.html\">Cart</a> (DO NOT USE)\n\n"
                "□ HEADER CART SECTION:\n"
                "  - MUST NOT include <div class=\"header__cart\"> or any cart-related elements\n"
                "  - MUST NOT include id=\"cart-count\", id=\"cart-subtotal\", or cart-icon\n"
                "  - Header should ONLY have: logo, navigation, search input (#search-input)\n\n"
                "□ JAVASCRIPT CLASSES:\n"
                "  - MUST NOT use ProductManager or CartManager classes\n"
                "  - MUST use domain-appropriate classes (e.g., MatchManager, ResultsManager, MatchListManager)\n"
                "  - Example CORRECT: class MatchManager { ... } class ResultsManager { ... }\n"
                "  - Example WRONG: class ProductManager { ... } class CartManager { ... } (DO NOT USE)\n\n"
                "□ JAVASCRIPT DATA LOADING:\n"
                "  - MUST NOT use fetch('products.json')\n"
                "  - MUST use fetch paths from SHARED_ASSETS (e.g., fetch('matches.json'), fetch('results.json'))\n"
                "  - Example CORRECT: const response = await fetch('matches.json');\n"
                "  - Example WRONG: const response = await fetch('products.json'); (DO NOT USE)\n\n"
                "□ HTML CONTAINER IDs:\n"
                "  - MUST NOT use id=\"products-container\"\n"
                "  - MUST use domain-appropriate IDs (e.g., id=\"matches-container\", id=\"results-list\", id=\"matches-list\")\n"
                "  - Container IDs MUST match what JavaScript uses in getElementById()\n"
                "  - Example CORRECT: <section id=\"matches-container\"> or <div id=\"results-list\">\n"
                "  - Example WRONG: <section id=\"products-container\"> (DO NOT USE)\n\n"
                "□ JSON DATA STRUCTURE:\n"
                "  - MUST match what JavaScript expects (e.g., { \"matches\": [...] } for matches.json, { \"results\": [...] } for results.json)\n"
                "  - MUST NOT use { \"products\": [...] } structure unless explicitly required\n\n"
                "□ PATH CONSISTENCY:\n"
                "  - MUST use consistent paths for shared assets across all HTML files\n"
                "  - Either all files use 'styles.css' OR all use 'SHARED_ASSETS/styles.css' (not mixed)\n\n"
                "VERIFICATION PROCESS:\n"
                "1. Before generating each HTML file, check the checklist above\n"
                "2. Before generating script.js, verify it uses MatchManager/ResultsManager (NOT ProductManager/CartManager)\n"
                "3. Before generating script.js, verify it fetches matches.json/results.json (NOT products.json)\n"
                "4. If ANY checklist item is violated, you MUST regenerate the code to fix it\n"
                "5. DO NOT proceed with saving files until ALL checklist items are satisfied\n\n"
                "=" * 80 + "\n\n"
            )
        
        # Generate engineer brief with website_type for better customization
        engineer_brief = _get_engineer_brief(website_type)
        
        engineer_message = (
            f"{engineer_brief.strip()}\n\n"
            f"PREVIOUS_STATUS: {DEFAULT_AGENT_STATUSES['project_manager']}\n\n"
            f"{structured_handoff_text}"
            f"{shared_assets_reminder}"
            "IMPORTANT: Use ONLY the structured handoff data above to extract PROJECT_NAME, FILES, ORDER, and STEPS. "
            "Reference SOP templates for default component behaviors and keep all IDs/requirements identical to the structured data. "
            "If website_type is information_site, you MUST follow the MANDATORY CHECKLIST above - verify each item before generating code."
        )
        
        engineer_output = await _invoke_agent("engineer", engineer_fn.ainvoke, engineer_message)

        logger.info("MAS workflow completed; returning engineer output")
        return engineer_output

    yield FunctionInfo.create(single_fn=_response_fn)
