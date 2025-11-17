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

from .prompt_sections import SOP_REFERENCE_TEXT, render_prompt_sections
from .sop_templates import get_sop_summary
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


def _get_engineer_brief() -> str:
    """Get engineer brief with SOP templates included."""
    sop_summary = get_sop_summary()
    structured_rules = render_prompt_sections()
    
    return f"""
=== SOFTWARE ENGINEER BRIEF ===
You are Phase 4 Software Engineer. You MUST follow strict ReAct format.

NOTE: This prompt is used when automatic code generation is not available. Follow the instructions below to generate and save all files.

{sop_summary}
{structured_rules}

CRITICAL: When generating code, you MUST follow the SOP templates summarized above for default component behaviors.
DO NOT invent or guess implementations - use the standardized specifications exactly as specified. Reference the SOP module when you need the full text.

Your task: Generate and save all files listed in STEPS from the structured handoff data below.

For each STEP (in order from EXTRACTED_PROJECT_MANAGER_CONTENT):

Thought: plan generation for [filename] using provided constraints
Action: code_generation_tool
Action Input: {{"query": "Generate [filename] for [PROJECT_NAME]. Requirements: [FULL STEP CONSTRAINTS].", "programming_language": "[LANGUAGE]"}}
Observation: [The tool will return code, possibly wrapped in markdown code fences like ```html or ```javascript. The actual code is between the fences.]
Thought: I received the generated code. Now I need to extract the actual code content (removing markdown fences if present) and save it to a file.
Action: save_file_code
Action Input: {{"file_path": "output/[PROJECT_NAME]/[filename]", "code_content": "[PASTE THE ACTUAL CODE HERE - extract everything between markdown fences if they exist, otherwise use the code as-is]"}}
Observation: [Wait for confirmation that file was saved]

After all files saved:
Thought: confirm completion
Final Answer: All files have been successfully generated and saved to output/[PROJECT_NAME]/.

Hard requirements:
- Use PROJECT_NAME, FILES, ORDER, STEPS exactly as defined in the structured handoff data.
- Use STEP[n].constraints directly in code generation - it already contains all FILE_REQUIREMENTS for that file.
- Extract PROJECT_NAME from structured handoff and use this EXACT value for all file paths - do NOT change it.
- Always maintain naming consistency across every file created. If FILE_REQUIREMENTS specify a filename, use it exactly (case-sensitive) in both file content and save_file_code.
- Honor REQUIREMENTS, SHARED_COMPONENTS, SHARED_ASSETS, and FILE_REQUIREMENTS from structured handoff: ensure each file implements its requirements, reuses shared components/assets, and meets the success criteria.
- CRITICAL: For HTML files - Header and Footer MUST be on EVERY page:
  * EVERY HTML page MUST have IDENTICAL header structure with: logo (clickable, links to homepage), navigation menu (links to ALL pages), search input (#search-input on input element itself), cart section (#cart-count, #cart-subtotal)
  * EVERY HTML page MUST have IDENTICAL footer structure with: company info, navigation links, contact info, copyright
  * Header and Footer must be professional, modern, and visually appealing
  * Header must use flexbox or grid for responsive layout
  * Footer must use flexbox or grid for responsive layout (3 columns desktop, stacked mobile)
- CRITICAL: For HTML files with products:
  * ALWAYS check SHARED_ASSETS first. If "products.json" is listed in SHARED_ASSETS: HTML MUST have an empty container with a clear, consistent ID. 
  * STANDARD CONTAINER ID: Use id="products-container" (with 's', plural) as the standard. This is the most common and consistent ID to use.
  * Example: <section id="products-container" class="product-container"></section> or <div id="products-container"></div>
  * The ID MUST be used consistently in JavaScript. DO NOT hardcode any products in HTML - leave the container completely empty.
  * If "products.json" is NOT in SHARED_ASSETS: Products MUST be hardcoded directly in the HTML markup with data attributes (data-category, data-price) for filtering/sorting. Use actual product names, prices, categories, and descriptions from PRODUCTS section. The container should still have id="products-container" for JavaScript to reference.
  * CRITICAL: The container ID in HTML MUST match exactly what JavaScript uses. Use id="products-container" (with 's') consistently in both HTML and JavaScript.
  * For product listing pages (shop.html, index.html): MUST include filter and sort controls:
    - Category filter: <select id="filter-select"> or <select id="category-filter"> with options for all categories
    - Sort dropdown: <select id="sort-select"> or <select id="sort-by"> with sort options (Price: Low to High, Price: High to Low, Name: A to Z, etc.)
    - These controls should be placed above or near the product container
- CRITICAL: For products.json (if in SHARED_ASSETS):
  * Engineer MUST generate products.json file with ALL products from PRODUCTS section
  * Format: Array of objects, each with id (number), name (string), price (number), category (string), description (string), image (string URL)
  * Example: [{{"id": 1, "name": "Product Name", "price": 29.99, "category": "Category", "description": "Description", "image": "https://via.placeholder.com/300x300?text=Product"}}]
  * Save to: output/[PROJECT_NAME]/products.json
  * CRITICAL: This file MUST be generated BEFORE or ALONG WITH HTML files so JavaScript can load it
- CRITICAL: For script.js:
  * CRITICAL: Container ID consistency - Use id="products-container" (with 's', plural) as the standard. Use document.getElementById('products-container') or document.querySelector('#products-container') consistently.
  * FIRST: Check if "products.json" exists in SHARED_ASSETS. If it does, you MUST load products from products.json using fetch('products.json') on page initialization (DOMContentLoaded). DO NOT hardcode products array in JavaScript.
  * If "products.json" is in SHARED_ASSETS: 
    - Use async/await or .then() to load products.json
    - Parse the JSON response to get the products array:
      * If response is a direct array (starts with square bracket), use it directly as the products array
      * If response is an object with a "products" property, extract the products array from that property
      * You must handle both formats: check if the response is an array, if yes use it directly, if no check for a "products" property and use that, otherwise use an empty array
    - CRITICAL: If fetch fails (404, network error), you MUST have a fallback: either use hardcoded products array or show error message. Do NOT leave page empty.
    - Generate product cards dynamically using the loaded products
    - Insert generated cards into the product container using getElementById with 'products-container' or querySelector with '#products-container'
    - Use the loaded products for all cart, filter, sort, and search operations
    - Add data attributes (data-category, data-price) when generating HTML elements for filtering/sorting
  * If "products.json" is NOT in SHARED_ASSETS: Use hardcoded products array with actual product data from PRODUCTS section in constraints.
  * MUST follow CART, FILTER, SORT, SEARCH SOPs exactly. Implement all standard behaviors as specified in the SOPs.
  * CRITICAL: You MUST attach event listeners, but ONLY if elements exist:
    - ALWAYS check if element exists before attaching listener: First get the element using getElementById or querySelector, then check if it exists (not null), and only then attach the event listener
    - Filter dropdown: Check for filter-select or category-filter element, if it exists then listen to change events
    - Sort dropdown: Check for sort-select or sort-by element, if it exists then listen to change events
    - Search input: Check for search-input element, if it exists then listen to input or keyup events for live search (debounced, 300ms)
    - Add to cart buttons: Listen to click events on all "Add to Cart" buttons (attach after rendering products)
  * Cart must use localStorage with key "cart" and update header cart display (#cart-count, #cart-subtotal) automatically on ALL pages.
  * updateCartDisplay() function: Must be called after every cart operation (add, remove, update quantity) AND on page load
  * For multi-page projects: JavaScript must detect which page it's on (check window.location.pathname or document.querySelector for page-specific elements) and initialize appropriate functionality:
    - Product listing pages: Load products from JSON (if available), render product grid, handle filter/sort/search
    - Cart page: Load cart from localStorage, render cart items, handle remove/update quantity, calculate totals
    - All pages: Update header cart count and subtotal from localStorage on page load
  * All event listeners MUST check if elements exist before attaching: First get the element, check if it exists (not null), and only then attach the event listener. This allows the code to work across different pages where some elements may not exist.
- CRITICAL: For header component - follow HEADER SOP exactly:
  * Logo (left, clickable, links to homepage/index.html)
  * Navigation menu (center, links to ALL pages listed in FILES)
  * Search bar (#search-input on input element itself, not a wrapper div)
  * Cart section (#cart-count, #cart-subtotal) on right
  * Modern, professional design with proper spacing and alignment
  * Responsive: Stacks vertically on mobile, horizontal on desktop
  * Header background: Light color (#f8f9fa or similar), with border-bottom
- CRITICAL: For footer component - follow FOOTER SOP exactly:
  * Company info, navigation links, contact info, copyright
  * Dark background (#343a40 or similar), light text (#ffffff)
  * Responsive: 3 columns on desktop, stacked on mobile
  * Clear visual separation from main content (margin-top: 40px)
  * Must appear on EVERY HTML page with IDENTICAL structure
- CRITICAL: For styles.css - create modern, beautiful, professional styling:
  * Use modern color schemes (avoid harsh colors like bright pink #ff69b4, use professional palettes)
  * Product cards: Modern card design with subtle shadows (box-shadow: 0 2px 8px rgba(0,0,0,0.1)), rounded corners (border-radius: 8px), smooth hover effects (transform: translateY(-4px), transition: all 0.3s ease)
  * Responsive product grid: CSS Grid or Flexbox, 3-4 columns on desktop, 2 columns on tablet, 1 column on mobile (use media queries)
  * Typography: Use modern font stacks (e.g., -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif), proper font sizes and line heights
  * Buttons: Modern button styles with hover states, proper padding, rounded corners, smooth transitions
  * Header: Clean, professional design with proper spacing, modern layout (flexbox or grid), responsive
  * Footer: Clean, modern design with dark background, light text, responsive multi-column layout
  * Overall: Professional, modern, e-commerce quality design - NOT basic or ugly styling
  * Include smooth transitions and hover effects throughout
  * Use proper spacing, padding, and margins for visual hierarchy
- CRITICAL: Reference SHARED_ASSETS from structured handoff - use exact filenames (e.g., "styles.css", "script.js") when linking in HTML.
- Action Inputs MUST be valid JSON with double-quoted keys/values, no trailing commas, no Markdown fences.
- Replace placeholders ([filename], [PROJECT_NAME], [FULL STEP CONSTRAINTS], [LANGUAGE], [EXTRACTED CODE]) with real values.
- Action Input must be inline JSON with proper double quotes, no ```json``` fences.
- CRITICAL: Do NOT use markdown formatting (like ** or __) around Action names. Write "Action: code_generation_tool" NOT "**Action:** code_generation_tool" or "Action: **code_generation_tool**".
- CRITICAL: [LANGUAGE] must be mapped from filename extension to correct format:
  * .html or html -> "HTML"
  * .css or css -> "CSS"
  * .js or js or javascript -> "JavaScript"
  * .ts or ts or typescript -> "TypeScript"
  * .py or py or python -> "Python"
  * .java or java -> "Java"
  * .cpp, .cc, .cxx or cpp, c++ -> "C++"
  * .c or c -> "C"
  * .cs or cs or c# -> "C#"
  * .go or go -> "Go"
  * .rs or rust -> "Rust"
  * .php or php -> "PHP"
  * .rb or ruby -> "Ruby"
  * .sql or sql -> "SQL"
  * .json or json -> "JSON"
  * .yaml, .yml or yaml, yml -> "YAML"
  * .xml or xml -> "XML"
  * Other: capitalize properly (e.g., "Swift", "Kotlin", etc.)
- For CSS query include phrase "Generate CSS that styles the HTML elements from the previous file".
- For JS query include phrase "Generate JavaScript that manipulates HTML elements and uses CSS classes from the previous files".
- Save each generated file immediately after code_generation_tool; never batch saves.
- CRITICAL: HTML files must NOT contain any CSS code inside. This means:
  * NO <style> tags in HTML files
  * NO inline styles (style="...") on HTML elements
  * All CSS must be in separate CSS files only
- HTML files must link their stylesheet using the exact filename listed in FILES (default to <link rel="stylesheet" href="style.css"> when FILES contains style.css). Do NOT inline CSS or invent new paths unless FILE_REQUIREMENTS explicitly specify otherwise.
- HTML files must include their JavaScript bundle using the exact filename listed in FILES (default to <script src="script.js"></script> placed right before </body>). Do NOT move the script tag after </html>.
- Footer: Do NOT use position: fixed unless page content has sufficient bottom padding. Prefer static/normal flow.
- Consistency: Ensure all DOM elements referenced in JS exist in corresponding HTML pages. No broken selectors.
- Separation of concerns: All styling in CSS files; no inline styles, no <style> tags in HTML. All behavior in JS files; minimal inline JS.
- CRITICAL for multi-page projects:
  * EVERY HTML page MUST have IDENTICAL header structure with EXACT same IDs: #search-input (on the input element itself, not a div), #cart-count, #cart-subtotal
  * Header MUST include: logo (clickable, links to homepage), navigation menu (links to ALL pages), search input, cart section
  * EVERY HTML page MUST include navigation menu with links to ALL other HTML pages listed in FILES (e.g., <nav><a href="index.html">Home</a><a href="shop.html">Shop</a><a href="cart.html">Cart</a></nav>)
  * EVERY HTML page MUST include the same footer structure with company info, navigation links, contact info, copyright
  * EVERY HTML page MUST link the same CSS and JS files from SHARED_ASSETS
  * JavaScript must work across ALL pages - check which page you're on and initialize appropriate functionality
  * Product container IDs must be consistent: use id="products-container" (with 's', plural) consistently across all pages that display products
  * Cart page must have #cart-items or #cart-container container for cart items
  * Header and Footer must look professional and modern on ALL pages
- For multi-page projects: every HTML page must include the shared CSS and JS assets using the exact filenames from SHARED_ASSETS (e.g., "styles.css", "script.js") unless FILE_REQUIREMENTS explicitly provide different paths.
- CRITICAL: After receiving Observation from code_generation_tool, you MUST write a Thought before the next Action. Never skip the Thought step.
- The Observation from code_generation_tool is a STRING. Extract the code from it:
  * If Observation has markdown code block (```lang ... ```), extract ONLY the code inside (remove ``` and language tag)
  * If Observation is plain code text, use it directly
  * Pass the extracted code string directly to code_content field - NOT as JSON object, NOT serialized
- Always preserve the complete code with all whitespace, newlines, and indentation.
- Never replace any portion of the generated code with "..." or summaries; ensure the exact extracted code is saved.
- If you cannot extract the code properly (e.g., Observation is malformed), regenerate the code instead of saving a truncated version.
- After each save, verify the file using file_reader to ensure there are no ellipses or truncation. If verification shows ellipses ("...") or missing sections, re-run code_generation_tool for that file and repeat the save/verify cycle until the saved file contains the full code.
- Always follow the format: Thought -> Action -> Action Input -> Observation -> Thought -> Action -> ...
- Before moving to the next file or completing the workflow, make sure you have called code_generation_tool at least once for the current file in this session.
- After saving ALL files in ORDER (and verifying each), provide Final Answer IMMEDIATELY and STOP.
- Do NOT generate extra files, do NOT continue after Final Answer.
- Your Final Answer must explicitly confirm that every file was generated in this session via code_generation_tool and saved after verification. If you cannot truthfully confirm this, you MUST call code_generation_tool again to fix it. Never claim success otherwise.
- If any step cannot be completed, respond with "ERROR: Engineer could not complete the required actions." instead of success message.

{SOP_REFERENCE_TEXT}
"""

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


def _parse_project_name(content: str) -> str:
    """Parse PROJECT_NAME from project manager content."""
    lines = content.split('\n')
    for line in lines:
        stripped = line.strip()
        # Handle both "PROJECT_NAME:" and "<PROJECT_NAME:" formats
        if stripped.startswith('PROJECT_NAME:') or stripped.startswith('<PROJECT_NAME:'):
            # Remove < if present, then split on PROJECT_NAME:
            cleaned = stripped.lstrip('<')
            if 'PROJECT_NAME:' in cleaned:
                project_name = cleaned.split('PROJECT_NAME:', 1)[1].strip()
                logger.info(f"Parsed PROJECT_NAME: {project_name}")
                return project_name
    raise ValueError("PROJECT_NAME not found in project manager content")


def _parse_steps(content: str) -> list[dict]:
    """Parse STEPS from project manager content. Returns list of dicts with 'filename' and 'constraints'."""
    steps = []
    in_steps_section = False
    
    lines = content.split('\n')
    for line in lines:
        stripped = line.strip()
        
        # Check if we're entering STEPS section
        if stripped.startswith('STEPS:'):
            in_steps_section = True
            continue
        
        # Check if we're leaving STEPS section (next section starts)
        if in_steps_section and stripped and not stripped.startswith('Step') and not stripped.startswith('-') and ':' in stripped and not stripped.startswith('Step'):
            break
        
        if in_steps_section and stripped.startswith('Step'):
            # Match "Step N: filename Constraints: ..." pattern (all on one line)
            # Pattern: Step N: <filename> Constraints: <constraints>
            step_match = re.match(r'Step\s+(\d+):\s*(.+?)\s+Constraints:\s*(.+)$', stripped, re.IGNORECASE)
            if step_match:
                step_num = step_match.group(1)
                filename = step_match.group(2).strip()
                constraints = step_match.group(3).strip()
                
                steps.append({
                    'filename': filename,
                    'constraints': constraints
                })
                logger.debug(f"Parsed step {step_num}: filename={filename}, constraints length={len(constraints)}")
    
    logger.info(f"Parsed {len(steps)} steps from project manager content")
    return steps


def _extract_code_from_markdown(code_text: str) -> str:
    """Extract code from markdown code fences if present."""
    # Try to find code blocks with language tags
    code_block_pattern = r'```(?:\w+)?\s*\n(.*?)```'
    matches = re.findall(code_block_pattern, code_text, re.DOTALL)
    if matches:
        code = matches[0].strip()
        logger.info("Extracted code from markdown fences")
        return code
    
    # If no markdown fences, return as-is
    return code_text.strip()


async def _call_code_generation_tool(
    code_gen_fn,
    filename: str,
    project_name: str,
    constraints: str,
    programming_language: str,
) -> str:
    """Helper function to call code_generation_tool."""
    query = f"Generate {filename} for {project_name}. Requirements: {constraints}."
    logger.info(f"Calling code_generation_tool for {filename} with language {programming_language}")
    
    # code_generation_tool expects a dict with 'query' and 'programming_language' keys
    tool_input = {
        "query": query,
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

        # STEP 3: Use helper functions if available, otherwise fallback to agent
        if pm_content and code_gen_fn and save_file_fn:
            try:
                # Parse project manager content
                project_name = _parse_project_name(pm_content)
                steps = _parse_steps(pm_content)
                
                logger.info(f"Found {len(steps)} steps for project: {project_name}")
                
                # Process each step
                results = []
                for i, step in enumerate(steps, 1):
                    filename = step['filename']
                    constraints = step['constraints']
                    programming_language = _map_filename_to_programming_language(filename)
                    
                    logger.info(f"Processing step {i}/{len(steps)}: {filename}")
                    
                    # Generate code
                    generated_code = await _call_code_generation_tool(
                        code_gen_fn,
                        filename,
                        project_name,
                        constraints,
                        programming_language
                    )
                    
                    # Extract code from markdown if needed
                    extracted_code = _extract_code_from_markdown(generated_code)
                    
                    # Save file
                    file_path = f"output/{project_name}/{filename}"
                    save_result = await _call_save_file_code(
                        save_file_fn,
                        file_path,
                        extracted_code
                    )
                    
                    results.append(f"Step {i}: {filename} - Generated and saved to {file_path}")
                    logger.info(f"Completed step {i}/{len(steps)}: {filename}")
                
                # Return summary
                summary = f"All files have been successfully generated and saved to output/{project_name}/.\n\n"
                summary += "\n".join(results)
                logger.info("MAS workflow completed using helper functions")
                return summary
                
            except Exception as e:
                logger.error(f"Error using helper functions: {e}. Falling back to agent.")
                # Fall through to agent-based approach
        
        # Fallback to agent-based approach
        logger.info("Step 3: Invoking engineer agent")
        
        # Try to load structured handoffs
        pm_handoff = None
        architect_handoff = None
        project_manager_handoff = None
        
        try:
            pm_handoff = load_handoff_json("output/doc/pm_handoff.json")
            logger.info("Loaded PM structured handoff")
        except Exception as e:
            logger.warning(f"Could not load PM handoff: {e}")
        
        try:
            architect_handoff = load_handoff_json("output/doc/architect_handoff.json")
            logger.info("Loaded architect structured handoff")
        except Exception as e:
            logger.warning(f"Could not load architect handoff: {e}")
        
        if pm_content:
            try:
                project_manager_handoff = parse_project_manager_output_to_handoff(pm_content, architect_handoff)
                structured_handoff_text = format_handoff_for_agent(project_manager_handoff)
                logger.info("Created structured handoff from project manager output")
                
                # Save structured handoff JSON
                save_handoff_json(project_manager_handoff, "output/doc/project_manager_handoff.json")
            except Exception as e:
                logger.warning(f"Error creating structured handoff: {e}. Using text-based handoff.")
                structured_handoff_text = f"EXTRACTED_PROJECT_MANAGER_CONTENT:\n{pm_content}\n\n"
        else:
            structured_handoff_text = ""
        
        if pm_content:
            # Include structured handoff in the brief
            # Add explicit reminder about checking SHARED_ASSETS for products.json
            shared_assets_reminder = ""
            if project_manager_handoff and project_manager_handoff.shared_assets:
                has_products_json = any(asset.get('name') == 'products.json' for asset in project_manager_handoff.shared_assets)
                if has_products_json:
                    shared_assets_reminder = "\n\nCRITICAL REMINDER: products.json is listed in SHARED_ASSETS above. You MUST:\n- HTML: Create empty product container (NO hardcoded products)\n- JavaScript: Load products from products.json using fetch('products.json') on page load\n- Do NOT hardcode products array in JavaScript\n⚠️⚠️⚠️\n\n"
            
            engineer_message = (
                f"{ENGINEER_BRIEF.strip()}\n\n"
                f"PREVIOUS_STATUS: {DEFAULT_AGENT_STATUSES['project_manager']}\n\n"
                f"{structured_handoff_text}"
                f"{shared_assets_reminder}"
                "IMPORTANT: Use the structured handoff data above to extract PROJECT_NAME, FILES, ORDER, and STEPS. "
                "Reference SOP templates for default component behaviors. "
                "Be explicit about which shared assets/components each file uses."
            )
        else:
            # Fallback to original behavior
            engineer_message = (
                f"{ENGINEER_BRIEF.strip()}\n\nPREVIOUS_STATUS: {DEFAULT_AGENT_STATUSES['project_manager']}"
                "\nAlways read output/doc/project_manager_output.txt first."
            )
        
        engineer_output = await _invoke_agent("engineer", engineer_fn.ainvoke, engineer_message)

        logger.info("MAS workflow completed; returning engineer output")
        return engineer_output

    yield FunctionInfo.create(single_fn=_response_fn)
