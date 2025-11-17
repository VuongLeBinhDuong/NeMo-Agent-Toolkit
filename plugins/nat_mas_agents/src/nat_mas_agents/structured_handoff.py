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

"""Structured JSON handoff format for sharing context between MAS agents.

This module provides functions to create and parse structured JSON handoffs
that clearly specify files, modules, shared assets, tasks, and data locations.
This ensures agents know exactly what to work with, leading to cohesive outputs.
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class StructuredHandoff:
    """Structured handoff data structure for MAS workflow."""

    def __init__(
        self,
        project_name: str = "",
        requirements: str = "",
        products: list[dict[str, Any]] | None = None,
        categories: list[str] | None = None,
        sort_options: list[str] | None = None,
        files: list[dict[str, Any]] | None = None,
        shared_assets: list[dict[str, Any]] | None = None,
        shared_components: list[str] | None = None,
        tasks: list[dict[str, Any]] | None = None,
        product_data_location: str = "",
    ):
        """Initialize structured handoff."""
        self.project_name = project_name
        self.requirements = requirements
        self.products = products or []
        self.categories = categories or []
        self.sort_options = sort_options or []
        self.files = files or []
        self.shared_assets = shared_assets or []
        self.shared_components = shared_components or []
        self.tasks = tasks or []
        self.product_data_location = product_data_location

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "project_name": self.project_name,
            "requirements": self.requirements,
            "products": self.products,
            "categories": self.categories,
            "sort_options": self.sort_options,
            "files": self.files,
            "shared_assets": self.shared_assets,
            "shared_components": self.shared_components,
            "tasks": self.tasks,
            "product_data_location": self.product_data_location,
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StructuredHandoff":
        """Create from dictionary."""
        return cls(
            project_name=data.get("project_name", ""),
            requirements=data.get("requirements", ""),
            products=data.get("products", []),
            categories=data.get("categories", []),
            sort_options=data.get("sort_options", []),
            files=data.get("files", []),
            shared_assets=data.get("shared_assets", []),
            shared_components=data.get("shared_components", []),
            tasks=data.get("tasks", []),
            product_data_location=data.get("product_data_location", ""),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "StructuredHandoff":
        """Create from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


def save_products_json(products: list[dict[str, Any]], file_path: str | Path) -> None:
    """Save products list to a JSON file for use in the website.
    
    This saves products to the project output directory (same location as HTML/CSS/JS files),
    not in the doc directory. The JSON file can be loaded by JavaScript to populate products.
    
    Args:
        products: List of product dictionaries with keys: name, price, category, description
        file_path: Path where to save the JSON file (should be in project output directory)
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Format products for JSON output
    products_data = {
        "products": products,
        "total": len(products)
    }
    
    json_content = json.dumps(products_data, indent=2, ensure_ascii=False)
    file_path.write_text(json_content, encoding="utf-8")
    logger.info(f"Saved {len(products)} products to {file_path}")


def load_products_json(file_path: str | Path) -> list[dict[str, Any]]:
    """Load products list from a JSON file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        List of product dictionaries
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the JSON format is invalid
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Products file not found: {file_path}")
    
    content = file_path.read_text(encoding="utf-8")
    data = json.loads(content)
    
    # Handle both formats: {"products": [...]} or direct list [...]
    if isinstance(data, dict) and "products" in data:
        products = data["products"]
    elif isinstance(data, list):
        products = data
    else:
        raise ValueError(f"Invalid products JSON format in {file_path}")
    
    logger.info(f"Loaded {len(products)} products from {file_path}")
    return products


def parse_pm_output_to_handoff(content: str) -> StructuredHandoff:
    """Parse Product Manager output text into structured handoff."""
    handoff = StructuredHandoff()

    lines = content.split("\n")
    current_section = None
    section_content = []

    for line in lines:
        stripped = line.strip()

        # Detect section headers
        if stripped.endswith(":") and not stripped.startswith("-"):
            # Save previous section
            if current_section:
                _process_section(handoff, current_section, "\n".join(section_content))

            # Start new section
            current_section = stripped.rstrip(":").upper()
            section_content = []
        elif current_section:
            section_content.append(line)

    # Process last section
    if current_section:
        _process_section(handoff, current_section, "\n".join(section_content))

    return handoff


def _process_section(handoff: StructuredHandoff, section: str, content: str) -> None:
    """Process a section of the PM output."""
    content = content.strip()

    if section == "PRODUCT":
        # Extract product name/description
        handoff.project_name = content.split("\n")[0].strip() if content else ""

    elif section == "REQUIREMENTS":
        handoff.requirements = content

    elif section == "PRODUCTS":
        # Parse products list
        products = []
        for line in content.split("\n"):
            line = line.strip()
            if line and (line.startswith("-") or line.startswith("•")):
                line = line.lstrip("- •").strip()
                # Format: "Product Name: $XX.XX, Category Name, Full description text"
                if ":" in line and "$" in line:
                    parts = line.split(":", 1)
                    name = parts[0].strip()
                    rest = parts[1].strip()

                    # Extract price
                    price_str = ""
                    if "$" in rest:
                        price_start = rest.find("$")
                        price_end = rest.find(",", price_start)
                        if price_end == -1:
                            price_end = rest.find(" ", price_start + 1)
                        if price_end == -1:
                            price_end = len(rest)
                        price_str = rest[price_start:price_end].replace("$", "").strip()

                    # Extract category
                    category = ""
                    if "," in rest:
                        parts_rest = rest.split(",")
                        if len(parts_rest) >= 2:
                            category = parts_rest[1].strip()

                    # Extract description
                    description = rest
                    if "," in rest:
                        desc_parts = rest.split(",", 2)
                        if len(desc_parts) >= 3:
                            description = desc_parts[2].strip()

                    products.append(
                        {
                            "name": name,
                            "price": float(price_str) if price_str.replace(".", "").isdigit() else 0.0,
                            "category": category,
                            "description": description,
                        }
                    )
        handoff.products = products

    elif section == "CATEGORIES":
        # Parse categories list
        categories = []
        for line in content.split("\n"):
            line = line.strip()
            if line and (line.startswith("-") or line.startswith("•")):
                category = line.lstrip("- •").strip()
                if category:
                    categories.append(category)
        handoff.categories = categories

    elif section == "SORT_OPTIONS":
        # Parse sort options list
        sort_options = []
        for line in content.split("\n"):
            line = line.strip()
            if line and (line.startswith("-") or line.startswith("•")):
                option = line.lstrip("- •").strip()
                if option:
                    sort_options.append(option)
        handoff.sort_options = sort_options

    elif section == "SHARED_COMPONENTS":
        # Parse shared components list
        components = []
        for line in content.split("\n"):
            line = line.strip()
            if line and (line.startswith("-") or line.startswith("•")):
                component = line.lstrip("- •").strip()
                if component:
                    components.append(component)
        handoff.shared_components = components

    elif section == "SHARED_ASSETS":
        # Parse shared assets list
        assets = []
        for line in content.split("\n"):
            line = line.strip()
            if line and (line.startswith("-") or line.startswith("•")):
                asset = line.lstrip("- •").strip()
                if asset:
                    assets.append({"name": asset, "type": "file", "path": asset})
        handoff.shared_assets = assets


def parse_architect_output_to_handoff(content: str, pm_handoff: StructuredHandoff | None = None) -> StructuredHandoff:
    """Parse Architect output text into structured handoff, inheriting from PM handoff."""
    handoff = pm_handoff.to_dict() if pm_handoff else {}
    handoff = StructuredHandoff.from_dict(handoff)

    lines = content.split("\n")
    current_section = None
    section_content = []

    for line in lines:
        stripped = line.strip()

        # Detect section headers
        if stripped.endswith(":") and not stripped.startswith("-"):
            # Save previous section
            if current_section:
                _process_architect_section(handoff, current_section, "\n".join(section_content))

            # Start new section
            current_section = stripped.rstrip(":").upper()
            section_content = []
        elif current_section:
            section_content.append(line)

    # Process last section
    if current_section:
        _process_architect_section(handoff, current_section, "\n".join(section_content))

    # After parsing architect output, save products to JSON in project output directory
    # and add it to shared_assets if products exist
    # NOTE: We don't create products.json here because PROJECT_NAME might not be finalized yet.
    # products.json will be created by engineer phase using the exact PROJECT_NAME from project manager.
    # We only add it to shared_assets if it's mentioned there.
    if handoff.products:
        # Check if products.json is already in shared_assets
        if not any(asset.get("name") == "products.json" for asset in handoff.shared_assets):
            # Add products.json to shared_assets (without path, engineer will generate it)
            products_json_asset = {
                "name": "products.json",
                "type": "json",
                "path": "products.json"  # Relative path, engineer will use PROJECT_NAME to create full path
            }
            handoff.shared_assets.append(products_json_asset)
            logger.info("Added products.json to shared_assets (will be generated by engineer phase)")

    return handoff


def _process_architect_section(handoff: StructuredHandoff, section: str, content: str) -> None:
    """Process a section of the Architect output."""
    content = content.strip()

    if section == "SHARED_ASSETS":
        # Parse shared assets list
        assets = []
        for line in content.split("\n"):
            line = line.strip()
            if line and (line.startswith("-") or line.startswith("•")):
                asset = line.lstrip("- •").strip()
                if asset:
                    assets.append({"name": asset, "type": "file", "path": asset})
        handoff.shared_assets = assets

    elif section == "FILES":
        # Parse files list (comma-separated)
        files = []
        file_list = content.replace("\n", " ").split(",")
        for file_name in file_list:
            file_name = file_name.strip()
            if file_name:
                # Determine file type from extension
                file_type = "unknown"
                if file_name.endswith(".html"):
                    file_type = "html"
                elif file_name.endswith(".css"):
                    file_type = "css"
                elif file_name.endswith(".js"):
                    file_type = "javascript"
                elif file_name.endswith(".json"):
                    file_type = "json"

                files.append(
                    {
                        "name": file_name,
                        "type": file_type,
                        "path": f"output/{handoff.project_name}/{file_name}" if handoff.project_name else file_name,
                    }
                )
        handoff.files = files

    elif section == "ORDER":
        # Parse order (arrow-separated)
        order = []
        order_list = content.replace("\n", " ").split("->")
        for file_name in order_list:
            file_name = file_name.strip()
            if file_name:
                order.append(file_name)
        # Update files with order
        for i, file_name in enumerate(order):
            for file_info in handoff.files:
                if file_info["name"] == file_name:
                    file_info["order"] = i + 1
                    break

    elif section == "FILE_REQUIREMENTS":
        # Parse file requirements
        current_file = None
        for line in content.split("\n"):
            line = line.strip()
            if line and (line.startswith("-") or line.startswith("•")):
                req = line.lstrip("- •").strip()
                # Try to match requirement to a file
                for file_info in handoff.files:
                    if file_info["name"] in req or req.startswith(file_info["name"]):
                        if "requirements" not in file_info:
                            file_info["requirements"] = []
                        file_info["requirements"].append(req)
                        break


def parse_project_manager_output_to_handoff(
    content: str, architect_handoff: StructuredHandoff | None = None
) -> StructuredHandoff:
    """Parse Project Manager output text into structured handoff, inheriting from Architect handoff."""
    handoff = architect_handoff.to_dict() if architect_handoff else {}
    handoff = StructuredHandoff.from_dict(handoff)

    lines = content.split("\n")
    current_section = None
    section_content = []

    for line in lines:
        stripped = line.strip()

        # Detect section headers
        if stripped.endswith(":") and not stripped.startswith("-") and not stripped.startswith("Step"):
            # Save previous section
            if current_section:
                _process_pm_section(handoff, current_section, "\n".join(section_content))

            # Start new section
            current_section = stripped.rstrip(":").upper()
            section_content = []
        elif current_section:
            section_content.append(line)

    # Process last section
    if current_section:
        _process_pm_section(handoff, current_section, "\n".join(section_content))

    return handoff


def _process_pm_section(handoff: StructuredHandoff, section: str, content: str) -> None:
    """Process a section of the Project Manager output."""
    content = content.strip()

    if section == "PROJECT_NAME":
        handoff.project_name = content.split("\n")[0].strip() if content else ""

    elif section == "STEPS":
        # Parse steps
        tasks = []
        import re

        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("Step"):
                # Format: "Step N: filename Constraints: [constraints text]"
                step_match = re.match(r"Step\s+(\d+):\s*(.+?)\s+Constraints:\s*(.+)$", line, re.IGNORECASE)
                if step_match:
                    step_num = int(step_match.group(1))
                    filename = step_match.group(2).strip()
                    constraints = step_match.group(3).strip()

                    tasks.append(
                        {
                            "step": step_num,
                            "filename": filename,
                            "constraints": constraints,
                            "status": "pending",
                        }
                    )
        handoff.tasks = tasks


def save_handoff_json(handoff: StructuredHandoff, file_path: str | Path) -> None:
    """Save structured handoff to JSON file."""
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(handoff.to_json(), encoding="utf-8")
    logger.info(f"Saved structured handoff to {file_path}")


def load_handoff_json(file_path: str | Path) -> StructuredHandoff:
    """Load structured handoff from JSON file."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Handoff file not found: {file_path}")

    content = file_path.read_text(encoding="utf-8")
    handoff = StructuredHandoff.from_json(content)
    logger.info(f"Loaded structured handoff from {file_path}")
    return handoff


def format_handoff_for_agent(handoff: StructuredHandoff) -> str:
    """Format structured handoff as a readable string for agent prompts."""
    lines = [
        "=== STRUCTURED HANDOFF DATA ===",
        "",
        f"PROJECT_NAME: {handoff.project_name}",
        "",
        "REQUIREMENTS:",
        handoff.requirements,
        "",
        "PRODUCTS:",
    ]

    for product in handoff.products:
        lines.append(f"  - {product['name']}: ${product['price']:.2f}, {product['category']}, {product['description']}")

    lines.extend(
        [
            "",
            "CATEGORIES:",
        ]
    )
    for category in handoff.categories:
        lines.append(f"  - {category}")

    lines.extend(
        [
            "",
            "SORT_OPTIONS:",
        ]
    )
    for option in handoff.sort_options:
        lines.append(f"  - {option}")

    lines.extend(
        [
            "",
            "FILES:",
        ]
    )
    for file_info in handoff.files:
        lines.append(f"  - {file_info['name']} ({file_info['type']})")
        if "order" in file_info:
            lines.append(f"    Order: {file_info['order']}")
        if "requirements" in file_info:
            lines.append(f"    Requirements: {', '.join(file_info['requirements'][:2])}...")

    lines.extend(
        [
            "",
            "SHARED_ASSETS:",
        ]
    )
    for asset in handoff.shared_assets:
        asset_name = asset.get('name', '')
        asset_type = asset.get('type', 'file')
        asset_path = asset.get('path', '')
        # Highlight products.json if present
        if asset_name == "products.json":
            lines.append(f"  - {asset_name} ({asset_type}) at {asset_path} ⚠️ CRITICAL: Products must be loaded from this JSON file, not hardcoded!")
        else:
            lines.append(f"  - {asset_name} ({asset_type}) at {asset_path}")
    
    # Add warning if products.json is in SHARED_ASSETS
    if any(asset.get('name') == 'products.json' for asset in handoff.shared_assets):
        lines.extend([
            "",
            "IMPORTANT: products.json is in SHARED_ASSETS. HTML files MUST have empty product containers, and script.js MUST load products from products.json using fetch()."
        ])

    lines.extend(
        [
            "",
            "SHARED_COMPONENTS:",
        ]
    )
    for component in handoff.shared_components:
        lines.append(f"  - {component}")

    lines.extend(
        [
            "",
            "TASKS:",
        ]
    )
    for task in handoff.tasks:
        lines.append(f"  Step {task['step']}: {task['filename']}")
        lines.append(f"    Constraints: {task['constraints'][:100]}...")

    lines.extend(
        [
            "",
            f"PRODUCT_DATA_LOCATION: {handoff.product_data_location or 'Hardcoded in HTML'}",
            "",
            "=== END STRUCTURED HANDOFF ===",
        ]
    )

    return "\n".join(lines)

