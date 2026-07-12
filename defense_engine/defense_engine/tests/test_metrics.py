# ============================================================
# 测试: 防御指标引擎
# ============================================================

from metrics import DefenseMetrics, MetricsSummary, MetricRecord


# ---- 辅助 ----

class FakeResult:
    """模拟 DefenseTestResult"""
    def __init__(self, passed=True, final_action="passed", risk_score=0.0,
                 layer_results=None, processing_time_ms=1.0):
        self.passed = passed
        self.final_action = final_action
        self.risk_score = risk_score
        self.layer_results = layer_results or {}
        self.processing_time_ms = processing_time_ms


def make_passed():
    return FakeResult(passed=True, final_action="passed", risk_score=0.0,
                      layer_results={
                          "source_governance": {"passed": True, "flags": [], "matched_rules": []},
                          "model_interaction": {"passed": True, "flags": [], "matched_rules": []},
                          "memory_control": {"passed": True, "flags": [], "matched_rules": []},
                          "tool_constraint": {"passed": True, "flags": [], "matched_rules": []},
                          "decision_supervision": {"passed": True, "flags": [], "matched_rules": []},
                      })


def make_blocked(blocking_layer="source_governance", rule_id="SG001"):
    layers = {
        "source_governance": {"passed": True, "flags": [], "matched_rules": []},
        "model_interaction": {"passed": True, "flags": [], "matched_rules": []},
        "memory_control": {"passed": True, "flags": [], "matched_rules": []},
        "tool_constraint": {"passed": True, "flags": [], "matched_rules": []},
        "decision_supervision": {"passed": True, "flags": [], "matched_rules": []},
    }
    layers[blocking_layer] = {
        "passed": False, "flags": [f"[{rule_id}] blocked"],
        "matched_rules": [rule_id],
    }
    return FakeResult(passed=False, final_action="blocked", risk_score=0.4,
                      layer_results=layers)


# ---- 记录 ----

def test_metrics_record_attack():
    m = DefenseMetrics()
    m.record(make_blocked(), is_attack=True, attack_family="prompt_injection")
    assert m.total == 1


def test_metrics_record_benign():
    m = DefenseMetrics()
    m.record(make_passed(), is_attack=False)
    assert m.total == 1


def test_metrics_record_verdict():
    m = DefenseMetrics()
    m.record_verdict("blocked", risk_score=0.5, is_attack=True,
                     attack_family="jailbreak", blocking_layer="model_interaction")
    assert m.total == 1


# ---- DSR (Defense Success Rate) ----

def test_dsr_perfect():
    m = DefenseMetrics()
    for _ in range(10):
        m.record(make_blocked(), is_attack=True, attack_family="prompt_injection")
    s = m.summary()
    assert s.dsr == 1.0


def test_dsr_zero():
    m = DefenseMetrics()
    for _ in range(10):
        m.record(make_passed(), is_attack=True, attack_family="prompt_injection")
    s = m.summary()
    assert s.dsr == 0.0


def test_dsr_mixed():
    m = DefenseMetrics()
    for _ in range(5):
        m.record(make_blocked(), is_attack=True, attack_family="prompt_injection")
    for _ in range(5):
        m.record(make_passed(), is_attack=True, attack_family="prompt_injection")
    s = m.summary()
    assert s.dsr == 0.5


# ---- FPR (False Positive Rate) ----

def test_fpr_zero():
    m = DefenseMetrics()
    for _ in range(10):
        m.record(make_passed(), is_attack=False)
    s = m.summary()
    assert s.fpr == 0.0


def test_fpr_with_false_positives():
    m = DefenseMetrics()
    for _ in range(5):
        m.record(make_passed(), is_attack=False)
    for _ in range(5):
        m.record(make_blocked(), is_attack=False)
    s = m.summary()
    assert s.fpr == 0.5


# ---- FNR (False Negative Rate) ----

def test_fnr_zero():
    m = DefenseMetrics()
    for _ in range(10):
        m.record(make_blocked(), is_attack=True, attack_family="jailbreak")
    s = m.summary()
    assert s.fnr == 0.0


def test_fnr_with_misses():
    m = DefenseMetrics()
    for _ in range(7):
        m.record(make_blocked(), is_attack=True, attack_family="jailbreak")
    for _ in range(3):
        m.record(make_passed(), is_attack=True, attack_family="jailbreak")
    s = m.summary()
    assert s.fnr == 0.3


# ---- 层拦截率 ----

def test_layer_intercept_rates():
    m = DefenseMetrics()
    m.record(make_blocked("source_governance"), is_attack=True)
    m.record(make_blocked("tool_constraint"), is_attack=True)
    m.record(make_passed(), is_attack=True)
    m.record(make_passed(), is_attack=False)
    rates = m.layer_intercept_rates()
    assert "source_governance" in rates
    assert "tool_constraint" in rates


# ---- 规则命中分布 ----

def test_rule_hit_distribution():
    m = DefenseMetrics()
    m.record(make_blocked("source_governance", "SG001"), is_attack=True)
    m.record(make_blocked("source_governance", "SG002"), is_attack=True)
    m.record(make_blocked("source_governance", "SG001"), is_attack=True)
    dist = m.rule_hit_distribution()
    assert dist.get("SG001") == 2
    assert dist.get("SG002") == 1


# ---- 攻击族 DSR ----

def test_attack_family_dsr():
    m = DefenseMetrics()
    m.record(make_blocked(), is_attack=True, attack_family="prompt_injection")
    m.record(make_blocked(), is_attack=True, attack_family="prompt_injection")
    m.record(make_passed(), is_attack=True, attack_family="jailbreak")
    m.record(make_blocked(), is_attack=True, attack_family="jailbreak")
    family_dsr = m.attack_family_dsr()
    assert family_dsr["prompt_injection"] == 1.0
    assert family_dsr["jailbreak"] == 0.5


# ---- 混淆矩阵 ----

def test_confusion_matrix():
    m = DefenseMetrics()
    # TP: attack blocked
    m.record(make_blocked(), is_attack=True, attack_family="injection")
    m.record(make_blocked(), is_attack=True, attack_family="injection")
    # FN: attack passed
    m.record(make_passed(), is_attack=True, attack_family="injection")
    # TN: benign passed
    m.record(make_passed(), is_attack=False)
    m.record(make_passed(), is_attack=False)
    m.record(make_passed(), is_attack=False)
    # FP: benign blocked
    m.record(make_blocked(), is_attack=False)

    cm = m.get_confusion_matrix()
    assert cm["true_positive"] == 2
    assert cm["false_negative"] == 1
    assert cm["true_negative"] == 3
    assert cm["false_positive"] == 1
    assert cm["accuracy"] == 5/7
    assert cm["precision"] == 2/3
    assert cm["recall"] == 2/3


# ---- 延迟统计 ----

def test_latency_stats():
    m = DefenseMetrics()
    for ms in [1.0, 2.0, 3.0, 4.0, 5.0]:
        r = make_blocked()
        r.processing_time_ms = ms
        m.record(r, is_attack=True)
    s = m.summary()
    assert s.avg_latency_ms == 3.0
    assert s.p50_latency_ms == 3.0


# ---- reset ----

def test_metrics_reset():
    m = DefenseMetrics()
    m.record(make_blocked(), is_attack=True)
    m.reset()
    assert m.total == 0


# ---- print_report ----

def test_print_report_no_crash():
    m = DefenseMetrics()
    m.record(make_blocked(), is_attack=True, attack_family="prompt_injection")
    m.record(make_passed(), is_attack=False)
    m.print_report()  # 不应崩溃


# ---- get_records ----

def test_get_records_limit():
    m = DefenseMetrics()
    for i in range(20):
        m.record(make_blocked() if i % 2 == 0 else make_passed(),
                 is_attack=(i % 2 == 0))
    records = m.get_records(limit=5)
    assert len(records) == 5


# ---- empty summary ----

def test_empty_summary():
    m = DefenseMetrics()
    s = m.summary()
    assert s.total_samples == 0
    assert s.dsr == 0.0
    assert s.fpr == 0.0
    assert s.fnr == 0.0
