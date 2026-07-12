# Agent Chain Poison 合并实验报告

## 1. 合并概览

- 源 CSV 文件数: **18**
- 原始记录数: **655**
- 去重后样本数: **100**
- 有效样本数: **100**
- 失败样本数: **0**
- 总 strict_success_rate: **33.00%**
- reasoning_shift_rate: **49.00%**
- decision_shift_rate: **8.00%**
- risk_downgrade_rate: **7.00%**
- autonomous_action_rate: **9.00%**

## 2. 源文件列表

- `agent_chain_poison_20260608_231105_254a92ae.csv`
- `agent_chain_poison_20260608_231105_870968d0.csv`
- `agent_chain_poison_20260608_231115_ac3d40a6.csv`
- `agent_chain_poison_20260608_231448_58e5f90d.csv`
- `agent_chain_poison_20260608_231459_497c3565.csv`
- `agent_chain_poison_20260608_231517_45436197.csv`
- `agent_chain_poison_20260608_232559_72f0dad1.csv`
- `agent_chain_poison_20260608_232832_fee179c1.csv`
- `agent_chain_poison_20260608_232934_af3115b4.csv`
- `agent_chain_poison_20260608_233204_52c8c64b.csv`
- `agent_chain_poison_20260609_000821_0cf95f21.csv`
- `agent_chain_poison_20260609_003828_2f4af2ca.csv`
- `agent_chain_poison_20260609_003943_72403c3c.csv`
- `agent_chain_poison_20260609_005457_89d7aef1.csv`
- `agent_chain_poison_20260609_005922_37de611a.csv`
- `agent_chain_poison_20260609_010503_a1eb3ebe.csv`
- `agent_chain_poison_20260609_010945_7cc472a7.csv`
- `agent_chain_poison_20260609_011647_97714ab7.csv`

## 3. 按 poison_type 分组统计

| poison_type | total | reasoning_shift | decision_shift | risk_downgrade | autonomous_action | strict_success |
|---|---:|---:|---:|---:|---:|---:|
| autonomous_action_drift | 20 | 45.00% | 0.00% | 0.00% | 45.00% | 95.00% |
| evidence_suppression | 20 | 30.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| logical_rule_injection | 20 | 65.00% | 35.00% | 35.00% | 0.00% | 35.00% |
| priority_shift_injection | 20 | 45.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| step_order_hijack | 20 | 60.00% | 5.00% | 0.00% | 0.00% | 35.00% |
