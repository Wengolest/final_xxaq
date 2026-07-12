# ============================================================
# 测试: L5 决策监督与多源验证
# ============================================================

import time
from defense_types import DefenseContext, DefenseLayer, LayerCheckResult
from layer5_decision_supervision import DecisionSupervision


# ---- 辅助 ----

def make_ctx(content="test content", source="user_input", trust_level=1.0):
    return DefenseContext(content=content, source=source, trust_level=trust_level)


def make_layer_result(layer, passed=True, action="pass", risk_score=0.0, flags=None):
    return LayerCheckResult(
        layer=layer,
        passed=passed,
        action=action,
        risk_score=risk_score,
        flags=flags or [],
        trust_level=1.0 - risk_score,
    )


# ---- 初始化 ----

def test_d5_initialization():
    ds = DecisionSupervision()
    assert ds.audit_threshold == 0.7
    assert ds.consecutive_block_max == 3
    assert ds.high_risk_window == 10


def test_d5_custom_params():
    ds = DecisionSupervision({
        "audit_threshold": 0.5,
        "consecutive_block_max": 5,
    })
    assert ds.audit_threshold == 0.5
    assert ds.consecutive_block_max == 5


# ---- 熔断机制 ----

def test_circuit_breaker_normal():
    ds = DecisionSupervision()
    c = ds._check_circuit_breaker()
    assert c.severity == "pass"


def test_circuit_breaker_triggers():
    ds = DecisionSupervision()
    ds._consecutive_blocks = 3
    c = ds._check_circuit_breaker()
    assert c.severity == "block"
    assert ds._circuit_open


def test_circuit_breaker_open():
    ds = DecisionSupervision()
    ds._circuit_open = True
    ds._circuit_until = time.time() + 30
    c = ds._check_circuit_breaker()
    assert c.severity == "block"
    assert "熔断器开启中" in c.description


def test_circuit_breaker_recovery():
    ds = DecisionSupervision()
    ds._circuit_open = True
    ds._circuit_until = time.time() - 1  # already passed
    c = ds._check_circuit_breaker()
    assert c.severity == "warn"  # 半开状态
    assert not ds._circuit_open


# ---- 多源交叉验证 ----

def test_cross_validation_consensus_pass():
    ds = DecisionSupervision()
    ctx = make_ctx()
    prior = {
        "source_governance": make_layer_result(DefenseLayer.SOURCE_GOVERNANCE),
        "model_interaction": make_layer_result(DefenseLayer.MODEL_INTERACTION),
    }
    c = ds._check_cross_validation(ctx, prior)
    assert c.severity == "pass"


def test_cross_validation_consensus_block():
    ds = DecisionSupervision()
    ctx = make_ctx()
    prior = {
        "l1": make_layer_result(DefenseLayer.SOURCE_GOVERNANCE, action="block", risk_score=0.3),
        "l2": make_layer_result(DefenseLayer.MODEL_INTERACTION, action="block", risk_score=0.3),
    }
    c = ds._check_cross_validation(ctx, prior)
    assert c.severity == "block"


def test_cross_validation_split_opinion():
    ds = DecisionSupervision()
    ctx = make_ctx()
    prior = {
        "l1": make_layer_result(DefenseLayer.SOURCE_GOVERNANCE, action="block"),
        "l2": make_layer_result(DefenseLayer.MODEL_INTERACTION, action="pass"),
    }
    c = ds._check_cross_validation(ctx, prior)
    assert c.severity == "warn"
    assert "意见分裂" in c.description


def test_cross_validation_insufficient_layers():
    ds = DecisionSupervision()
    ctx = make_ctx()
    prior = {
        "l1": make_layer_result(DefenseLayer.SOURCE_GOVERNANCE),
    }
    c = ds._check_cross_validation(ctx, prior)
    assert c.severity == "pass"


# ---- 审计复核 ----

def test_audit_high_risk():
    ds = DecisionSupervision()
    c = ds._check_audit(0.85, 2, 1)
    assert c.severity == "block"


def test_audit_medium_risk():
    ds = DecisionSupervision()
    c = ds._check_audit(0.55, 0, 2)
    assert c.severity == "warn"
    assert "接近" in c.description


def test_audit_low_risk():
    ds = DecisionSupervision()
    c = ds._check_audit(0.1, 0, 0)
    assert c.severity == "pass"


# ---- 异常检测 ----

def test_anomaly_high_risk_ratio():
    ds = DecisionSupervision()
    # Populate recent history with blocks
    for _ in range(8):
        ds._recent_decisions.append({"risk_score": 0.9, "action": "block", "flag_types": []})
    ds._recent_decisions.append({"risk_score": 0.1, "action": "pass", "flag_types": []})
    ds._recent_decisions.append({"risk_score": 0.1, "action": "pass", "flag_types": []})
    c = ds._check_anomaly(0, 0, [])
    assert c.severity == "warn"


def test_anomaly_normal():
    ds = DecisionSupervision()
    for _ in range(5):
        ds._recent_decisions.append({"risk_score": 0.1, "action": "pass", "flag_types": []})
    c = ds._check_anomaly(0, 0, [])
    assert c.severity == "pass"


# ---- 最终仲裁 ----

def test_final_arbitration_pass():
    ds = DecisionSupervision()
    c = ds._check_final_arbitration(0.1, 0)
    assert c.severity == "pass"


def test_final_arbitration_block_multi_layers():
    ds = DecisionSupervision()
    c = ds._check_final_arbitration(0.4, 2)
    assert c.severity == "block"


def test_final_arbitration_block_high_risk():
    ds = DecisionSupervision()
    c = ds._check_final_arbitration(0.8, 0)
    assert c.severity == "block"


def test_final_arbitration_warn():
    ds = DecisionSupervision()
    c = ds._check_final_arbitration(0.35, 0)
    assert c.severity == "warn"


def test_final_arbitration_circuit_open():
    ds = DecisionSupervision()
    ds._circuit_open = True
    c = ds._check_final_arbitration(0.0, 0)
    assert c.severity == "block"


# ---- evaluate() 集成 ----

def test_evaluate_normal():
    ds = DecisionSupervision()
    ctx = make_ctx("normal content")
    prior = {
        "source_governance": make_layer_result(DefenseLayer.SOURCE_GOVERNANCE),
        "model_interaction": make_layer_result(DefenseLayer.MODEL_INTERACTION),
        "tool_constraint": make_layer_result(DefenseLayer.TOOL_CONSTRAINT),
    }
    result = ds.evaluate(ctx, prior_layer_results=prior)
    assert result.passed
    assert result.risk_score == 0.0


def test_evaluate_with_prior_blocks():
    ds = DecisionSupervision()
    ctx = make_ctx("dangerous content")
    prior = {
        "l1": make_layer_result(DefenseLayer.SOURCE_GOVERNANCE,
                                action="block", risk_score=0.3,
                                flags=["[SG-zero_width_char] detected"]),
        "l2": make_layer_result(DefenseLayer.MODEL_INTERACTION,
                                action="block", risk_score=0.3,
                                flags=["[MI-sensitive_behavior] jailbreak"]),
        "l3": make_layer_result(DefenseLayer.MEMORY_CONTROL, action="pass"),
        "l4": make_layer_result(DefenseLayer.TOOL_CONSTRAINT, action="pass"),
    }
    result = ds.evaluate(ctx, prior_layer_results=prior)
    assert not result.passed
    assert result.action == "block"
    assert result.risk_score > 0.3


def test_evaluate_with_engine():
    from rule_engine import RuleEngine
    engine = RuleEngine([
        {
            "rule_id": "DS001",
            "name": "multi_source_conflict",
            "enabled": True,
            "action": "warn",
            "priority": 1,
            "pattern_type": "condition",
            "pattern": "",
            "condition": "source_weight_divergence > 0.2",
            "target_fields": ["content"],
        },
    ])
    ds = DecisionSupervision()
    ctx = make_ctx("conflicting info")
    prior = {
        "l1": make_layer_result(DefenseLayer.SOURCE_GOVERNANCE,
                                action="block", risk_score=0.35),
        "l2": make_layer_result(DefenseLayer.MODEL_INTERACTION, action="pass"),
    }
    result = ds.evaluate(ctx, engine, prior_layer_results=prior)
    # Should have both programmatic and rule-based flags
    assert result.risk_score > 0


# ---- 状态管理 ----

def test_consecutive_blocks_tracking():
    ds = DecisionSupervision()
    # Simulate a sequence of evaluations with blocks
    for i in range(4):
        prior = {
            "l1": make_layer_result(
                DefenseLayer.SOURCE_GOVERNANCE,
                action="block" if i < 4 else "pass",
                risk_score=0.3,
            ),
        }
        ctx = make_ctx(f"attack_{i}")
        ctx.run_id = f"run_{i}"
        result = ds.evaluate(ctx, prior_layer_results=prior)

    # After 3 consecutive blocks, circuit should open
    assert ds._circuit_open or ds._consecutive_blocks >= 3


def test_high_risk_ratio_calculation():
    ds = DecisionSupervision()
    assert ds._get_high_risk_ratio() == 0.0
    ds._recent_decisions.append({"risk_score": 0.9, "action": "block", "flag_types": []})
    ds._recent_decisions.append({"risk_score": 0.1, "action": "pass", "flag_types": []})
    assert ds._get_high_risk_ratio() == 0.5


# ---- 日志/状态查询 ----

def test_audit_log_records():
    ds = DecisionSupervision()
    ctx = make_ctx("test")
    ctx.run_id = "run_test"
    prior = {
        "l1": make_layer_result(DefenseLayer.SOURCE_GOVERNANCE, action="block", risk_score=0.5),
    }
    ds.evaluate(ctx, prior_layer_results=prior)
    log = ds.get_audit_log()
    assert len(log) >= 1
    assert log[-1]["run_id"] == "run_test"


def test_get_state():
    ds = DecisionSupervision()
    state = ds.get_state()
    assert "circuit_open" in state
    assert "consecutive_blocks" in state
    assert "high_risk_ratio" in state
    assert "total_audits" in state


def test_reset_state():
    ds = DecisionSupervision()
    ds._consecutive_blocks = 5
    ds._recent_decisions.append({"risk_score": 0.9, "action": "block", "flag_types": []})
    ds.reset_state()
    assert ds._consecutive_blocks == 0
    assert len(ds._recent_decisions) == 0
    assert not ds._circuit_open
