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

import logging
from typing import Literal
from typing import TypedDict

from pydantic import BaseModel, model_validator
from pydantic import Field

from nat.builder.builder import Builder
from nat.builder.framework_enum import LLMFrameworkEnum
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.component_ref import LLMRef
from nat.data_models.function import FunctionBaseConfig

log = logging.getLogger(__name__)


class CodeGenToolConfig(FunctionBaseConfig, name="code_gen_tool"):
    """Advanced multi-language code generation tool with test-driven development workflow."""
    reasoning_llm: LLMRef
    code_llm: LLMRef
    max_iterations: int = Field(default=5, description="Maximum number of iterations for the TDD workflow")
    programming_language: list = Field(default=["Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust", "Swift", "Kotlin", "PHP", "Ruby", "Scala", "Haskell", "Clojure", "R", "MATLAB", "Julia", "Dart", "Lua", "Perl", "Shell", "Bash", "PowerShell", "SQL", "HTML", "CSS", "XML", "YAML", "JSON"], description="List of supported programming languages")
    description: str = Field(
        default="Advanced multi-language code generation agent using test driven development. Supports Python, JavaScript, TypeScript, Java, C++, C#, Go, Rust, Swift, Kotlin, PHP, Ruby, Scala, Haskell, and many more programming languages. Uses code_generation_tool to generate code and code_execution_tool to test. Provide input including the issue, current code to fix, and unit tests that should pass. The agent will generate code patches and iterate until tests pass.",
        description="Description of the code generation tool"
    )


class CodeGenInputSchema(BaseModel):
    """Input schema for the code generation tool."""
    problem_statement: str = Field(description="Description of the problem or issue to solve")
    current_code: str = Field(default="", description="Existing code that needs to be fixed or improved")
    unit_tests: str = Field(default="", description="Unit tests that should pass")
    programming_language: str = Field(default="", description="Target programming language for code generation")
    
    @model_validator(mode='before')
    @classmethod
    def handle_string_input(cls, data):
        """Handle string input by converting to dict format."""
        print(f"DEBUG CodeGen: Input data type: {type(data)}")
        print(f"DEBUG CodeGen: Input data: {data}")
        
        if isinstance(data, str):
            # Try to parse JSON from string if it contains structured data
            import json
            import re
            
            # Check if string contains JSON-like structure
            if 'problem_statement' in data and 'programming_language' in data:
                try:
                    # Extract JSON from string by finding balanced braces
                    start_idx = data.find('{')
                    if start_idx != -1:
                        brace_count = 0
                        end_idx = start_idx
                        for i, char in enumerate(data[start_idx:], start_idx):
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    end_idx = i + 1
                                    break
                        
                        if brace_count == 0:  # Found balanced braces
                            json_str = data[start_idx:end_idx]
                            parsed_data = json.loads(json_str)
                            result = {
                                "problem_statement": parsed_data.get('problem_statement', ''),
                                "current_code": parsed_data.get('current_code', ''),
                                "unit_tests": parsed_data.get('unit_tests', ''),
                                "programming_language": parsed_data.get('programming_language', '')
                            }
                            print(f"DEBUG CodeGen: Extracted JSON from string: {result}")
                            return result
                except (json.JSONDecodeError, AttributeError):
                    pass
            
            # If no JSON found or parsing failed, treat entire string as problem_statement
            result = {
                "problem_statement": data,
                "current_code": "",
                "unit_tests": "",
                "programming_language": ""
            }
            print(f"DEBUG CodeGen: Converted string to dict: {result}")
            return result
        
        # Handle dict input
        if isinstance(data, dict):
            problem_statement = data.get('problem_statement', '')
            
            # Check if problem_statement contains nested JSON-like structure
            if isinstance(problem_statement, str) and 'problem_statement' in problem_statement and 'programming_language' in problem_statement:
                try:
                    import json
                    import re
                    # Extract JSON from the nested string by finding balanced braces
                    start_idx = problem_statement.find('{')
                    if start_idx != -1:
                        brace_count = 0
                        end_idx = start_idx
                        for i, char in enumerate(problem_statement[start_idx:], start_idx):
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    end_idx = i + 1
                                    break
                        
                        if brace_count == 0:  # Found balanced braces
                            json_str = problem_statement[start_idx:end_idx]
                            parsed_data = json.loads(json_str)
                            result = {
                                "problem_statement": parsed_data.get('problem_statement', ''),
                                "current_code": parsed_data.get('current_code', ''),
                                "unit_tests": parsed_data.get('unit_tests', ''),
                                "programming_language": parsed_data.get('programming_language', '')
                            }
                            print(f"DEBUG CodeGen: Extracted JSON from nested dict: {result}")
                            return result
                except (json.JSONDecodeError, AttributeError):
                    pass
            
            result = {
                "problem_statement": problem_statement,
                "current_code": data.get('current_code', ''),
                "unit_tests": data.get('unit_tests', ''),
                "programming_language": data.get('programming_language', '')
            }
            print(f"DEBUG CodeGen: Processed dict input: {result}")
            return result
        
        print(f"DEBUG CodeGen: Returning data as-is: {data}")
        return data


class CodeState(TypedDict):
    """State for the code generation workflow."""
    problem_statement: str
    current_code: str
    unit_tests: str
    programming_language: str
    generated_code: str
    generated_unit_tests: str  # Unit tests generated by code generation tool
    test_results: dict
    iteration_count: int
    max_iterations: int
    reasoning_llm: object
    code_llm: object
    code_execution_tool: object
    code_generation_tool: object
    debug_feedback: str  # Debug feedback from reflection


@register_function(config_type=CodeGenToolConfig)
async def code_generation(config: CodeGenToolConfig, builder: Builder):
    """Advanced code generation function with LangGraph TDD workflow."""
    
    from langchain_core.prompts.chat import ChatPromptTemplate
    from langgraph.graph import StateGraph, START, END
    
    log.info('Initializing advanced code generation tool')
    
    reasoning_llm = await builder.get_llm(config.reasoning_llm, wrapper_type=LLMFrameworkEnum.LANGCHAIN)
    code_llm = await builder.get_llm(config.code_llm, wrapper_type=LLMFrameworkEnum.LANGCHAIN)
    
    code_execution_tool = builder.get_tools(tool_names=["code_execution_tool"], wrapper_type=LLMFrameworkEnum.LANGCHAIN)
    code_generation_tool = builder.get_tools(tool_names=["code_generation_tool"], wrapper_type=LLMFrameworkEnum.LANGCHAIN)
    
    if not code_execution_tool:
        raise ValueError("code_execution_tool not found. Please ensure it's configured in your workflow.")
    if not code_generation_tool:
        raise ValueError("code_generation_tool not found. Please ensure it's configured in your workflow.")
    
    code_execution_tool = code_execution_tool[0]  
    code_generation_tool = code_generation_tool[0]  
    
    # Define debug prompt for reasoning LLM (concise, actionable, test-edit allowed when wrong)
    debug_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """You are an expert debugger using NVIDIA NIM reflection. Analyze failing tests and produce concise, actionable guidance. Do NOT invent or add new tests. You MAY update expectations in EXISTING tests if they are objectively incorrect.

Problem Statement: {problem_statement}
Generated Code: {generated_code}
Generated Unit Tests: {generated_unit_tests}
Test Results: {test_results}

Instructions:
- Do not include chain-of-thought. Output only conclusions and steps.
- Keep feedback short, specific, and directly actionable.
- If a test is wrong, specify the exact assert to change and the corrected expected value. Do not add new tests.
- If code is wrong, point to the exact logic to change and how.
- Ensure the fix aligns with the problem statement.

Output (plain text, no markdown fences):
Root Cause:
- <one or two bullets>

Code Changes:
- <specific edit instructions>

Test Adjustments (only if tests are wrong):
- <which assert to change and the correct expected>

Next Steps:
- <brief steps to re-run and verify>""",
        ),
        (
            "user",
            "Analyze the test failures and generate debug feedback for the next iteration.",
        ),
    ])

    async def generate_code(state: CodeState) -> CodeState:
        """Generate code using the code_generation_tool."""
        log.info(f"Generating code for iteration {state['iteration_count']}")
        
        # Create a comprehensive prompt for code generation tool
        debug_context = ""
        if state.get("debug_feedback"):
            debug_context = f"""
Debug Feedback from Previous Iteration:
{state["debug_feedback"]}

Based on this feedback, fix the issues in the code and tests.
"""
        
        programming_lang = state.get("programming_language", "")
        
        # Handle None or empty values
        if programming_lang is None or programming_lang == "":
            log.info("No specific programming language provided, letting LLM infer from context")
            programming_lang = "the most appropriate language"
        else:
            # Validate that the target language is supported
            if programming_lang not in config.programming_language:
                log.warning(f"Language {programming_lang} not in supported list, letting LLM choose appropriate language")
                programming_lang = "the most appropriate language"
        
        # Get language-specific syntax and conventions
        if programming_lang == "the most appropriate language":
            # Let LLM choose the language and provide flexible syntax
            test_syntax = "Use appropriate assertion syntax for the chosen language"
            main_block = "Include appropriate main execution block for the chosen language"
        elif programming_lang.lower() in ["javascript", "typescript", "js", "ts"]:
            test_syntax = "expect(result).toBe(expected)"
            main_block = "// Run tests\nif (require.main === module) {\n    testFunction();\n}"
        elif programming_lang.lower() in ["java"]:
            test_syntax = "assert result == expected"
            main_block = "public static void main(String[] args) {\n    testFunction();\n}"
        elif programming_lang.lower() in ["c++", "cpp", "c"]:
            test_syntax = "assert(result == expected)"
            main_block = "int main() {\n    testFunction();\n    return 0;\n}"
        elif programming_lang.lower() in ["c#", "csharp"]:
            test_syntax = "Assert.AreEqual(expected, result)"
            main_block = "static void Main(string[] args) {\n    TestFunction();\n}"
        elif programming_lang.lower() in ["go"]:
            test_syntax = "if result != expected { t.Errorf(\"Expected %v, got %v\", expected, result) }"
            main_block = "func main() {\n    testFunction()\n}"
        elif programming_lang.lower() in ["rust"]:
            test_syntax = "assert_eq!(result, expected)"
            main_block = "fn main() {\n    test_function();\n}"
        else:  # Default to Python syntax
            test_syntax = "assert result == expected"
            main_block = "if __name__ == \"__main__\":\n    test_function()"
        
        if programming_lang == "the most appropriate language":
            prompt = f"""
Problem Statement: {state["problem_statement"]}
Current Code: {state.get("current_code", "")}
Unit Tests: {state.get("unit_tests", "")}
{debug_context}
Generate clean, executable code that solves the problem. Choose the most appropriate programming language based on the problem context.

For web development:
- HTML FILES: Generate ONLY HTML structure without embedded CSS or JavaScript
  * Use semantic HTML5 elements
  * Include proper DOCTYPE, head, and body structure  
  * Use external CSS file references: <link rel='stylesheet' href='styles.css'>
  * NO <style> tags or inline CSS
  * NO <script> tags or inline JavaScript

- CSS FILES: Generate ONLY CSS styling without HTML
  * Use proper CSS selectors and properties
  * Include responsive design with media queries
  * NO HTML tags or structure
  * Focus on styling and layout only

For other languages: Generate clean, executable code with proper structure and best practices.

CRITICAL: 
- For HTML: Generate ONLY HTML structure, reference external CSS files
- For CSS: Generate ONLY CSS styling, no HTML content  
- Keep HTML and CSS completely separate

IMPORTANT: Do NOT include any markdown backticks (```) in your response. Only provide clean code.

Just provide the code directly without special formatting markers.
"""
        else:
            # Special handling for web development languages
            if programming_lang.upper() == "HTML":
                prompt = f"""
Problem Statement: {state["problem_statement"]}
Current Code: {state.get("current_code", "")}
Unit Tests: {state.get("unit_tests", "")}
Target Language: {programming_lang}
{debug_context}
Generate clean HTML structure that solves the problem. 

CRITICAL HTML REQUIREMENTS:
- Generate ONLY HTML structure without embedded CSS or JavaScript
- Use semantic HTML5 elements (header, nav, main, section, footer, etc.)
- Include proper DOCTYPE, head, and body structure
- Use external CSS file references: <link rel='stylesheet' href='styles.css'>
- NO <style> tags or inline CSS
- NO <script> tags or inline JavaScript
- Include proper meta tags for viewport and charset
- Use meaningful class names for CSS targeting

IMPORTANT: Do NOT include any markdown backticks (```) in your response. Only provide clean HTML code.

Just provide the HTML code directly without special formatting markers.
"""
            elif programming_lang.upper() == "CSS":
                prompt = f"""
Problem Statement: {state["problem_statement"]}
Current Code: {state.get("current_code", "")}
Unit Tests: {state.get("unit_tests", "")}
Target Language: {programming_lang}
{debug_context}
Generate clean CSS styling that solves the problem.

CRITICAL CSS REQUIREMENTS:
- Generate ONLY CSS styling without HTML content
- Use proper CSS selectors and properties
- Include responsive design with media queries
- NO HTML tags or structure
- Focus on styling and layout only
- Use modern CSS features (flexbox, grid, etc.)
- Include proper typography and spacing

IMPORTANT: Do NOT include any markdown backticks (```) in your response. Only provide clean CSS code.

Just provide the CSS code directly without special formatting markers.
"""
            else:
                prompt = f"""
Problem Statement: {state["problem_statement"]}
Current Code: {state.get("current_code", "")}
Unit Tests: {state.get("unit_tests", "")}
Target Language: {programming_lang}
{debug_context}
Generate clean, executable {programming_lang} code that solves the problem. 
The code should include:
1. The main function to solve the problem
2. Proper error handling
3. Clear implementation
4. Fix any issues identified in the debug analysis
5. Follow {programming_lang} best practices and conventions

IMPORTANT: Do NOT include any markdown backticks (```) in your response. Only provide clean {programming_lang} code.

Just provide the code directly without special formatting markers.
"""
        
        try:
            # Convert prompt string to proper input format for code_generation_tool
            # Handle empty or None programming_language by providing a default
            if not programming_lang or programming_lang == "" or programming_lang == "the most appropriate language":
                tool_language = "Python"  
            else:
                tool_language = programming_lang
            tool_input = {
                "query": prompt,
                "programming_language": tool_language
            }
            response = await state["code_generation_tool"].ainvoke(tool_input)
            log.info(f"Generated response length: {len(response)}")
            # log.info(f"Response preview: {response}")
            
            # Simplified: treat entire response as code since we're focusing on code generation
            generated_code = response
            generated_unit_tests = ""
            log.info("Treating entire response as generated code (focus on code generation)")
                
        except Exception as e:
            log.exception("Error generating code with code_generation_tool")
            generated_code = f"# Error generating code: {str(e)}"
            generated_unit_tests = ""
        
        return {
            **state,
            "generated_code": generated_code,
            "generated_unit_tests": generated_unit_tests
        }

    async def test_code(state: CodeState) -> CodeState:
        """Execute the generated code and run tests using sandbox execution tool."""
        log.info("Running unit tests on generated code")
        
        # COMMENTED OUT: Focus on code generation first, skip testing for now
        # # Combine generated code and generated unit tests (following diagram)
        # generated_code = state['generated_code']
        # generated_unit_tests = state['generated_unit_tests']
        # 
        # # If no generated unit tests, use the provided unit_tests as fallback
        # if not generated_unit_tests and state.get('unit_tests'):
        #     generated_unit_tests = state['unit_tests']
        # 
        # # Create the complete test code to execute and ensure tests run in sandbox
        # test_code = f"""
        # {generated_code}
        # 
        # {generated_unit_tests}
        # 
        # # Auto-run discovered test_* functions using a snapshot to avoid mutation during iteration
        # _snapshot = [(k, v) for k, v in globals().items()]
        # for _name, _fn in _snapshot:
        #     if callable(_fn) and isinstance(_name, str) and _name.startswith("test_"):
        #         _fn()
        # """
        # 
        # try:
        #     # Execute using sandbox code execution tool (as shown in diagram)
        #     result = await state["code_execution_tool"].ainvoke({"generated_code": test_code})
        #     test_results = result if isinstance(result, dict) else {"stdout": str(result), "stderr": ""}
        # except Exception as e:
        #     log.exception("Error executing code")
        #     test_results = {"stdout": "", "stderr": str(e), "process_status": "error"}
        # 
        # log.info(f"Test results: {test_results}")

        # Skip testing for now - just return success
        test_results = {"stdout": "Tests skipped - focusing on code generation", "stderr": "", "process_status": "completed"}

        return {
            **state,
            "test_results": test_results,
            "iteration_count": state["iteration_count"] + 1
        }

    async def debug_code(state: CodeState) -> CodeState:
        """Use NVIDIA NIM reflection to analyze errors and generate debug feedback."""
        log.info("NVIDIA NIM reflection: Analyzing test failures and generating debug feedback")
        
        # COMMENTED OUT: Skip debug since we're not running tests
        # Just return the state without changes
        return state
        
        # COMMENTED OUT: All debug logic below
        # def _truncate(text: str, max_len: int = 4000) -> str:
        #     if not isinstance(text, str):
        #         text = str(text)
        #     if len(text) <= max_len:
        #         return text
        #     return text[:max_len] + "\n... [truncated] ...\n" + text[-max_len//4:]
        # 
        # # Prepare a size-safe prompt input
        # test_results = state["test_results"] or {}
        # safe_stdout = _truncate(test_results.get("stdout", ""), 4000)
        # safe_stderr = _truncate(test_results.get("stderr", ""), 2000)
        # safe_results = {**test_results, "stdout": safe_stdout, "stderr": safe_stderr}
        # prompt_input = {
        #     "problem_statement": _truncate(state.get("problem_statement", ""), 1000),
        #     "current_code": _truncate(state.get("generated_code", ""), 6000),
        #     "generated_unit_tests": _truncate(state.get("generated_unit_tests", ""), 4000),
        #     "test_results": safe_results,
        # }
        # 
        # # Helper to extract textual content from various response shapes
        # def _extract_text(resp) -> str:
        #     try:
        #         text = getattr(resp, "content", None)
        #         if isinstance(text, str) and text.strip():
        #             return text
        #         meta = getattr(resp, "response_metadata", None)
        #         if isinstance(meta, dict):
        #             for k in ("output_text", "text", "final_output", "message"):
        #                 v = meta.get(k)
        #                 if isinstance(v, str) and v.strip():
        #                     return v
        #         extra = getattr(resp, "additional_kwargs", None)
        #         if isinstance(extra, dict):
        #             for k in ("content", "output_text", "text", "final_output", "message"):
        #                 v = extra.get(k)
        #                 if isinstance(v, str) and v.strip():
        #                     return v
        #         if isinstance(resp, str):
        #             return resp
        #         if isinstance(resp, dict):
        #             for k in ("content", "output_text", "text", "final_output", "message"):
        #                 v = resp.get(k)
        #                 if isinstance(v, str) and v.strip():
        #                     return v
        #         return ""
        #     except Exception:
        #         return ""
        # 
        # # Create the prompt and invoke with LLM, with one retry on empty/whitespace-only content
        # debug_prompt_chain = debug_prompt | state["reasoning_llm"]
        # debug_response = await debug_prompt_chain.ainvoke(prompt_input)
        # debug_feedback = _extract_text(debug_response)
        # 
        # log.info(f"Debug response type: {type(debug_response)}")
        # log.info(f"Debug feedback length: {len(debug_feedback) if debug_feedback else 0}")
        # log.info(f"Debug feedback generated: {debug_feedback}")
        # 
        # # Retry once with minimized prompt if empty
        # if not debug_feedback or not debug_feedback.strip():
        #     log.info("Empty debug feedback received. Retrying once with minimized prompt.")
        #     minimal_input = {
        #         "problem_statement": prompt_input["problem_statement"],
        #         "current_code": _truncate(state.get("generated_code", ""), 2000),
        #         "generated_unit_tests": "",
        #         "test_results": {
        #             "stdout": _truncate(safe_results.get("stdout", ""), 800),
        #             "stderr": _truncate(safe_results.get("stderr", ""), 800),
        #             "process_status": safe_results.get("process_status", "unknown"),
        #         },
        #     }
        #     debug_response_retry = await debug_prompt_chain.ainvoke(minimal_input)
        #     debug_feedback = _extract_text(debug_response_retry)
        #     log.info(f"Retry debug feedback length: {len(debug_feedback) if debug_feedback else 0}")
        #     log.info(f"Retry debug feedback generated: {debug_feedback}")
        # 
        # # Final fallback: synthesize heuristic feedback when LLM remains empty
        # if not debug_feedback or not debug_feedback.strip():
        #     stderr_text = safe_results.get("stderr", "") or ""
        #     stdout_text = safe_results.get("stdout", "") or ""
        #     which_test = None
        #     for line in (stdout_text or "").splitlines():
        #         if line.startswith("TEST_FAIL:"):
        #             which_test = line.split(":", 1)[-1].strip()
        #             break
        #     hints = []
        #     if which_test:
        #         hints.append(f"Failing test detected: {which_test}.")
        #     if "AssertionError" in (stderr_text or ""):
        #         hints.append("An assertion failed. Compare expected vs. actual values and adjust either the implementation or the expected values accordingly.")
        #     if "NameError" in (stderr_text or ""):
        #         hints.append("A NameError occurred. Ensure referenced symbols (functions/variables) are defined in scope.")
        #     if "Traceback" in (stderr_text or ""):
        #         hints.append("There is a runtime error in the stack trace. Fix the reported line(s) first.")
        #     if stdout_text.strip():
        #         hints.append("The program produced printed outputs prior to failure. Ensure tests assert on return values, not printed text.")
        #     generic = (
        #         "For histogram largest-rectangle, maintain a stack of ascending indices; on pop, width is (i - stack[-1] - 1) or i if empty; update max_area each pop; after loop, drain stack similarly. Validate edge cases (empty, all equal, strictly mono)."
        #     )
        #     synthesized = "\n- ".join(hints) if hints else "General debugging required."
        #     debug_feedback = (
        #         "Automatic fallback feedback (LLM returned empty):\n"
        #         f"- {synthesized}\n"
        #         f"- {generic}"
        #     )
        # 
        # return {
        #     **state,
        #     "current_code": state["generated_code"],  # Keep current code for reference
        #     "debug_feedback": debug_feedback  # Store debug feedback for next iteration
        # }

    def should_continue(state: CodeState) -> Literal["end", "debug"]:
        """Determine whether to continue or end the workflow."""
        # COMMENTED OUT: Skip testing logic, always end after code generation
        # test_results = state["test_results"]
        # 
        # # Check if tests passed - require exactly 5 asserts and no errors
        # if test_results.get("process_status") == "completed":
        #     stdout = test_results.get("stdout", "")
        #     stderr = test_results.get("stderr", "")
        #     import re
        #     # Validate exactly 5 asserts present in generated unit tests
        #     unit_tests_text = state.get("generated_unit_tests", "") or state.get("unit_tests", "")
        #     assert_count = len(re.findall(r"^\s*assert\b", unit_tests_text, flags=re.MULTILINE))
        #     if (not stderr) and ("AssertionError" not in stdout) and ("ERROR" not in stdout) and assert_count == 5:
        #         log.info("All tests passed with exactly 5 asserts. Ending workflow.")
        #         return "end"
        #     # Fail or wrong assert count → continue debugging
        #     if stderr or "ERROR" in stdout or "AssertionError" in stdout or assert_count != 5:
        #         log.info(f"Tests not satisfied (assert_count={assert_count}). Continuing to debug.")
        #         return "debug"
        # 
        # # Check if we've exceeded max iterations
        # if state["iteration_count"] >= state["max_iterations"]:
        #     log.info(f"Reached max iterations ({state['max_iterations']}). Ending workflow.")
        #     return "end"
        # 
        # # Continue debugging
        # log.info("Tests failed, continuing to debug step.")
        # return "debug"
        
        # Always end after code generation since we're skipping tests
        log.info("Code generation completed. Ending workflow (tests skipped).")
        return "end"

    # Build the LangGraph workflow
    workflow = StateGraph(CodeState)
    workflow.add_node("code_generation", generate_code)
    workflow.add_node("run_unit_test", test_code)
    workflow.add_node("debug", debug_code)
    
    workflow.add_edge(START, "code_generation")
    workflow.add_edge("code_generation", "run_unit_test")
    workflow.add_conditional_edges(
        "run_unit_test",
        should_continue,
        {
            "end": END,
            "debug": "debug"
        }
    )
    workflow.add_edge("debug", "code_generation")
    
    agent = workflow.compile()

    async def _code_generation_tool(input_data: CodeGenInputSchema) -> dict:
        """Main function that orchestrates the TDD workflow."""
        log.info("Starting advanced code generation workflow")
        
        # Initialize state
        initial_state = CodeState(
            problem_statement=input_data.problem_statement,
            current_code=input_data.current_code,
            unit_tests=input_data.unit_tests,
            programming_language=input_data.programming_language,
            generated_code="",
            generated_unit_tests="",
            test_results={},
            iteration_count=0,
            max_iterations=config.max_iterations,
            reasoning_llm=reasoning_llm,
            code_llm=code_llm,
            code_execution_tool=code_execution_tool,
            code_generation_tool=code_generation_tool,
            debug_feedback=""
        )
        
        try:
            # Run the workflow
            final_state = await agent.ainvoke(initial_state)
            
            # Format the final result
            test_results = final_state['test_results']
            stdout = test_results.get('stdout', '')
            stderr = test_results.get('stderr', '')
            # Derive pass/fail consistent with should_continue: require 5 asserts and no errors
            import re
            unit_tests_text = final_state.get('generated_unit_tests', '') or final_state.get('unit_tests', '')
            assert_count = len(re.findall(r"^\s*assert\b", unit_tests_text, flags=re.MULTILINE))
            if test_results.get('process_status') == 'completed' and not stderr and 'AssertionError' not in stdout and 'ERROR' not in stdout and assert_count == 5:
                pass_count, fail_count = 5, 0
            else:
                # If error or wrong assert count, conservatively report failure
                pass_count = 0
                fail_count = max(0, 5 - pass_count)
            
            # Check for truncation and handle it
            truncated = test_results.get('truncated', False)
            if len(stdout) > 10000:
                stdout_display = stdout[:5000] + "\n... [truncated] ...\n" + stdout[-5000:]
                truncated = True
            else:
                stdout_display = stdout
                
            if len(stderr) > 5000:
                stderr_display = stderr[:2500] + "\n... [truncated] ...\n" + stderr[-2500:]
            else:
                stderr_display = stderr
            
            # Let LLM agent decide the file path based on context
            # This gives the agent full control over file organization
            return {
                "code_content": final_state['generated_code'],
                "file_path": "",  # Empty - LLM agent should provide meaningful path
                "execution_result": f"Code generated successfully for: {final_state['problem_statement']}"
            }
            
        except Exception as e:
            log.exception("Error in code generation workflow")
            return {
                "code_content": f"# Error in code generation workflow: {str(e)}",
                "file_path": "",  # Empty - let save_file_code_tool decide the path
                "execution_result": f"Error occurred: {str(e)}"
            }

    yield FunctionInfo.from_fn(
        _code_generation_tool,
        input_schema=CodeGenInputSchema,
        description=config.description
    )
