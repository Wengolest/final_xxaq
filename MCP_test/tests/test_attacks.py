"""
攻击样本库单元测试（替代已删除的 data_exfiltration / tool_hijacking 模块）。
"""

import pytest

from src.attacks.samples import collect_all_samples


class TestAttackSamples:
    """验证 50 条样本 catalog 基本完整性。"""

    def test_sample_count(self):
        samples = collect_all_samples()
        assert len(samples) >= 50

    def test_unique_ids(self):
        samples = collect_all_samples()
        ids = [s.id for s in samples]
        assert len(ids) == len(set(ids))

    def test_payload_has_poison_tool(self):
        samples = collect_all_samples()
        for s in samples[:5]:
            p = s.to_payload()
            assert "tool" in p
            assert p["tool"].get("name")
            assert p["tool"].get("description")

    def test_paradigms_present(self):
        samples = collect_all_samples()
        paradigms = {s.paradigm for s in samples}
        assert "P1" in paradigms
        assert "P2" in paradigms
