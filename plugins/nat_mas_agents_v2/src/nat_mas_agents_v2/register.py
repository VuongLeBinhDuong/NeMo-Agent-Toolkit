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

"""Register MAS V2 workflow and tools with NAT.

This plugin is independent of nat_mas_agents (v1). It provides:
- product_step, architect_step, planner_step, worker_step, executor_step, critic_step
- code_loop_workflow, full_mas_workflow (Product → Architect → code loop)
- list_files, search_code, read_file, write_file, run_shell, run_test
"""

import json
import logging
from io import TextIOWrapper

from nat.utils.type_converter import GlobalTypeConverter

from .models import TaskState

# Import tools, agents, and workflow so their @register_function decorators run
from . import tools  # noqa: F401
from . import agents  # noqa: F401
from . import workflow  # noqa: F401

logger = logging.getLogger(__name__)


def _text_io_to_task_state(data: TextIOWrapper) -> TaskState:
    """Convert JSON file content to TaskState so nat run --input_file works."""
    return TaskState.model_validate(json.load(data))


def _str_to_task_state(data: str) -> TaskState:
    """Convert JSON string to TaskState so nat run --input works."""
    return TaskState.model_validate(json.loads(data))


def _task_state_to_str(data: TaskState) -> str:
    """Convert TaskState to JSON string so nat run can print the result."""
    return data.model_dump_json(indent=2)


GlobalTypeConverter.register_converter(_text_io_to_task_state)
GlobalTypeConverter.register_converter(_str_to_task_state)
GlobalTypeConverter.register_converter(_task_state_to_str)
