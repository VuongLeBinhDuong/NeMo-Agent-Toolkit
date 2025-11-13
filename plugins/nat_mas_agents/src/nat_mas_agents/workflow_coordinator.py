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

PRODUCT_MANAGER_BRIEF = """
=== PRODUCT MANAGER BRIEF ===
You are Phase 1 Product Manager. You MUST follow strict ReAct format:

Thought: describe reasoning (plain text, no JSON)
Action: save_file_code
Action Input: {{"file_path": "output/doc/pm_output.txt", "code_content": "<FULL SPEC TEXT>"}}
Observation: Success message from tool (verbatim, no edits)
Thought: Confirm completion
Final Answer:
OUTPUT_FILE: output/doc/pm_output.txt
STATUS: Product specification saved.

Hard requirements:
- Call save_file_code exactly once.
- Action Input MUST be valid JSON with double-quoted keys/values, no trailing commas, no Markdown fences.
- Replace <FULL SPEC TEXT> with the complete specification body (no placeholders).
- Do NOT include extra commentary before or after the required sections.
- After the Observation from save_file_code, immediately provide the Final Answer block exactly as shown (no additional Thought/Action lines, no "Action: None").

Specification body (save to file) must include sections in order:
PRODUCT:
REQUIREMENTS: (3-5 sentences covering context, goals, users, success criteria)
FEATURES: (bullet list)
PRODUCTS: (items with name, price, category, description; categories must match filters)
CATEGORIES:
SORT_OPTIONS:
FUNCTIONALITY: (bullet list of behavioural requirements)
UI_COMPONENTS: (bullet list with identifiers/classes)

Additional rules:
- Never use placeholder text (TBD, lorem ipsum, etc.).
- Ensure PRODUCTS, CATEGORIES, SORT_OPTIONS align.
- Output spec only via save_file_code (not in Final Answer).
- Write the specification as plain text (no JSON/object literals). Use "- " for bullet items and separate sections with a blank line.
- Keep all tool JSON inline (no ``` fences or extra formatting).
"""

ARCHITECT_BRIEF = """
=== SYSTEM ARCHITECT BRIEF ===
You are Phase 2 System Architect. You MUST follow strict ReAct format:

Thought: describe reasoning (plain text, no JSON)
Action: save_file_code
Action Input: {{"file_path": "output/doc/architect_output.txt", "code_content": "<FULL ARCHITECTURE DOCUMENT>"}}
Observation: Success message from tool (verbatim, no edits)
Thought: Confirm completion
Final Answer:
OUTPUT_FILE: output/doc/architect_output.txt
STATUS: Architecture design saved.

Hard requirements:
- Call save_file_code exactly once.
- Action Input MUST be valid JSON with double-quoted keys/values, no trailing commas, no Markdown fences.
- Replace <FULL ARCHITECTURE DOCUMENT> with the complete architecture body (no placeholders).
- After the Observation from save_file_code, immediately provide the Final Answer block exactly as shown.
- Do NOT output the architecture document as plain text anywhere else and do not include PREVIOUS_STATUS.

Architecture body must include sections in order:
REQUIREMENTS: (paste verbatim from EXTRACTED_PM_CONTENT)
PRODUCTS: (paste verbatim from EXTRACTED_PM_CONTENT)
CATEGORIES: (paste verbatim from EXTRACTED_PM_CONTENT)
SORT_OPTIONS: (paste verbatim from EXTRACTED_PM_CONTENT)
FUNCTIONALITY: (paste verbatim from EXTRACTED_PM_CONTENT)
UI_COMPONENTS: (paste verbatim from EXTRACTED_PM_CONTENT)
FILE_REQUIREMENTS: (derive per-file responsibilities, use "- " bullets)
FILES: (comma-separated list, e.g. "index.html, styles.css, app.js")
ORDER: (arrow-separated, e.g. "index.html -> styles.css -> app.js")
"""

PROJECT_MANAGER_BRIEF = """
=== PROJECT MANAGER BRIEF ===
You are Phase 3 Project Manager. You MUST follow strict ReAct format:

Thought: describe reasoning (plain text, no JSON)
Action: save_file_code
Action Input: {{"file_path": "output/doc/project_manager_output.txt", "code_content": "<FULL PROJECT PLAN>"}}
Observation: Success message from tool (verbatim, no edits)
Thought: Confirm completion
Final Answer:
OUTPUT_FILE: output/doc/project_manager_output.txt
STATUS: Project plan saved.

Hard requirements:
- Call save_file_code exactly once.
- Action Input MUST be valid JSON with double-quoted keys/values, no trailing commas, no Markdown fences.
- Replace <FULL PROJECT PLAN> with the complete project plan body (no placeholders).
- After the Observation from save_file_code, immediately provide the Final Answer block exactly as shown.
- Do NOT output the project plan as plain text anywhere else.

Project plan body must include sections in order:
PROJECT_NAME: (short slug derived from requirements, lowercase, hyphen separated)
REQUIREMENTS: (paste verbatim from EXTRACTED_ARCHITECT_CONTENT)
PRODUCTS: (paste verbatim from EXTRACTED_ARCHITECT_CONTENT)
CATEGORIES: (paste verbatim from EXTRACTED_ARCHITECT_CONTENT)
SORT_OPTIONS: (paste verbatim from EXTRACTED_ARCHITECT_CONTENT)
FUNCTIONALITY: (paste verbatim from EXTRACTED_ARCHITECT_CONTENT)
UI_COMPONENTS: (paste verbatim from EXTRACTED_ARCHITECT_CONTENT)
FILES: (paste verbatim from EXTRACTED_ARCHITECT_CONTENT)
ORDER: (paste verbatim from EXTRACTED_ARCHITECT_CONTENT)
FILE_REQUIREMENTS: (paste verbatim from EXTRACTED_ARCHITECT_CONTENT)
STEPS: (one entry per file in numeric order. CRITICAL: Each step must be on a separate line. Format: "Step N: [filename]" followed by " Constraints: [constraints text]" on the same line. Each step should be on its own line, not all steps on one line. The constraints should contain (1) one-sentence restatement of overall REQUIREMENTS context, (2) the exact FILE_REQUIREMENTS bullet, and (3) explicit references to relevant PRODUCTS/CATEGORIES/SORT_OPTIONS/FUNCTIONALITY/UI_COMPONENTS. Use plain sentences, no JSON)
Example format:
STEPS:
Step 1: index.html Constraints: [full constraints text here]
Step 2: styles.css Constraints: [full constraints text here]
Step 3: app.js Constraints: [full constraints text here]
"""

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


class MASWorkflowConfig(FunctionBaseConfig, name="mas_workflow"):
    """Configuration for the MAS workflow coordinator."""

    product_manager: FunctionRef
    architect: FunctionRef
    project_manager: FunctionRef
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


@register_function(config_type=MASWorkflowConfig)
async def mas_workflow(config: MASWorkflowConfig, builder: Builder):
    """Register the MAS workflow coordinator as a NAT function.
    
    This coordinator chains the 4 phase functions sequentially:
    1. product_manager_phase - creates product specification from user request
    2. architect_phase - creates architecture design from PM output
    3. project_manager_phase - creates project plan from architect output
    4. engineer_phase - generates code files from project manager output
    
    Each phase function handles its own file I/O and brief prompts internally.
    """

    product_manager_phase_fn = builder.get_function(config.product_manager)
    architect_phase_fn = builder.get_function(config.architect)
    project_manager_phase_fn = builder.get_function(config.project_manager)
    engineer_phase_fn = builder.get_function(config.engineer)

    async def _response_fn(user_request: str) -> str:
        logger.info("Starting MAS workflow for request: %s", user_request)

        # Phase 1: Product Manager - uses user_request directly
        logger.info("Phase 1: Invoking product_manager_phase")
        pm_output = await product_manager_phase_fn.ainvoke(user_request)
        pm_status = _extract_status("product_manager", pm_output)
        logger.info("Product manager phase completed with status: %s", pm_status)

        # Phase 2: Architect - reads pm_output.txt automatically
        logger.info("Phase 2: Invoking architect_phase")
        architect_output = await architect_phase_fn.ainvoke("")  # user_request ignored, reads file instead
        architect_status = _extract_status("architect", architect_output)
        logger.info("Architect phase completed with status: %s", architect_status)

        # Phase 3: Project Manager - reads architect_output.txt automatically
        logger.info("Phase 3: Invoking project_manager_phase")
        project_manager_output = await project_manager_phase_fn.ainvoke("")  # user_request ignored, reads file instead
        project_manager_status = _extract_status("project_manager", project_manager_output)
        logger.info("Project manager phase completed with status: %s", project_manager_status)

        # Phase 4: Engineer - reads project_manager_output.txt automatically
        logger.info("Phase 4: Invoking engineer_phase")
        engineer_output = await engineer_phase_fn.ainvoke("")  # user_request ignored, reads file instead

        logger.info("MAS workflow completed; returning engineer output")
        return engineer_output

    yield FunctionInfo.create(single_fn=_response_fn)
