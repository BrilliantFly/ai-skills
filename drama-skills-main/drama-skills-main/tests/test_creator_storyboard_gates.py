"""Regression for the three hard storyboard gates in creator_markdown_check.

G1 声音必填：every shot must carry a 「- 声音：」 field.
G2 场界空占位：a handoff field (转场/交出/接住) filled with an empty 无 placeholder
   is rejected — a non-boundary shot must not emit a handoff at all.
G3 终点态泄漏：the 冻结关键帧提示词 must project the 起点, never quote the 终点 verbatim
   (a shared 6-gram between the keyframe and the end state is the mechanical trace).

The native example (examples/creator-first/EP001) already satisfies all five
documents, so it doubles as the "quiet" baseline: none of these three errors may
appear on it. Each test copies it into a temp project, mutates 分镜.md to inject
exactly one violation, and asserts the matching gate fires.
"""

from __future__ import annotations

import importlib.util
import re
import shutil
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EPISODE = ROOT / "examples/creator-first/EP001"
VALIDATOR_SPEC = importlib.util.spec_from_file_location(
    "creator_markdown_check",
    ROOT / "skills/short-drama/scripts/creator_markdown_check.py",
)
assert VALIDATOR_SPEC and VALIDATOR_SPEC.loader
creator_markdown_check = importlib.util.module_from_spec(VALIDATOR_SPEC)
VALIDATOR_SPEC.loader.exec_module(creator_markdown_check)


class CreatorStoryboardGatesTest(unittest.TestCase):
    def _errors_after(self, mutate) -> list[str]:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            episode = project / "剧集/EP001"
            shutil.copytree(EPISODE, episode)
            path = episode / "分镜.md"
            path.write_text(
                mutate(path.read_text(encoding="utf-8")), encoding="utf-8"
            )
            return creator_markdown_check.validate_episode(episode, project)

    def test_gates_are_quiet_on_the_golden_baseline(self) -> None:
        errors = creator_markdown_check.validate_episode(EPISODE, ROOT)
        self.assertEqual(errors, [])

    def test_sound_field_is_required(self) -> None:
        def mutate(document: str) -> str:
            return re.sub(r"^- 声音：.*$\n", "", document, count=1, flags=re.MULTILINE)

        errors = self._errors_after(mutate)
        self.assertTrue(
            any("缺少「- 声音：」" in error for error in errors), errors
        )

    def test_empty_handoff_placeholder_is_rejected(self) -> None:
        def mutate(document: str) -> str:
            return document.replace("- 声音：", "- 转场交出：无\n- 声音：", 1)

        errors = self._errors_after(mutate)
        self.assertTrue(
            any("填了空占位" in error for error in errors), errors
        )

    def test_keyframe_must_not_quote_end_state(self) -> None:
        def mutate(document: str) -> str:
            return document.replace(
                "### 冻结关键帧提示词\n> ",
                "### 冻结关键帧提示词\n> 指节攥到发白茶面还在抖 ",
                1,
            )

        errors = self._errors_after(mutate)
        self.assertTrue(
            any("终点态成片文字" in error for error in errors), errors
        )


if __name__ == "__main__":
    unittest.main()
