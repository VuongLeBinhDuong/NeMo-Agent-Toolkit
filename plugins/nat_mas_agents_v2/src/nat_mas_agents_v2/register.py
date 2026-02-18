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
- planner_step, worker_step, executor_step, critic_step, code_loop_workflow
- list_files, search_code, read_file, write_file, run_shell, run_test
"""

import logging

# Import tools, agents, and workflow so their @register_function decorators run
from . import tools  # noqa: F401
from . import agents  # noqa: F401
from . import workflow  # noqa: F401

logger = logging.getLogger(__name__)
