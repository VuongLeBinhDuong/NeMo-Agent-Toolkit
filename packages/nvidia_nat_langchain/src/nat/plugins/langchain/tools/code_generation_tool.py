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

from nat.builder.builder import Builder
from nat.builder.framework_enum import LLMFrameworkEnum
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.component_ref import LLMRef
from nat.data_models.function import FunctionBaseConfig

log = logging.getLogger(__name__)


class CodeGenerationTool(FunctionBaseConfig, name="code_generation"):
    """
    Tool for generating code using the configured LLM.
    Supports multiple programming languages for multi-agent software development.
    """
    llm_name: LLMRef
    verbose: bool = False
    programming_language: list = ["Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust", "Swift", "Kotlin", "PHP", "Ruby", "Scala", "Haskell", "Clojure", "R", "MATLAB", "Julia", "Dart", "Lua", "Perl", "Shell", "Bash", "PowerShell", "SQL", "HTML", "CSS", "XML", "YAML", "JSON"]
    description: str = ("Multi-language code generation tool. Supports Python, JavaScript, TypeScript, Java, C++, C#, Go, Rust, Swift, Kotlin, PHP, Ruby, Scala, Haskell, and many more programming languages. For any questions about code generation, you must only use this tool!")


@register_function(config_type=CodeGenerationTool)
async def code_generation_tool(config: CodeGenerationTool, builder: Builder):
    from langchain_core.prompts.chat import ChatPromptTemplate

    log.info('Initializing code generation tool\nGetting tool LLM from config')
    llm = await builder.get_llm(config.llm_name, wrapper_type=LLMFrameworkEnum.LANGCHAIN)

    system_prompt = """
You are a multi-language code assistant that can generate code in many programming languages. 
You are an expert in software development and can create high-quality, production-ready code.

Supported languages: {supported_languages}

For code generation:
- Generate clean, well-structured, and efficient code
- Follow best practices and coding standards for the requested language
- Include proper error handling and documentation
- Use appropriate design patterns and conventions
- Generate complete, executable code blocks
- If no specific language is mentioned, infer the most appropriate language from the context

Don't explain the code, just generate the code block itself with appropriate syntax highlighting.
"""
    user_prompt = """
{question}
"""
    log.info('Initialized code generation tool')

    async def _inner(query: str, programming_language: str = "") -> str:
        log.info('Running code generation tool')
        
        # Create prompt with supported languages list
        prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("user", user_prompt)])
        prompt = prompt.partial(
            supported_languages=", ".join(config.programming_language)
        )
        tool = prompt | llm
        
        # If specific language is requested, add it to the query
        if programming_language:
            if programming_language not in config.programming_language:
                log.warning(f"Language {programming_language} not in supported list")
            enhanced_query = f"Generate code in {programming_language}: {query}"
        else:
            enhanced_query = query
        
        response = await tool.ainvoke({"question": enhanced_query})
        if config.verbose:
            log.debug('Tool input was: %s\nTool output is: \n%s', enhanced_query, response)
        return response.content

    yield FunctionInfo.from_fn(_inner, description=config.description)
