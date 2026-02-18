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

"""Detect loop / stuck state: same verdict or no progress across iterations."""

from typing import List

from ..models import Critique, TaskState


def is_stuck(
    state: TaskState,
    window: int = 3,
    same_verdict_only: bool = True,
) -> bool:
    """Return True if the last `window` critiques suggest we are stuck (no progress).

    Stuck = last N verdicts are all "continue" and (optionally) same suggested_fix/root_cause.
    """
    history: List[Critique] = state.critique_history or []
    if len(history) < window:
        return False
    last_n = history[-window:]
    if not all(c.verdict == "continue" for c in last_n):
        return False
    if same_verdict_only:
        return True
    # Optional: require same suggested_fix or root_cause to reduce false positives
    first_fix = (last_n[0].suggested_fix or "").strip()[:200]
    first_cause = (last_n[0].root_cause or "").strip()[:200]
    for c in last_n[1:]:
        if (c.suggested_fix or "").strip()[:200] != first_fix:
            return False
        if (c.root_cause or "").strip()[:200] != first_cause:
            return False
    return True
