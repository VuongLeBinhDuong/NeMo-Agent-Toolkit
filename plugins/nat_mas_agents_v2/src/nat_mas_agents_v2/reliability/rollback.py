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

"""Backup before write and restore on fatal test failure (rollback code)."""

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)


def _path_to_safe(rel_path: str) -> str:
    return rel_path.replace("/", "_").replace("\\", "_")


def save_backup(backup_dir: Path, rel_path: str, content: str) -> None:
    """Save file content to backup_dir for later restore. Overwrites existing backup for this path."""
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    safe = _path_to_safe(rel_path)
    (backup_dir / f"backup_{safe}").write_text(content, encoding="utf-8")
    manifest_path = backup_dir / "manifest.json"
    if manifest_path.exists():
        paths = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        paths = []
    if rel_path not in paths:
        paths.append(rel_path)
        manifest_path.write_text(json.dumps(paths, indent=0), encoding="utf-8")
    log.debug("Saved backup for %s to %s", rel_path, backup_dir)


def restore_from_backup(backup_dir: Path, repo_root: Path) -> None:
    """Restore all backed-up files into repo_root. Call after critic verdict fatal to rollback code."""
    backup_dir = Path(backup_dir)
    repo_root = Path(repo_root).resolve()
    manifest_path = backup_dir / "manifest.json"
    if not manifest_path.exists():
        log.warning("No manifest at %s, skip rollback", manifest_path)
        return
    paths = json.loads(manifest_path.read_text(encoding="utf-8"))
    for rel_path in paths:
        safe = _path_to_safe(rel_path)
        backup_file = backup_dir / f"backup_{safe}"
        if not backup_file.exists():
            log.warning("Backup file missing for %s", rel_path)
            continue
        target = repo_root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(backup_file.read_text(encoding="utf-8"), encoding="utf-8")
        log.info("Restored %s from backup (rollback)", rel_path)
