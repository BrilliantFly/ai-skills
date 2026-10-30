"""武打登记行（`- 武打：`）三条机械门的回归测试。

这些门是纯增量挂载：分镜没有登记 `- 武打：` 时一律不参与检查，所以本文件同时钉住
「不该响的时候不响」——既有稿件不会因为挂载而新报错。规则文字见
`short-drama-storyboard/references/fight-shot-budget.md` 与 `martial-action-library.md`，
判据见 `short-drama-review/references/rubric-fight-action.md`。
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_SPEC = importlib.util.spec_from_file_location(
    "creator_markdown_check",
    ROOT / "skills/short-drama/scripts/creator_markdown_check.py",
)
assert VALIDATOR_SPEC and VALIDATOR_SPEC.loader
validator = importlib.util.module_from_spec(VALIDATOR_SPEC)
sys.modules[VALIDATOR_SPEC.name] = validator
VALIDATOR_SPEC.loader.exec_module(validator)


def record(order, shot_id, scene, phase, stance, framing, exempt=False):
    return (
        order,
        shot_id,
        scene,
        {
            "phase": phase,
            "stance": stance,
            "weapon": "",
            "exempt": exempt,
        },
        framing,
    )


class FightMarkerParsingTests(unittest.TestCase):
    def parse(self, value):
        errors: list[str] = []
        parsed = validator._parse_fight_marker(value, "SHOT-EP001-001", errors)
        return parsed, errors

    def test_absent_field_opts_out_silently(self) -> None:
        parsed, errors = self.parse("")
        self.assertIsNone(parsed)
        self.assertEqual(errors, [])

    def test_full_marker_parses_three_parts(self) -> None:
        parsed, errors = self.parse("兵器·横刀 / 相位=接触瞬间 / 姿态=低桩")
        self.assertEqual(errors, [])
        self.assertEqual(
            parsed,
            {
                "phase": "接触瞬间",
                "stance": "低桩",
                "weapon": "横刀",
                "exempt": False,
            },
        )

    def test_empty_placeholder_is_rejected(self) -> None:
        parsed, errors = self.parse("无")
        self.assertIsNone(parsed)
        self.assertEqual(len(errors), 1)
        self.assertIn("空占位", errors[0])

    def test_half_written_marker_is_rejected_not_ignored(self) -> None:
        for value in (
            "兵器·长剑 / 姿态=低桩",
            "相位=收势",
            "相位=对攻 / 姿态=低桩",
            "相位=收势 / 姿态=坐姿",
        ):
            with self.subTest(value=value):
                parsed, errors = self.parse(value)
                self.assertIsNone(parsed)
                self.assertEqual(len(errors), 1)

    def test_bare_hands_does_not_demand_a_prop_entry(self) -> None:
        parsed, errors = self.parse("兵器·徒手 / 相位=起手 / 姿态=自由站姿")
        self.assertEqual(errors, [])
        self.assertEqual(parsed["weapon"], "")

    def test_exempt_token_is_carried_through(self) -> None:
        parsed, errors = self.parse("相位=接触瞬间 / 姿态=低桩 / 连相")
        self.assertEqual(errors, [])
        self.assertTrue(parsed["exempt"])

    def test_exempt_token_appended_to_the_last_part_still_parses(self) -> None:
        # 文档写的是"在这几行末尾追加 `连相`"，所以 `姿态=低桩 连相` 这种写法必须可用
        parsed, errors = self.parse("兵器·横刀 / 相位=起手 / 姿态=低桩 连相")
        self.assertEqual(errors, [])
        self.assertEqual(parsed["stance"], "低桩")
        self.assertTrue(parsed["exempt"])
        self.assertEqual(parsed["weapon"], "横刀")


class FightSceneShapeTests(unittest.TestCase):
    def run_gate(self, records):
        errors: list[str] = []
        validator._check_fight_scene_shape(list(records), errors)
        return errors

    def test_well_spread_exchange_is_silent(self) -> None:
        records = [
            record(0, "S1", "EP001-SC003", "起手", "低桩", "中景"),
            record(1, "S2", "EP001-SC003", "接触瞬间", "特写", "近景"),
            record(2, "S3", "EP001-SC003", "收势", "转身", "全景"),
            record(3, "S4", "EP001-SC003", "起手", "腾空", "远景"),
            record(4, "S5", "EP001-SC003", "接触瞬间", "低桩", "中近景"),
            record(5, "S6", "EP001-SC003", "收势", "转身", "近景"),
        ]
        self.assertEqual(self.run_gate(records), [])

    def test_three_identical_phases_fire_once(self) -> None:
        records = [
            record(0, "S1", "EP001-SC002", "起手", "低桩", "中景"),
            record(1, "S2", "EP001-SC002", "起手", "转身", "近景"),
            record(2, "S3", "EP001-SC002", "起手", "腾空", "全景"),
            record(3, "S4", "EP001-SC002", "接触瞬间", "低桩", "近景"),
            record(4, "S5", "EP001-SC002", "收势", "特写", "中景"),
            record(5, "S6", "EP001-SC002", "起手", "转身", "远景"),
        ]
        errors = self.run_gate(records)
        self.assertEqual(len(errors), 1)
        self.assertIn("连续三镜武打相位都是「起手」", errors[0])
        self.assertIn("连相", errors[0])

    def test_declared_exempt_run_is_silent(self) -> None:
        records = [
            record(0, "S1", "EP001-SC002", "起手", "低桩", "中景", exempt=True),
            record(1, "S2", "EP001-SC002", "起手", "转身", "近景", exempt=True),
            record(2, "S3", "EP001-SC002", "起手", "腾空", "全景", exempt=True),
            record(3, "S4", "EP001-SC002", "接触瞬间", "低桩", "近景", exempt=True),
        ]
        self.assertEqual(self.run_gate(records), [])

    def test_one_shot_size_over_eighty_percent_fire(self) -> None:
        records = [
            record(0, "S1", "EP001-SC005", "起手", "低桩", "中景"),
            record(1, "S2", "EP001-SC005", "接触瞬间", "特写", "中景"),
            record(2, "S3", "EP001-SC005", "收势", "转身", "中景"),
            record(3, "S4", "EP001-SC005", "起手", "腾空", "中景"),
            record(4, "S5", "EP001-SC005", "接触瞬间", "低桩", "中景"),
            record(5, "S6", "EP001-SC005", "收势", "转身", "近景"),
        ]
        errors = self.run_gate(records)
        self.assertEqual(len(errors), 1)
        self.assertIn("景别都写作「中景」", errors[0])

    def test_missing_stance_floor_fire(self) -> None:
        records = [
            record(i, f"S{i + 1}", "EP001-SC006", phase, "低桩", framing)
            for i, (phase, framing) in enumerate(
                [
                    ("起手", "中景"),
                    ("接触瞬间", "近景"),
                    ("收势", "全景"),
                    ("起手", "中近景"),
                    ("接触瞬间", "特写"),
                    ("收势", "中景"),
                ]
            )
        ]
        errors = self.run_gate(records)
        self.assertEqual(len(errors), 1)
        self.assertIn("完全没有", errors[0])
        self.assertIn("腾空", errors[0])

    def test_below_six_shots_distribution_stays_quiet(self) -> None:
        records = [
            record(0, "S1", "EP001-SC007", "起手", "低桩", "中景"),
            record(1, "S2", "EP001-SC007", "接触瞬间", "低桩", "中景"),
            record(2, "S3", "EP001-SC007", "收势", "低桩", "中景"),
            record(3, "S4", "EP001-SC007", "起手", "低桩", "中景"),
        ]
        self.assertEqual(self.run_gate(records), [])

    def test_missing_shot_size_skips_grouping_only(self) -> None:
        records = [
            record(0, "S1", "EP001-SC008", "起手", "低桩", ""),
            record(1, "S2", "EP001-SC008", "接触瞬间", "特写", ""),
            record(2, "S3", "EP001-SC008", "收势", "转身", ""),
            record(3, "S4", "EP001-SC008", "起手", "腾空", ""),
            record(4, "S5", "EP001-SC008", "接触瞬间", "低桩", ""),
            record(5, "S6", "EP001-SC008", "收势", "自由站姿", ""),
        ]
        self.assertEqual(self.run_gate(records), [])

    def test_entry_label_drops_bracket_qualifier(self) -> None:
        self.assertEqual(validator._entry_label("横刀（柄缠布）"), "横刀")


class FightRelayTests(unittest.TestCase):
    """`- 接力：` 只校写法：没写即沉默，写了就要能被下一镜接住。"""

    def parse(self, value):
        errors: list[str] = []
        count = validator._parse_fight_relay(value, "SHOT-EP001-002", errors)
        return count, errors

    def test_absent_field_is_silent(self) -> None:
        count, errors = self.parse("")
        self.assertEqual(count, 0)
        self.assertEqual(errors, [])

    def test_four_items_pass(self) -> None:
        count, errors = self.parse(
            "姿态=右脚在前 / 运动=向画面左退 / 器械=横刀出鞘、刀背有缺口 / 攻防权=对方"
        )
        self.assertEqual(errors, [])
        self.assertEqual(count, 4)

    def test_all_seven_items_pass(self) -> None:
        count, errors = self.parse(
            "姿态=低桩 / 运动=前冲 / 高度=地面 / 器械=长枪扎老 / 攻防权=我方 /"
            " 摄影机=手持右跟 / 余波=瓦屑仍在落"
        )
        self.assertEqual(errors, [])
        self.assertEqual(count, 7)

    def test_placeholder_is_rejected(self) -> None:
        count, errors = self.parse("无")
        self.assertEqual(count, 0)
        self.assertEqual(len(errors), 1)
        self.assertIn("空占位", errors[0])

    def test_unregistered_dimension_is_rejected(self) -> None:
        count, errors = self.parse(
            "姿态=低桩 / 心情=愤怒 / 器械=刀 / 攻防权=对方"
        )
        self.assertIn("心情", errors[0])
        self.assertEqual(count, 3)

    def test_empty_value_is_rejected(self) -> None:
        count, errors = self.parse("姿态= / 运动=后退 / 器械=刀 / 攻防权=对方")
        self.assertTrue(any("没有内容" in error for error in errors), errors)
        self.assertEqual(count, 3)

    def test_below_minimum_is_reported_with_filled_names(self) -> None:
        count, errors = self.parse("姿态=低桩 / 器械=横刀")
        self.assertEqual(count, 2)
        self.assertEqual(len(errors), 1)
        self.assertIn("只填了 2 项", errors[0])
        self.assertIn("沿用上一镜", errors[0])

    def test_no_dimensions_at_all_is_rejected(self) -> None:
        count, errors = self.parse("照上一镜继续")
        self.assertEqual(count, 0)
        self.assertEqual(len(errors), 1)
        self.assertIn("没有写出任何", errors[0])


class FightEpisodeAggregationTests(unittest.TestCase):
    """分布门按全集聚合，相位连续仍按场——《针与剑》EP001 实测出来的口径修正。"""

    def run_gate(self, records):
        errors: list[str] = []
        validator._check_fight_scene_shape(list(records), errors)
        return errors

    def test_distribution_counts_across_scenes(self) -> None:
        records = [
            record(0, "S1", "EP001-SC001", "起手", "低桩", "中景"),
            record(1, "S2", "EP001-SC001", "接触瞬间", "特写", "中景"),
            record(2, "S3", "EP001-SC001", "收势", "转身", "中景"),
            record(3, "S4", "EP001-SC002", "起手", "腾空", "中景"),
            record(4, "S5", "EP001-SC002", "接触瞬间", "低桩", "中景"),
            record(5, "S6", "EP001-SC002", "收势", "转身", "中景"),
        ]
        errors = self.run_gate(records)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("本集武打镜 6 镜", errors[0])
        self.assertIn("景别都写作「中景」", errors[0])

    def test_phase_run_does_not_cross_scene_boundary(self) -> None:
        records = [
            record(0, "S1", "EP001-SC001", "起手", "低桩", "中景"),
            record(1, "S2", "EP001-SC001", "接触瞬间", "特写", "近景"),
            record(2, "S3", "EP001-SC001", "起手", "转身", "全景"),
            record(3, "S4", "EP001-SC002", "起手", "腾空", "远景"),
            record(4, "S5", "EP001-SC002", "收势", "低桩", "中近景"),
            record(5, "S6", "EP001-SC002", "接触瞬间", "特写", "特写"),
        ]
        self.assertEqual(self.run_gate(records), [])


class FramingBucketTests(unittest.TestCase):
    """复合景别标签归并到主景别档，否则扎堆测不出来。"""

    def test_first_mentioned_band_wins(self) -> None:
        cases = {
            "中景带纵深，机位低": "中景",
            "特写偏中景": "特写",
            "仰角中远景": "中远景",
            "中近景正反打": "中近景",
            "大全景偏低机位": "大全景",
            "低机位中景": "中景",
        }
        for label, expected in cases.items():
            with self.subTest(label=label):
                self.assertEqual(validator._framing_bucket(label), expected)

    def test_unrecognised_label_is_kept(self) -> None:
        self.assertEqual(validator._framing_bucket("侧面，过肩"), "侧面")


if __name__ == "__main__":
    unittest.main()
