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

import datetime
from zoneinfo import ZoneInfo

from mcp.server.fastmcp import FastMCP

# Create an MCP server instance
mcp = FastMCP("Our First MCP Server", port=15000)


# Define a tool
@mcp.tool()
def get_city_time(city: str) -> str:
    """Get the time in a specified city."""

    if city.lower() == "new york":
        tz_identifier = "America/New_York"
    else:
        return f"Sorry, I don't have timezone information for {city}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    report = f'The current time in {city} is {now.strftime("%Y-%m-%d %H:%M:%S %Z%z")}'
    return report


if __name__ == "__main__":
    mcp.run(transport="sse")
