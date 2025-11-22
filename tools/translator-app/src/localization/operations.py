#!/usr/bin/env python3
"""Shared translation workflow backend for CLI and GUI clients."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from .registry import LANGUAGE_REGISTRY

ROOT_SENTINELS = ("main.py", "Main.py", "app_config.cfg")


def resolve_language_code(code: Optional[str]) -> Optional[str]:
    """Return the canonical registry key for a language code or alias."""

    if not code:
        return None
    normalized = code.strip().lower()
    if not normalized:
        return None
    for registered in LANGUAGE_REGISTRY.keys():
        if registered.lower() == normalized:
            return registered
    return None


def normalize_languages(languages: Optional[Sequence[str]]) -> List[str]:
    """Return a validated list of language codes.

    Passing "all" or nothing returns the full registry. Unknown codes are ignored.
    """

    if not languages:
        return list(LANGUAGE_REGISTRY.keys())

    resolved: List[str] = []
    for code in languages:
        if isinstance(code, str) and code.strip().lower() == "all":
            return list(LANGUAGE_REGISTRY.keys())
        canonical = resolve_language_code(code)
        if canonical:
            resolved.append(canonical)
    return resolved or list(LANGUAGE_REGISTRY.keys())


@dataclass
class TranslationPaths:
    """Resolved directories used by translation tooling."""

    project_root: Path
    src_dir: Path
    translations_dir: Path

    @classmethod
    def discover(cls, start: Optional[Path] = None) -> "TranslationPaths":
        """Discover repo root by walking parents until the primary src/ folder exists."""

        start_path = (start or Path(__file__)).resolve()
        if start_path.is_file():
            start_path = start_path.parent

        fallback: Optional[Tuple[Path, Path, Path]] = None

        for candidate in [start_path, *start_path.parents]:
            src_dir = candidate / "src"
            if not src_dir.exists():
                continue
            translations_dir = src_dir / "translations"
            if cls._looks_like_project_root(src_dir):
                return cls(candidate, src_dir, translations_dir)
            if fallback is None:
                fallback = (candidate, src_dir, translations_dir)

        if fallback:
            return cls(*fallback)

        # Fallback to current working directory layout
        project_root = Path.cwd()
        src_dir = project_root / "src"
        translations_dir = src_dir / "translations"
        return cls(project_root, src_dir, translations_dir)

    @staticmethod
    def _looks_like_project_root(src_dir: Path) -> bool:
        """Return True when the src folder appears to belong to the main app."""

        return any((src_dir / marker).exists() for marker in ROOT_SENTINELS)


@dataclass
class CommandResult:
    """Result of a subprocess run."""

    command: Sequence[str]
    success: bool
    stdout: str
    stderr: str
    exit_code: int


class CommandRunner:
    """Thin wrapper around subprocess.run so we can swap it during tests."""

    def run(self, command: Sequence[str], cwd: Optional[Path] = None) -> CommandResult:
        try:
            process = subprocess.run(
                command,
                cwd=str(cwd) if cwd else None,
                capture_output=True,
                text=True,
                shell=False,
                check=False,
            )
        except FileNotFoundError as exc:
            return CommandResult(
                command=command,
                success=False,
                stdout="",
                stderr=str(exc),
                exit_code=127,
            )
        return CommandResult(
            command=command,
            success=process.returncode == 0,
            stdout=process.stdout.strip(),
            stderr=process.stderr.strip(),
            exit_code=process.returncode,
        )


@dataclass
class OperationResult:
    """Canonical response for every translation workflow action."""

    name: str
    success: bool
    logs: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    details: Dict[str, object] = field(default_factory=dict)

    def add_log(self, message: str) -> None:
        self.logs.append(message)

    def add_error(self, message: str) -> None:
        self.errors.append(message)
        self.success = False


def _count_messages(ts_path: Path) -> Tuple[int, int]:
    """Return (total_messages, finished_messages) for a TS file."""

    if not ts_path.exists():
        return 0, 0

    content = ts_path.read_text(encoding="utf-8", errors="ignore")
    total = content.count("<message>")
    unfinished = content.count('type="unfinished"')
    finished = max(total - unfinished, 0)
    return total, finished


DISCLAIMER_BLOCK = """<context>
    <name>MachineTranslationDisclaimer</name>
    <message>
        <location filename="../main.py" line="0"/>
        <source>Machine Translation Notice</source>
        <translation type="unfinished">Machine Translation Notice</translation>
    </message>
    <message>
        <location filename="../main.py" line="1"/>
        <source>This language was automatically translated and may contain inaccuracies. If you would like to contribute better translations, please visit our GitHub repository.</source>
        <translation type="unfinished">This language was automatically translated and may contain inaccuracies. If you would like to contribute better translations, please visit our GitHub repository.</translation>
    </message>
</context>
"""


class LocalizationOperations:
    """High-level operations reused by CLI and GUI."""

    def __init__(
        self, paths: Optional[TranslationPaths] = None, runner: Optional[CommandRunner] = None
    ):
        self.paths = paths or TranslationPaths.discover()
        self.runner = runner or CommandRunner()
        self._tool_cache: Dict[str, List[str]] = {}

    def set_translations_dir(self, translations_dir: Path | str) -> TranslationPaths:
        """Override the discovered translations directory at runtime."""

        new_paths = self._build_paths_from_translations(translations_dir)
        self.paths = new_paths
        self._tool_cache.clear()
        return self.paths

    def _build_paths_from_translations(self, translations_dir: Path | str) -> TranslationPaths:
        candidate = Path(translations_dir).expanduser().resolve()
        if not candidate.exists() or not candidate.is_dir():
            raise ValueError("Translations directory does not exist.")

        src_dir = candidate.parent
        if not src_dir.exists():
            raise ValueError("Translations directory must live inside a src folder.")

        if not TranslationPaths._looks_like_project_root(src_dir):
            raise ValueError(
                "Selected folder is not part of a recognized TextureAtlas Toolbox source tree."
            )

        project_root = src_dir.parent
        return TranslationPaths(project_root, src_dir, candidate)

    def _ensure_translations_dir(self) -> None:
        self.paths.translations_dir.mkdir(parents=True, exist_ok=True)

    def _collect_source_files(self) -> List[Path]:
        if not self.paths.src_dir.exists():
            return []

        files: List[Path] = []
        for pattern in ("*.py", "*.ui"):
            files.extend(self.paths.src_dir.rglob(pattern))

        unique_files = {f.resolve() for f in files if f.is_file()}
        return sorted(unique_files)

    def _build_tool_command(self, tool: str, extra_args: Sequence[str]) -> List[str]:
        base = self._tool_cache.get(tool)
        if base is None:
            base = self._resolve_tool(tool)
            self._tool_cache[tool] = base
        return base + list(extra_args)

    def _resolve_tool(self, tool: str) -> List[str]:
        env_key = {"lupdate": "QT_LUPDATE", "lrelease": "QT_LRELEASE"}.get(tool)
        if env_key:
            env_value = os.environ.get(env_key)
            if env_value:
                candidate = Path(env_value)
                if candidate.exists():
                    return [str(candidate)]

        pyside_candidates: List[Path] = []
        try:
            import PySide6  # type: ignore
        except Exception:
            PySide6 = None  # type: ignore
        if PySide6 is not None:
            pyside_dir = Path(PySide6.__file__).resolve().parent
            pyside_candidates.extend(
                [
                    pyside_dir / tool,
                    pyside_dir / f"{tool}.exe",
                    pyside_dir / "Qt" / "libexec" / tool,
                    pyside_dir / "Qt" / "libexec" / f"{tool}.exe",
                ]
            )
        for candidate in pyside_candidates:
            if candidate.exists():
                return [str(candidate)]

        exe_name = f"pyside6-{tool}"
        which_path = shutil.which(exe_name)
        if which_path:
            return [which_path]

        alt_path = shutil.which(tool)
        if alt_path:
            return [alt_path]

        return [exe_name]

    def extract(self, languages: Optional[Sequence[str]] = None) -> OperationResult:
        self._ensure_translations_dir()
        result = OperationResult("extract", True)
        selected = normalize_languages(languages)
        source_files = self._collect_source_files()

        if not self.paths.src_dir.exists():
            result.add_error(f"Source directory not found: {self.paths.src_dir}")
            return result

        if not source_files:
            result.add_error("No source or UI files found for extraction.")
            return result

        per_language = []
        for lang in selected:
            ts_file = self.paths.translations_dir / f"app_{lang}.ts"
            cmd = self._build_tool_command(
                "lupdate",
                [*(str(f) for f in source_files), "-ts", str(ts_file)],
            )
            run_result = self.runner.run(cmd, cwd=self.paths.project_root)
            per_language.append(
                {
                    "language": lang,
                    "ts_file": str(ts_file),
                    "success": run_result.success,
                    "stdout": run_result.stdout,
                    "stderr": run_result.stderr,
                    "exit_code": run_result.exit_code,
                }
            )
            log_line = f"{'✅' if run_result.success else '❌'} {lang}: wrote {ts_file}"
            result.add_log(log_line)
            if not run_result.success:
                result.add_error(f"Failed to update {ts_file}")
        result.details["per_language"] = per_language
        result.details["files_processed"] = len(source_files)
        return result

    def compile(self, languages: Optional[Sequence[str]] = None) -> OperationResult:
        self._ensure_translations_dir()
        result = OperationResult("compile", True)
        selected = normalize_languages(languages)

        per_language = []
        for lang in selected:
            ts_file = self.paths.translations_dir / f"app_{lang}.ts"
            if not ts_file.exists():
                result.add_log(f"Skipping {lang}: missing {ts_file}")
                continue
            qm_file = ts_file.with_suffix(".qm")
            cmd = self._build_tool_command("lrelease", [str(ts_file), "-qm", str(qm_file)])
            run_result = self.runner.run(cmd, cwd=self.paths.project_root)
            per_language.append(
                {
                    "language": lang,
                    "ts_file": str(ts_file),
                    "qm_file": str(qm_file),
                    "success": run_result.success,
                    "stdout": run_result.stdout,
                    "stderr": run_result.stderr,
                    "exit_code": run_result.exit_code,
                }
            )
            log_line = f"{'✅' if run_result.success else '❌'} {lang}: compiled {qm_file.name}"
            result.add_log(log_line)
            if not run_result.success:
                result.add_error(f"Failed to compile {ts_file}")
        result.details["per_language"] = per_language
        return result

    def create_resource_file(self) -> OperationResult:
        self._ensure_translations_dir()
        result = OperationResult("resource", True)
        qm_files = sorted(self.paths.translations_dir.glob("app_*.qm"))
        if not qm_files:
            result.add_error("No .qm files found. Compile translations first.")
            return result

        qrc_content = [
            "<!DOCTYPE RCC>",
            '<RCC version="1.0">',
            '<qresource prefix="/translations">',
        ]
        for qm_file in qm_files:
            qrc_content.append(f"    <file>{qm_file.name}</file>")
        qrc_content.append("</qresource>")
        qrc_content.append("</RCC>")

        qrc_path = self.paths.translations_dir / "translations.qrc"
        qrc_path.write_text("\n".join(qrc_content), encoding="utf-8")
        result.add_log(f"Wrote resource file: {qrc_path}")
        result.details["qrc"] = str(qrc_path)
        return result

    def status_report(self, languages: Optional[Sequence[str]] = None) -> OperationResult:
        result = OperationResult("status", True)
        selected = normalize_languages(languages)
        entries = []
        for lang in selected:
            meta = LANGUAGE_REGISTRY.get(lang, {})
            ts_file = self.paths.translations_dir / f"app_{lang}.ts"
            qm_file = ts_file.with_suffix(".qm")
            ts_exists = ts_file.exists()
            qm_exists = qm_file.exists()
            total, finished = _count_messages(ts_file)
            unfinished = max(total - finished, 0)
            entry = {
                "language": lang,
                "name": meta.get("name", lang),
                "english_name": meta.get("english_name", meta.get("name", lang)),
                "quality": meta.get("quality", "unknown"),
                "ts_exists": ts_exists,
                "qm_exists": qm_exists,
                "ts_file": str(ts_file),
                "qm_file": str(qm_file),
                "total_messages": total,
                "finished_messages": finished,
                "unfinished_messages": unfinished,
                "needs_update": (not ts_exists) or unfinished > 0,
            }
            entries.append(entry)
            progress = f"{finished}/{total}" if total else "0/0"
            result.add_log(
                f"{lang.upper()} | .ts {'✅' if entry['ts_exists'] else '❌'} | .qm {'✅' if entry['qm_exists'] else '❌'} | {progress}"
            )
        result.details["entries"] = entries
        return result

    def inject_disclaimers(self, languages: Optional[Sequence[str]] = None) -> OperationResult:
        self._ensure_translations_dir()
        result = OperationResult("disclaimer", True)
        selected = normalize_languages(languages)

        for lang in selected:
            meta = LANGUAGE_REGISTRY.get(lang, {})
            if meta.get("quality") != "machine":
                result.add_log(f"Skipping {lang}: not tagged as machine translated")
                continue

            ts_file = self.paths.translations_dir / f"app_{lang}.ts"
            if not ts_file.exists():
                result.add_log(f"Skipping {lang}: missing {ts_file}")
                continue

            content = ts_file.read_text(encoding="utf-8")
            if "MachineTranslationDisclaimer" in content:
                result.add_log(f"Disclaimer already present in {ts_file.name}")
                continue

            if "</TS>" not in content:
                result.add_error(f"Malformed TS file (missing </TS>): {ts_file}")
                continue

            updated = content.replace("</TS>", DISCLAIMER_BLOCK + "\n</TS>")
            ts_file.write_text(updated, encoding="utf-8")
            result.add_log(f"Inserted disclaimer into {ts_file.name}")
        return result


__all__ = [
    "LocalizationOperations",
    "TranslationPaths",
    "CommandRunner",
    "CommandResult",
    "OperationResult",
    "resolve_language_code",
    "normalize_languages",
]
