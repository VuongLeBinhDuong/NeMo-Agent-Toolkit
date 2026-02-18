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

"""Executor agent: run tests/shell and record results in TaskState."""

import logging
from datetime import datetime

from nat.builder.builder import Builder
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.function import FunctionBaseConfig
from pydantic import Field

from ..models import ExecutionLog, TaskState, TestResult
from ..tools import RunShellInput, RunTestInput

log = logging.getLogger(__name__)


class ExecutorStepConfig(FunctionBaseConfig, name="executor_step"):
    """Configuration for the Executor step."""

    description: str = Field(
        default="Run tests/shell and record results in TaskState execution_log and last_tests.",
        description="Description of the executor step",
    )


@register_function(config_type=ExecutorStepConfig)
async def executor_step(config: ExecutorStepConfig, builder: Builder):
    """Executor step: run tests/shell and append execution logs."""

    log.info("Initializing executor_step")

    run_test_fn = None
    run_shell_fn = None
    try:
        run_test_fn = builder.get_function("run_test")
    except Exception:
        pass
    try:
        run_shell_fn = builder.get_function("run_shell")
    except Exception:
        pass

    async def _executor(state: TaskState) -> TaskState:
        state = state.model_copy(deep=True)
        repo_root = state.repo_root or "."
        execution_log = list(state.execution_log)
        last_tests = state.last_tests

        if run_test_fn:
            try:
                inp = RunTestInput(
                    test_command="pytest -v --tb=no -q",
                    working_directory=repo_root,
                    timeout=120,
                )
                raw = await run_test_fn.ainvoke(inp)
                exit_code = 0 if raw and "passed" in (raw or "").lower() else 1
                execution_log.append(
                    ExecutionLog(
                        step="pytest",
                        command=inp.test_command,
                        exit_code=exit_code,
                        stdout=(raw or "")[:4096],
                        stderr="",
                        timestamp=datetime.now().isoformat(),
                    )
                )
                passed = (raw or "").count(" passed") or (0 if exit_code != 0 else 1)
                failed = (raw or "").count(" failed") or (1 if exit_code != 0 else 0)
                last_tests = TestResult(
                    passed=passed,
                    failed=failed,
                    errors=0,
                    skipped=0,
                    details=(raw or "")[:2048],
                )
            except Exception as e:
                log.warning("Executor: run_test failed: %s", e)
                execution_log.append(
                    ExecutionLog(
                        step="pytest",
                        command="pytest -v",
                        exit_code=-1,
                        stdout="",
                        stderr=str(e),
                        timestamp=datetime.now().isoformat(),
                    )
                )
        elif run_shell_fn:
            try:
                inp = RunShellInput(
                    command="echo 'No tests run'",
                    working_directory=repo_root,
                    timeout=10,
                )
                raw = await run_shell_fn.ainvoke(inp)
                execution_log.append(
                    ExecutionLog(
                        step="shell",
                        command=inp.command,
                        exit_code=0,
                        stdout=(raw or "")[:4096],
                        stderr="",
                        timestamp=datetime.now().isoformat(),
                    )
                )
            except Exception as e:
                log.warning("Executor: run_shell failed: %s", e)
                execution_log.append(
                    ExecutionLog(
                        step="shell",
                        command="echo",
                        exit_code=-1,
                        stdout="",
                        stderr=str(e),
                        timestamp=datetime.now().isoformat(),
                    )
                )
        else:
            execution_log.append(
                ExecutionLog(
                    step="noop",
                    command="(no executor tool)",
                    exit_code=0,
                    stdout="No run_test or run_shell tool configured.",
                    stderr="",
                    timestamp=datetime.now().isoformat(),
                )
            )

        state.execution_log = execution_log
        state.last_tests = last_tests
        state.updated_at = datetime.now().isoformat()
        return state

    yield FunctionInfo.from_fn(
        _executor,
        input_schema=TaskState,
        description=config.description,
    )
