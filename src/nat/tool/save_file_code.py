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
import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from nat.builder.builder import Builder
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.function import FunctionBaseConfig

log = logging.getLogger(__name__)


class SaveFileCodeInput(BaseModel):
    """Input schema for saving executed code to file."""
    code_content: str = Field(description="The code content to save to file")
    file_path: str = Field(default="", description="Path where the code should be saved (optional, will auto-generate if not provided)")
    execution_result: str = Field(default="", description="Optional execution result summary to include in file comments")
    create_directories: bool = Field(default=True, description="Whether to create parent directories if they don't exist")
    encoding: str = Field(default="utf-8", description="File encoding to use")
    add_execution_info: bool = Field(default=True, description="Whether to add execution info as comments at the top of the file")
    
    @model_validator(mode='before')
    @classmethod
    def handle_input(cls, data):
        """Handle various input formats for save_file_code tool."""
        print(f"DEBUG save_file_code: Input data type: {type(data)}")
        
        # Handle string input - treat as code_content
        if isinstance(data, str):
            return {
                "code_content": data,
                "file_path": "",
                "execution_result": "",
                "create_directories": True,
                "encoding": "utf-8",
                "add_execution_info": True
            }
        
        # Handle dict input
        if isinstance(data, dict):
            return {
                "code_content": data.get('code_content', ''),
                "file_path": data.get('file_path', ''),
                "execution_result": data.get('execution_result', ''),
                "create_directories": data.get('create_directories', True),
                "encoding": data.get('encoding', 'utf-8'),
                "add_execution_info": data.get('add_execution_info', True)
            }
        
        return data


class SaveFileCodeConfig(FunctionBaseConfig, name="save_file_code"):
    """
    Tool for saving successfully executed code to files.
    This tool is used AFTER code has been debugged and executed successfully.
    """
    description: str = Field(
        default="Save successfully executed code to a file. Use this AFTER code has been debugged and tested successfully.",
        description="Description of the save executed code tool"
    )


@register_function(config_type=SaveFileCodeConfig)
async def save_file_code_tool(config: SaveFileCodeConfig, builder: Builder):
    """Tool for saving successfully executed code to files."""
    
    log.info('Initializing save executed code tool')
    
    async def _save_file_code(input_data: SaveFileCodeInput) -> str:
        """Save code to a file."""
        log.info(f'Saving code to: {input_data.file_path}')
        
        # Generate file path if not provided
        if not input_data.file_path or input_data.file_path.strip() == "":
            from datetime import datetime
            import re
            
            # Extract project name from execution_result or code_content
            project_name = "generated_code"
            content_lower = input_data.code_content.lower()
            
            # Determine project type from content
            if 'html' in content_lower or '<html>' in content_lower:
                project_name = "website"
                file_ext = ".html"
            elif 'css' in content_lower or '{' in content_lower:
                project_name = "website"
                file_ext = ".css"
            elif 'javascript' in content_lower or 'function' in content_lower:
                project_name = "website"
                file_ext = ".js"
            elif 'python' in content_lower or 'def ' in content_lower:
                project_name = "python_app"
                file_ext = ".py"
            else:
                file_ext = ".txt"
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            input_data.file_path = f"output/{project_name}_{timestamp}/file{file_ext}"
            log.info(f'Auto-generated file path: {input_data.file_path}')
        
        try:
            # Convert to Path object
            file_path = Path(input_data.file_path)
            
            # Create parent directories if requested
            if input_data.create_directories:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                log.info(f'Created directories: {file_path.parent}')
            
            # Write content to file
            with open(file_path, 'w', encoding=input_data.encoding) as f:
                # Process escape sequences to convert \n to actual newlines
                processed_content = input_data.code_content.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')
                f.write(processed_content)
            
            # Verify file was written
            if not file_path.exists() or os.path.getsize(file_path) == 0:
                raise IOError(f"File not saved correctly: {file_path}")
            
            # Get file info
            abs_path = file_path.resolve()
            file_size = os.path.getsize(abs_path)
            
            log.info(f'Successfully saved code to: {abs_path} ({file_size} bytes)')
            
            return f"""✅ Code saved successfully!

**File:** `{abs_path}`
**Size:** {file_size} bytes
**Status:** Ready to use! 🎉"""
            
        except Exception as e:
            error_msg = f"Error saving code to {input_data.file_path}: {str(e)}"
            log.error(error_msg)
            return f"""❌ Failed to save code

**Error:** {error_msg}
**File path:** {input_data.file_path}"""
    
    yield FunctionInfo.from_fn(
        _save_file_code,
        input_schema=SaveFileCodeInput,
        description=config.description
    )
