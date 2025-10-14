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

from pydantic import BaseModel
from pydantic import Field

from nat.builder.builder import Builder
from nat.builder.framework_enum import LLMFrameworkEnum
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.component_ref import LLMRef
from nat.data_models.function import FunctionBaseConfig

log = logging.getLogger(__name__)


class CodeGenToolConfig(FunctionBaseConfig, name="code_gen_tool"):
    """Advanced code generation tool with test-driven development workflow."""
    reasoning_llm: LLMRef
    code_llm: LLMRef
    max_iterations: int = Field(default=5, description="Maximum number of iterations for the TDD workflow")
    description: str = Field(
        default="Advanced code generation agent using test driven development. Uses code_generation_tool to generate code and code_execution_tool to test. Provide input including the issue, current code to fix, and unit tests that should pass. The agent will generate code patches and iterate until tests pass.",
        description="Description of the code generation tool"
    )


class CodeGenInputSchema(BaseModel):
    """Input schema for the code generation tool."""
    problem_statement: str = Field(description="Description of the problem or issue to solve")
    current_code: str = Field(default="", description="Existing code that needs to be fixed or improved")
    unit_tests: str = Field(default="", description="Unit tests that should pass")


class CodeState(TypedDict):
    """State for the code generation workflow."""
    problem_statement: str
    current_code: str
    unit_tests: str
    generated_code: str
    test_results: dict
    iteration_count: int
    max_iterations: int
    reasoning_llm: object
    code_llm: object
    code_execution_tool: object
    code_generation_tool: object


@register_function(config_type=CodeGenToolConfig)
async def code_generation(config: CodeGenToolConfig, builder: Builder):
    """Advanced code generation function with LangGraph TDD workflow."""
    
    from langchain_core.prompts.chat import ChatPromptTemplate
    from langgraph.graph import StateGraph, START, END
    
    log.info('Initializing advanced code generation tool')
    
    # Get the LLMs
    reasoning_llm = await builder.get_llm(config.reasoning_llm, wrapper_type=LLMFrameworkEnum.LANGCHAIN)
    code_llm = await builder.get_llm(config.code_llm, wrapper_type=LLMFrameworkEnum.LANGCHAIN)
    
    # Get tools
    code_execution_tool = builder.get_tools(tool_names=["code_execution_tool"], wrapper_type=LLMFrameworkEnum.LANGCHAIN)
    code_generation_tool = builder.get_tools(tool_names=["code_generation_tool"], wrapper_type=LLMFrameworkEnum.LANGCHAIN)
    
    if not code_execution_tool:
        raise ValueError("code_execution_tool not found. Please ensure it's configured in your workflow.")
    if not code_generation_tool:
        raise ValueError("code_generation_tool not found. Please ensure it's configured in your workflow.")
    
    code_execution_tool = code_execution_tool[0]  # Get the first tool
    code_generation_tool = code_generation_tool[0]  # Get the first tool
    
    # Define debug prompt for reasoning LLM
    debug_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert debugger. Analyze the test failure and suggest improvements to the code.

Problem Statement: {problem_statement}
Current Code: {current_code}
Unit Tests: {unit_tests}
Test Results: {test_results}

Based on the test failure, provide specific suggestions for fixing the code. Focus on:
1. Identifying the root cause of the test failure
2. Suggesting specific code changes
3. Ensuring the solution addresses the original problem statement

Return your analysis and suggestions."""),
        ("user", "Analyze the test failure and suggest fixes.")
    ])

    async def generate_code(state: CodeState) -> CodeState:
        """Generate code using the code_generation_tool."""
        log.info(f"Generating code for iteration {state['iteration_count']}")
        
        # Create a comprehensive prompt for code generation tool
        prompt = f"""
Problem Statement: {state["problem_statement"]}
Current Code: {state["current_code"]}
Unit Tests: {state["unit_tests"]}

Generate clean, executable Python code with exactly 3 test cases that demonstrate different scenarios. 
The code should include:
1. The main function to solve the problem
2. Three test cases with clear output showing PASS/FAIL status
3. Proper error handling

Format the output as:
```python
def function_name(params):
    # implementation
    return answer

# Test cases
print("Running test cases:")
print("Test 1: [description]")
test_input1 = [actual_test_input_values]
print(f"Input: {{test_input1}}")
result1 = function_name(test_input1)
expected1 = expected_value1
print(f"Result: {{result1}}")
print(f"Expected: {{expected1}}")
print(f"Status: {{'PASS' if result1 == expected1 else 'FAIL'}}")
print()

print("Test 2: [description]")
test_input2 = [actual_test_input_values]
print(f"Input: {{test_input2}}")
result2 = function_name(test_input2)
expected2 = expected_value2
print(f"Result: {{result2}}")
print(f"Expected: {{expected2}}")
print(f"Status: {{'PASS' if result2 == expected2 else 'FAIL'}}")
print()

print("Test 3: [description]")
test_input3 = [actual_test_input_values]
print(f"Input: {{test_input3}}")
result3 = function_name(test_input3)
expected3 = expected_value3
print(f"Result: {{result3}}")
print(f"Expected: {{expected3}}")
print(f"Status: {{'PASS' if result3 == expected3 else 'FAIL'}}")
```
"""
        
        try:
            generated_code = await state["code_generation_tool"].ainvoke(prompt)
            log.info(f"Generated code length: {len(generated_code)}")
        except Exception as e:
            log.exception("Error generating code with code_generation_tool")
            generated_code = f"# Error generating code: {str(e)}"
        
        return {
            **state,
            "generated_code": generated_code
        }

    async def test_code(state: CodeState) -> CodeState:
        """Execute the generated code and run tests."""
        log.info("Running unit tests on generated code")
        
        # Use the generated code directly as it should contain the tests
        test_code = state['generated_code']
        
        try:
            # Execute the code using the code execution tool
            result = await state["code_execution_tool"].ainvoke({"generated_code": test_code})
            test_results = result if isinstance(result, dict) else {"stdout": str(result), "stderr": ""}
        except Exception as e:
            log.exception("Error executing code")
            test_results = {"stdout": "", "stderr": str(e), "process_status": "error"}
        
        return {
            **state,
            "test_results": test_results,
            "iteration_count": state["iteration_count"] + 1
        }

    async def debug_code(state: CodeState) -> CodeState:
        """Use reasoning LLM to analyze test failures and suggest improvements."""
        log.info("Debugging test failures")
        
        prompt_input = {
            "problem_statement": state["problem_statement"],
            "current_code": state["generated_code"],
            "unit_tests": state["unit_tests"],
            "test_results": state["test_results"]
        }
        
        # Create the prompt and invoke with LLM
        debug_prompt_chain = debug_prompt | state["reasoning_llm"]
        debug_response = await debug_prompt_chain.ainvoke(prompt_input)
        debug_analysis = debug_response.content
        
        log.info(f"Debug analysis: {debug_analysis}")
        
        return {
            **state,
            "current_code": state["generated_code"]  # Update current code for next iteration
        }

    def should_continue(state: CodeState) -> Literal["end", "debug"]:
        """Determine whether to continue or end the workflow."""
        test_results = state["test_results"]
        
        # Check if tests passed - look for success indicators
        if test_results.get("process_status") == "completed":
            stdout = test_results.get("stdout", "")
            stderr = test_results.get("stderr", "")
            
            # Count PASS/FAIL status in output
            pass_count = stdout.count("Status: PASS")
            fail_count = stdout.count("Status: FAIL")
            
            # If all tests passed (3 PASS, 0 FAIL), end the workflow
            if pass_count >= 3 and fail_count == 0:
                log.info(f"All tests passed! ({pass_count} PASS, {fail_count} FAIL) Ending workflow.")
                return "end"
            
            # If there are failures or errors, continue debugging
            if fail_count > 0 or stderr or "ERROR" in stdout or "AssertionError" in stdout:
                log.info(f"Tests failed ({pass_count} PASS, {fail_count} FAIL). Continuing to debug.")
                return "debug"
        
        # Check if we've exceeded max iterations
        if state["iteration_count"] >= state["max_iterations"]:
            log.info(f"Reached max iterations ({state['max_iterations']}). Ending workflow.")
            return "end"
        
        # Continue debugging
        log.info("Tests failed, continuing to debug step.")
        return "debug"

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

    async def _code_generation_tool(input_data: CodeGenInputSchema) -> str:
        """Main function that orchestrates the TDD workflow."""
        log.info("Starting advanced code generation workflow")
        
        # Initialize state
        initial_state = CodeState(
            problem_statement=input_data.problem_statement,
            current_code=input_data.current_code,
            unit_tests=input_data.unit_tests,
            generated_code="",
            test_results={},
            iteration_count=0,
            max_iterations=config.max_iterations,
            reasoning_llm=reasoning_llm,
            code_llm=code_llm,
            code_execution_tool=code_execution_tool,
            code_generation_tool=code_generation_tool
        )
        
        try:
            # Run the workflow
            final_state = await agent.ainvoke(initial_state)
            
            # Format the final result
            test_results = final_state['test_results']
            stdout = test_results.get('stdout', '')
            stderr = test_results.get('stderr', '')
            pass_count = stdout.count("Status: PASS")
            fail_count = stdout.count("Status: FAIL")
            
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
            
            result = f"""
## Code Generation Complete

**Problem Statement:** {final_state['problem_statement']}

**Final Generated Code:**
```python
{final_state['generated_code']}
```

**Test Results:**
- Process Status: {test_results.get('process_status', 'unknown')}
- Iterations: {final_state['iteration_count']}/{final_state['max_iterations']}
- Test Summary: {pass_count} PASS, {fail_count} FAIL
- Output Truncated: {truncated}

**Execution Output:**
```
{stdout_display}
```

**Errors:**
```
{stderr_display}
```

**Summary:**
{'All tests passed!' if pass_count >= 3 and fail_count == 0 else f'Some tests failed ({pass_count} PASS, {fail_count} FAIL)'}
"""
            
            return result
            
        except Exception as e:
            log.exception("Error in code generation workflow")
            return f"Error in code generation workflow: {str(e)}"

    yield FunctionInfo.from_fn(
        _code_generation_tool,
        input_schema=CodeGenInputSchema,
        description=config.description
    )
