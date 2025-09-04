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
import types
from collections.abc import Callable
from dataclasses import is_dataclass
from typing import Any
from typing import Union
from typing import get_args
from typing import get_origin

from pydantic import BaseModel

from nat.builder.builder import Builder
from nat.builder.framework_enum import LLMFrameworkEnum
from nat.builder.function import Function
from nat.cli.register_workflow import register_tool_wrapper

logger = logging.getLogger(__name__)


def resolve_type(t):
    origin = get_origin(t)
    if origin in (Union, types.UnionType):
        # Pick the first type that isn’t NoneType
        for arg in get_args(t):
            if arg is not None:
                return arg

        return t  # fallback if union is only NoneType (unlikely)
    return t


@register_tool_wrapper(wrapper_type=LLMFrameworkEnum.ADK)
def google_adk_tool_wrapper(name: str, fn: Function, builder: Builder):

    import inspect

    async def callable_ainvoke(*args, **kwargs):
        return await fn.acall_invoke(*args, **kwargs)

    async def callable_astream(*args, **kwargs):
        async for item in fn.acall_stream(*args, **kwargs):
            yield item

    def nat_function(func: Callable[..., object] | None = None,
                     nat_function: Function | None = fn,
                     name: str = name,
                     description: str = fn.description,
                     input_schema: BaseModel | None = fn.input_schema) -> Callable[..., Any]:
        """
        Decorator to wrap a function as a NAT function.
        """
        if func is None and nat_function is None:
            raise ValueError("Either 'func' or 'nat_function' must be provided.")

        # If input_schema is a dataclass, convert it to a Pydantic model
        if is_dataclass(input_schema):
            input_schema = BaseModel.model_validate(input_schema)

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            """
            Decorator to set metadata on the function.
            """
            # Set the function's metadata
            setattr(func, "__name__", name)
            setattr(func, "__doc__", description)
            setattr(
                func,
                "__signature__",
                inspect.Signature(parameters=[
                    inspect.Parameter(
                        name, inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=resolve_type(annotation))
                    for name, annotation in input_schema.__annotations__.items()
                ]))
            return func

        return decorator(func)

    from google.adk.tools.function_tool import FunctionTool

    if fn.has_streaming_output and not fn.has_single_output:
        logger.debug(f"Creating streaming FunctionTool for : {name}")
        callable_tool = nat_function(func=callable_astream)
    else:
        logger.debug(f"Creating non-streaming FunctionTool for : {name}")
        callable_tool = nat_function(func=callable_ainvoke)
    return FunctionTool(callable_tool)
