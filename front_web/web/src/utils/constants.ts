// ============================================================
// 攻击族类型（对应文档第310-323行 攻击分类体系）
// ============================================================

export enum AttackFamily {
  // 直接输入类
  PROMPT_INJECTION = 'prompt_injection',       // 直接提示注入
  JAILBREAK = 'jailbreak',                     // 越狱改写
  ENCODING_OBFUSCATION = 'encoding_obfuscation', // 编码混淆
  ZERO_WIDTH = 'zero_width',                   // 零宽字符
  CONTEXT_ESCALATION = 'context_escalation',   // 上下文越权
  PII_LEAKAGE = 'pii_leakage',                 // PII泄露
  TOOL_MISUSE = 'tool_misuse',                 // 工具滥用
  MULTI_TURN_COMPOSITE = 'multi_turn_composite', // 复合攻击
  PAYLOAD_SPLIT = 'payload_split',             // 负载拆分
  // 环境/供应链式投毒
  RAG_POISONING = 'rag_poisoning',             // RAG文档投毒
  MEMORY_POISONING = 'memory_poisoning',       // 长期记忆投毒
  TOOL_OUTPUT_POISONING = 'tool_output_poisoning', // 工具输出投毒
  SKILL_MCP_POISONING = 'skill_mcp_poisoning', // Skill/MCP投毒
  // 推理与规划
  CHAIN_OF_THOUGHT_ATTACK = 'chain_of_thought_attack', // 推理/规划投毒
  // 舆论与信念
  OPINION_POISONING = 'opinion_poisoning',     // 舆论/信念投毒
  // 多智能体
  MULTI_AGENT_POISONING = 'multi_agent_poisoning', // 多智能体投毒
  // 供应链
  SUPPLY_CHAIN = 'supply_chain',               // 工具/协议供应链攻击
}

export const AttackFamilyLabel: Record<AttackFamily, string> = {
  [AttackFamily.PROMPT_INJECTION]: '直接提示注入',
  [AttackFamily.JAILBREAK]: '越狱改写',
  [AttackFamily.ENCODING_OBFUSCATION]: '编码混淆',
  [AttackFamily.ZERO_WIDTH]: '零宽字符',
  [AttackFamily.CONTEXT_ESCALATION]: '上下文越权',
  [AttackFamily.PII_LEAKAGE]: 'PII泄露',
  [AttackFamily.TOOL_MISUSE]: '工具滥用',
  [AttackFamily.MULTI_TURN_COMPOSITE]: '复合攻击',
  [AttackFamily.PAYLOAD_SPLIT]: '负载拆分',
  [AttackFamily.RAG_POISONING]: 'RAG文档投毒',
  [AttackFamily.MEMORY_POISONING]: '长期记忆投毒',
  [AttackFamily.TOOL_OUTPUT_POISONING]: '工具输出投毒',
  [AttackFamily.SKILL_MCP_POISONING]: 'Skill/MCP投毒',
  [AttackFamily.CHAIN_OF_THOUGHT_ATTACK]: '推理/规划投毒',
  [AttackFamily.OPINION_POISONING]: '舆论/信念投毒',
  [AttackFamily.MULTI_AGENT_POISONING]: '多智能体投毒',
  [AttackFamily.SUPPLY_CHAIN]: '工具/协议供应链攻击',
};

// 攻击一级分类
export enum AttackCategory {
  DIRECT_INPUT = 'direct_input',           // 直接输入类
  ENVIRONMENTAL = 'environmental',         // 环境/供应链式投毒
}

export const AttackFamilyCategory: Record<AttackFamily, AttackCategory> = {
  [AttackFamily.PROMPT_INJECTION]: AttackCategory.DIRECT_INPUT,
  [AttackFamily.JAILBREAK]: AttackCategory.DIRECT_INPUT,
  [AttackFamily.ENCODING_OBFUSCATION]: AttackCategory.DIRECT_INPUT,
  [AttackFamily.ZERO_WIDTH]: AttackCategory.DIRECT_INPUT,
  [AttackFamily.CONTEXT_ESCALATION]: AttackCategory.DIRECT_INPUT,
  [AttackFamily.PII_LEAKAGE]: AttackCategory.DIRECT_INPUT,
  [AttackFamily.TOOL_MISUSE]: AttackCategory.DIRECT_INPUT,
  [AttackFamily.MULTI_TURN_COMPOSITE]: AttackCategory.DIRECT_INPUT,
  [AttackFamily.PAYLOAD_SPLIT]: AttackCategory.DIRECT_INPUT,
  [AttackFamily.RAG_POISONING]: AttackCategory.ENVIRONMENTAL,
  [AttackFamily.MEMORY_POISONING]: AttackCategory.ENVIRONMENTAL,
  [AttackFamily.TOOL_OUTPUT_POISONING]: AttackCategory.ENVIRONMENTAL,
  [AttackFamily.SKILL_MCP_POISONING]: AttackCategory.ENVIRONMENTAL,
  [AttackFamily.CHAIN_OF_THOUGHT_ATTACK]: AttackCategory.ENVIRONMENTAL,
  [AttackFamily.OPINION_POISONING]: AttackCategory.ENVIRONMENTAL,
  [AttackFamily.MULTI_AGENT_POISONING]: AttackCategory.ENVIRONMENTAL,
  [AttackFamily.SUPPLY_CHAIN]: AttackCategory.ENVIRONMENTAL,
};

// 攻击严重级别（对应文档第181行 Risk Score公式）
export enum RiskLevel {
  LEVEL_1 = 1, // 很低
  LEVEL_2 = 2, // 较低
  LEVEL_3 = 3, // 中等
  LEVEL_4 = 4, // 较高
  LEVEL_5 = 5, // 灾难性
}

export const RiskLevelLabel: Record<RiskLevel, string> = {
  [RiskLevel.LEVEL_1]: '很低',
  [RiskLevel.LEVEL_2]: '较低',
  [RiskLevel.LEVEL_3]: '中等',
  [RiskLevel.LEVEL_4]: '较高',
  [RiskLevel.LEVEL_5]: '灾难性',
};

// 攻击样本状态
export enum SampleStatus {
  ACTIVE = 'active',           // 可用（稳定触发）
  PENDING = 'pending',         // 待验证
  UNSTABLE = 'unstable',       // 效果不稳定
  DEPRECATED = 'deprecated',   // 已废弃
}

// 实验状态
export enum ExperimentStatus {
  DRAFT = 'draft',             // 草稿（未提交）
  PENDING = 'pending',         // 等待执行
  RUNNING = 'running',         // 执行中
  COMPLETED = 'completed',     // 已完成
  FAILED = 'failed',           // 执行失败
  STOPPED = 'stopped',         // 已停止
}

// ============================================================
// 防御层（对应文档第355-367行 五层防御体系）
// ============================================================

export enum DefenseLayer {
  SOURCE_GOVERNANCE = 'source_governance',           // 第一层：源头数据与供应链治理
  MODEL_INTERACTION = 'model_interaction',           // 第二层：模型交互与上下文约束
  MEMORY_CONTROL = 'memory_control',                 // 第三层：记忆读写安全控制
  TOOL_CONSTRAINT = 'tool_constraint',               // 第四层：工具调用与执行安全控制
  DECISION_SUPERVISION = 'decision_supervision',     // 第五层：决策监督与多源验证
}

export const DefenseLayerLabel: Record<DefenseLayer, string> = {
  [DefenseLayer.SOURCE_GOVERNANCE]: '源头数据与供应链治理',
  [DefenseLayer.MODEL_INTERACTION]: '模型交互与上下文约束',
  [DefenseLayer.MEMORY_CONTROL]: '记忆读写安全控制',
  [DefenseLayer.TOOL_CONSTRAINT]: '工具调用与执行安全控制',
  [DefenseLayer.DECISION_SUPERVISION]: '决策监督与多源验证',
};

// 防御层序号映射
export const DefenseLayerIndex: Record<DefenseLayer, number> = {
  [DefenseLayer.SOURCE_GOVERNANCE]: 1,
  [DefenseLayer.MODEL_INTERACTION]: 2,
  [DefenseLayer.MEMORY_CONTROL]: 3,
  [DefenseLayer.TOOL_CONSTRAINT]: 4,
  [DefenseLayer.DECISION_SUPERVISION]: 5,
};

// ============================================================
// 规则引擎枚举 (Phase 0 新增)
// ============================================================

/** 规则命中后的动作 */
export enum RuleAction {
  BLOCK = 'block',
  WARN = 'warn',
  LOG = 'log',
  QUARANTINE = 'quarantine',
  FILTER = 'filter',
  REWRITE = 'rewrite',
}

export const RuleActionLabel: Record<RuleAction, string> = {
  [RuleAction.BLOCK]: '阻断',
  [RuleAction.WARN]: '警告',
  [RuleAction.LOG]: '日志',
  [RuleAction.QUARANTINE]: '隔离',
  [RuleAction.FILTER]: '过滤',
  [RuleAction.REWRITE]: '改写',
};

/** 规则匹配模式类型 */
export enum PatternType {
  REGEX = 'regex',
  KEYWORD = 'keyword',
  SEMANTIC = 'semantic',
  STRUCTURAL = 'structural',
  COMPOSITE = 'composite',
  CONDITION = 'condition',
}

export const PatternTypeLabel: Record<PatternType, string> = {
  [PatternType.REGEX]: '正则表达式',
  [PatternType.KEYWORD]: '关键词',
  [PatternType.SEMANTIC]: '语义检测',
  [PatternType.STRUCTURAL]: '结构校验',
  [PatternType.COMPOSITE]: '复合条件',
  [PatternType.CONDITION]: '条件表达式',
};

/** 防御编排模式 */
export enum DefenseMode {
  STRICT = 'strict',
  BALANCED = 'balanced',
  PERMISSIVE = 'permissive',
}

export const DefenseModeLabel: Record<DefenseMode, string> = {
  [DefenseMode.STRICT]: '严格模式 — 任何层拦截即全局阻断',
  [DefenseMode.BALANCED]: '均衡模式 — 累积风险分超阈值后拦截',
  [DefenseMode.PERMISSIVE]: '宽松模式 — 仅命中 block 规则时拦截',
};

// Agent 能力标签（对应文档第327行 标签过滤）
export enum AgentCapability {
  CHAT = 'chat',
  RAG = 'rag',
  TOOL = 'tool',
  STATEFUL = 'stateful',
  STATELESS = 'stateless',
  MULTI_AGENT = 'multi_agent',
}

export const AgentCapabilityLabel: Record<AgentCapability, string> = {
  [AgentCapability.CHAT]: '对话',
  [AgentCapability.RAG]: 'RAG检索',
  [AgentCapability.TOOL]: '工具调用',
  [AgentCapability.STATEFUL]: '有状态/记忆',
  [AgentCapability.STATELESS]: '无状态',
  [AgentCapability.MULTI_AGENT]: '多智能体协作',
};

// Agent 目标状态
export enum TargetStatus {
  ONLINE = 'online',
  OFFLINE = 'offline',
  REGISTERED = 'registered',     // 已注册未测试
  UNSTABLE = 'unstable',
}

// ============================================================
// 评估指标常量（对应文档第476-479行）
// ============================================================
export const RISK_SCORE_WEIGHTS = {
  w1: 0.4,  // ASR 权重
  w2: 0.35, // Impact 权重
  w3: 0.25, // Stealth 权重
};

export const RISK_SCORE_THRESHOLDS = [
  { max: 0.2, level: RiskLevel.LEVEL_1 },
  { max: 0.4, level: RiskLevel.LEVEL_2 },
  { max: 0.6, level: RiskLevel.LEVEL_3 },
  { max: 0.8, level: RiskLevel.LEVEL_4 },
  { max: 1.0, level: RiskLevel.LEVEL_5 },
];

// ============================================================
// 多源验证权重 (Phase 0 新增, 对应设计文档 §6.2.1)
// ============================================================
export const SOURCE_WEIGHTS: Record<string, number> = {
  user_confirmed: 1.0,
  internal_db: 0.9,
  verified_api: 0.8,
  curated_rag: 0.6,
  tool_output: 0.4,
  model_inference: 0.3,
};
