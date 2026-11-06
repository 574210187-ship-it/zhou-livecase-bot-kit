from __future__ import annotations

import copy
import unittest

from zhou_livecase.providers.human_readability import validate_visible_payload


def valid_payload():
    quote = "我今年三十五岁，和丈夫结婚十年，他最近总是回避沟通。"
    return {
        "schema": "zhou-visible-payload-v1",
        "source_identity": {"record_id": "source-001", "recording_name": "录屏样例-P001.mp4"},
        "source_text": "主持人：你好。\n来访者：" + quote + "\n主持人：先把具体事实说清楚。",
        "boundaries": [
            {
                "boundary_id": "source-001-call-001",
                "source_identity": {"record_id": "source-001", "recording_name": "录屏样例-P001.mp4"},
                "cells": {
                    "故事标题": "结婚十年后丈夫持续回避沟通",
                    "故事概要": "一名三十五岁的妻子发现丈夫近期持续回避沟通，希望厘清关系中的真实问题。",
                    "主方向": "婚姻沟通",
                    "次方向": "关系边界",
                    "看事索引": "长期婚姻中的沟通回避与关系判断",
                    "单麦作用及依据": "用具体婚龄和沟通变化呈现长期关系中的失衡。",
                    "可借鉴元素": "先核对婚龄和近期行为变化，再讨论关系选择。",
                    "禁借元素": "不能把回避沟通直接断言为婚外关系。",
                },
                "evidence": [{"claim": "当事人三十五岁并已结婚十年", "quote": quote, "turn_id": "t1"}],
            }
        ],
    }


class HumanReadabilityTests(unittest.TestCase):
    def test_valid_payload_passes(self) -> None:
        result = validate_visible_payload(valid_payload())
        self.assertTrue(result["passed"], result["issues"])

    def test_internal_code_is_rejected(self) -> None:
        value = valid_payload()
        value["boundaries"][0]["cells"]["故事概要"] = "blocked_model 等待处理"
        result = validate_visible_payload(value)
        self.assertIn("VISIBLE_FIELD_INTERNAL_CODE", {item["code"] for item in result["issues"]})

    def test_placeholder_template_is_rejected(self) -> None:
        value = valid_payload()
        value["boundaries"][0]["cells"]["单麦作用及依据"] = "作用：普通案例麦"
        result = validate_visible_payload(value)
        self.assertIn("VISIBLE_FIELD_INTERNAL_CODE", {item["code"] for item in result["issues"]})

    def test_non_verbatim_quote_is_rejected(self) -> None:
        value = valid_payload()
        value["boundaries"][0]["evidence"][0]["quote"] = "这句并不存在于原稿"
        result = validate_visible_payload(value)
        self.assertIn("EVIDENCE_NOT_VERBATIM", {item["code"] for item in result["issues"]})

    def test_unsupported_numeric_fact_is_rejected(self) -> None:
        value = valid_payload()
        value["boundaries"][0]["evidence"][0]["claim"] = "当事人四十岁并已结婚十年"
        result = validate_visible_payload(value)
        self.assertIn("CLAIM_FACT_UNSUPPORTED", {item["code"] for item in result["issues"]})

    def test_source_identity_mismatch_is_rejected(self) -> None:
        value = valid_payload()
        value["boundaries"][0]["source_identity"]["recording_name"] = "另一场录屏.mp4"
        result = validate_visible_payload(value)
        self.assertIn("SOURCE_IDENTITY_MISMATCH", {item["code"] for item in result["issues"]})

    def test_all_eight_visible_fields_are_required(self) -> None:
        value = valid_payload()
        del value["boundaries"][0]["cells"]["看事索引"]
        result = validate_visible_payload(value)
        self.assertIn("VISIBLE_FIELD_EMPTY", {item["code"] for item in result["issues"]})


if __name__ == "__main__":
    unittest.main()
