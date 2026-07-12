import { AttackFamily, RiskLevel } from './constants';

// 攻击族配色
export const attackFamilyColor: Record<AttackFamily, string> = {
  [AttackFamily.PROMPT_INJECTION]: '#1677ff',
  [AttackFamily.JAILBREAK]: '#fa8c16',
  [AttackFamily.ENCODING_OBFUSCATION]: '#722ed1',
  [AttackFamily.ZERO_WIDTH]: '#8c8c8c',
  [AttackFamily.CONTEXT_ESCALATION]: '#eb2f96',
  [AttackFamily.PII_LEAKAGE]: '#f5222d',
  [AttackFamily.TOOL_MISUSE]: '#d4380d',
  [AttackFamily.MULTI_TURN_COMPOSITE]: '#531dab',
  [AttackFamily.PAYLOAD_SPLIT]: '#c41d7f',
  [AttackFamily.RAG_POISONING]: '#13c2c2',
  [AttackFamily.MEMORY_POISONING]: '#2f54eb',
  [AttackFamily.TOOL_OUTPUT_POISONING]: '#faad14',
  [AttackFamily.SKILL_MCP_POISONING]: '#a0d911',
  [AttackFamily.CHAIN_OF_THOUGHT_ATTACK]: '#52c41a',
  [AttackFamily.OPINION_POISONING]: '#f5222d',
  [AttackFamily.MULTI_AGENT_POISONING]: '#08979c',
  [AttackFamily.SUPPLY_CHAIN]: '#fa541c',
};

// 风险等级配色
export const riskLevelColor: Record<RiskLevel, string> = {
  [RiskLevel.LEVEL_1]: '#52c41a',
  [RiskLevel.LEVEL_2]: '#bae637',
  [RiskLevel.LEVEL_3]: '#faad14',
  [RiskLevel.LEVEL_4]: '#fa8c16',
  [RiskLevel.LEVEL_5]: '#f5222d',
};

// 实验状态配色
export const experimentStatusColor: Record<string, string> = {
  draft: '#d9d9d9',
  pending: '#1677ff',
  running: '#faad14',
  completed: '#52c41a',
  failed: '#f5222d',
  stopped: '#fa8c16',
};

// 防御层配色 (L1→L5: 青→蓝→绿→橙→紫)
export const defenseLayerColor: Record<string, string> = {
  source_governance: '#13c2c2',
  model_interaction: '#1677ff',
  memory_control: '#52c41a',
  tool_constraint: '#fa8c16',
  decision_supervision: '#722ed1',
};
