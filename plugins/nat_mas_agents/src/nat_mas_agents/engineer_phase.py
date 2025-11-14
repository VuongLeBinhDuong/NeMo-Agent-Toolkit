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


ENGINEER_BRIEF = """
=== SOFTWARE ENGINEER BRIEF ===
You are Phase 4 Software Engineer. You MUST follow strict ReAct format.

NOTE: This prompt is used when automatic code generation is not available. Follow the instructions below to generate and save all files.

Your task: Generate and save all files listed in STEPS from EXTRACTED_PROJECT_MANAGER_CONTENT.

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
- Use PROJECT_NAME, FILES, ORDER, STEPS exactly as defined in EXTRACTED_PROJECT_MANAGER_CONTENT.
- Use STEP[n].constraints directly in code generation - it already contains all FILE_REQUIREMENTS for that file.
- Extract PROJECT_NAME from EXTRACTED_PROJECT_MANAGER_CONTENT and use this EXACT value for all file paths - do NOT change it.
- Always maintain naming consistency across every file created. If FILE_REQUIREMENTS specify a filename, use it exactly (case-sensitive) in both file content and save_file_code.
- Honor PAGE_REQUIREMENTS, SUCCESS_CRITERIA, SHARED_COMPONENTS, SHARED_ASSETS, and FILE_REQUIREMENTS sections: ensure each file implements its page-level requirements, reuses shared components/assets, and meets the success criteria.
- CRITICAL: For HTML files with products, products MUST be hardcoded directly in the HTML markup (not loaded from JSON or dynamically). Use the actual product names, prices, categories, and descriptions from the PRODUCTS section in constraints.
- CRITICAL: For header component in all HTML files, it MUST include: (1) logo/brand name, (2) navigation menu with links to all pages, (3) search bar input field (e.g., <input type="text" id="search-input" placeholder="Search...">), (4) cart section showing item count (e.g., <span id="cart-count">0</span> items) and subtotal (e.g., <span id="cart-subtotal">$0.00</span>).
- CRITICAL: For script.js, it MUST implement: (1) category filtering functionality, (2) sorting by price/name options, (3) live search that filters products as user types, (4) localStorage operations for cart (getItem, setItem, removeItem), (5) add to cart button event handlers, (6) quantity increase/decrease controls, (7) total price calculations, (8) cart display updates (item count and subtotal in header), (9) cart page functionality (load from localStorage, display items, update quantities, calculate totals).
- CRITICAL: For styles.css, it MUST include responsive product grid that displays 3 columns on desktop and 1 column on mobile (use CSS Grid or Flexbox with media queries).
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
- For multi-page projects: every HTML page must include the shared CSS and JS assets using the filenames from FILES (e.g., style.css, script.js) unless FILE_REQUIREMENTS explicitly provide different paths.
- For multi-page projects: every HTML page must include a nav with links to ALL other HTML pages listed in FILES; ensure hrefs are correct.
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
"""

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
        
        if pm_content:
            # Include extracted content in the brief
            engineer_message = (
                f"{ENGINEER_BRIEF.strip()}\n\n"
                f"PREVIOUS_STATUS: {DEFAULT_AGENT_STATUSES['project_manager']}\n\n"
                f"EXTRACTED_PROJECT_MANAGER_CONTENT:\n{pm_content}\n\n"
                "IMPORTANT: Use the EXTRACTED_PROJECT_MANAGER_CONTENT above to extract PROJECT_NAME, FILES, ORDER, and STEPS. "
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
