// ============================================================
// 所有 DTO 接口定义（与后端 API 契约）
// ============================================================

import {
  AttackFamily, SampleStatus, ExperimentStatus,
  DefenseLayer, AgentCapability, TargetStatus, RiskLevel,
  RuleAction, PatternType, DefenseMode,
} from '../utils/constants';

// --------------------- 目标（Agent）相关 ---------------------

export interface TargetAgent {
  id: string;                    // target_id: http_agent_001
  name: string;
  base_url: string;
  port: number;
  method: 'POST' | 'GET';
  input_field: string;           // 请求体中的输入字段名
  output_field: string;          // 响应体中的输出字段名
  health_check_path: string;     // 健康检查路径
  capabilities: AgentCapability[];
  rag_config?: RAGConfig;
  memory_config?: MemoryConfig;
  tool_config?: ToolConfig;
  defense_strategy?: string;     // 已应用的防御策略描述
  status: TargetStatus;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface RAGConfig {
  enabled: boolean;
  vector_db_type?: string;       // FAISS / Chroma / etc
  index_name?: string;
  embedding_model?: string;
}

export interface MemoryConfig {
  enabled: boolean;
  storage_type?: string;         // session / persistent / hybrid
  ttl_seconds?: number;
}

export interface ToolConfig {
  enabled: boolean;
  tool_schema?: unknown;         // 预留：工具定义schema
  max_calls_per_task?: number;
}

export interface TargetHealth {
  target_id: string;
  status: TargetStatus;
  response_time_ms: number;
  last_checked: string;
  error_message?: string;
}

// --------------------- 攻击相关 ---------------------

export interface AttackFamilyNode {
  family: AttackFamily;
  label: string;
  category: 'direct_input' | 'environmental';
  description: string;
  typical_carriers: string[];    // 典型载体
  risk_level: RiskLevel;         // 1-5级
  asr: number;                   // 攻击成功率 [0, 1]
  impact: number;                // 影响范围 [0, 1]
  stealth: number;               // 隐蔽性 [0, 1]
  risk_score: number;            // 综合风险评分
}

export interface AttackSample {
  case_id: string;
  family: AttackFamily;
  attack_goal: string;           // 攻击目标描述
  payload: string;               // 攻击载荷内容
  trigger_query?: string;        // 触发查询（环境型攻击用）
  expected_response_marker?: string;
  status: SampleStatus;
  tags: string[];               // 标签
  created_at: string;
  updated_at: string;
}

export interface AttackVariant {
  variant_id: string;
  case_id: string;               // 父样本ID
  family: AttackFamily;
  attack_goal: string;
  variant_strategy: string;      // 变体策略描述
  payload: string;
  trigger_query?: string;
  target_id: string;             // 测试目标
  run_id?: string;               // 关联的实验ID
  success?: boolean;             // 是否攻击成功
  score?: number;                // 评分
  feedback_summary?: string;     // 反馈原因摘要
  created_at: string;
}

// --------------------- 防御相关 ---------------------

export interface DefenseLayerConfig {
  layer: DefenseLayer;
  label: string;
  enabled: boolean;
  description: string;
  rules: DefenseRule[];
  // 以下字段按层有不同含义，统一用 Record 预留
  params: Record<string, unknown>;
  // 统计 (运行时填充)
  stats?: {
    total_checks: number;
    total_blocked: number;
    block_rate: number;
    last_check_at?: string;
  };
}

export interface DefenseRule {
  rule_id: string;
  name: string;
  description: string;
  enabled: boolean;
  action: RuleAction;
  priority: number;                    // 1-99, 越小越优先
  pattern_type: PatternType;           // 匹配模式类型
  pattern: string;                     // 匹配模式 (regex / keyword列表 / 条件表达式)
  condition?: string;                  // 额外条件, e.g. "trust_level < 0.5"
  target_fields: string[];             // 应用字段: ['content', 'source', 'tool_params', 'output']
  // 统计
  hit_count?: number;
  last_hit_at?: string;
  // 版本
  version?: number;
  created_at?: string;
  updated_at?: string;
}

// --------------------- 防御引擎专用类型 ---------------------

/** 单层检查结果 */
export interface LayerCheckResult {
  layer: DefenseLayer;
  passed: boolean;
  action: string;                      // "pass" | "block" | "warn" | "quarantine" | "rewrite"
  flags: string[];
  risk_score: number;
  matched_rules: string[];             // 命中的 rule_id 列表
  processing_time_ms: number;
  trust_level: number;                 // 经过此层后的可信度
  extra?: Record<string, unknown>;
}

/** 贯穿五层防御的运行时上下文 */
export interface DefenseContext {
  content: string;                     // 待检查内容
  source: string;                      // 来源标识
  task_description: string;
  run_id: string;
  target_id: string;
  trust_level: number;
  content_type: 'text' | 'file' | 'api_response' | 'tool_output';
  layer_results: Record<string, LayerCheckResult>;
  final_verdict: 'pending' | 'passed' | 'blocked' | 'warned';
  final_risk_score: number;
}

/** 防御事件日志 */
export interface DefenseEvent {
  event_id: string;
  timestamp: string;
  run_id: string;
  target_id: string;
  attack_family?: AttackFamily;
  case_id?: string;
  variant_id?: string;
  layer: DefenseLayer;
  rule_id: string;
  action: string;
  content_snippet: string;             // 匹配内容片段 (截断至 200 字符)
  risk_score: number;
}

/** POST /api/defenses/test 请求 */
export interface DefenseTestRequest {
  content: string;
  source: string;
  enabled_layers?: DefenseLayer[];     // 指定启用哪些层, 不传则全启用
  content_type?: 'text' | 'file' | 'api_response' | 'tool_output';
  task_description?: string;
}

/** POST /api/defenses/test 响应 */
export interface DefenseTestResult {
  passed: boolean;
  final_action: string;                // "block" | "warn" | "pass"
  layer_results: Record<string, LayerCheckResult | null>;
  risk_score: number;
  processing_time_ms: number;
}

/** 单层防御统计 */
export interface LayerStats {
  checks: number;
  blocked: number;
  rate: number;
}

/** 规则命中统计 */
export interface RuleHit {
  rule_id: string;
  hits: number;
  rule_name: string;
}

/** GET /api/defenses/stats 响应 */
export interface DefenseStats {
  total_checks: number;
  total_blocked: number;
  overall_block_rate: number;
  by_layer: Record<string, LayerStats>;
  top_rules: RuleHit[];
}

/** 预置防御策略 */
export interface DefenseStrategy {
  name: string;
  description: string;
  layers: Partial<Record<DefenseLayer, boolean>>;
  mode: DefenseMode;
}

// --------------------- 实验相关 ---------------------

export interface Experiment {
  run_id: string;
  name: string;
  description?: string;
  target_ids: string[];          // 测试目标列表
  attack_families: AttackFamily[];
  defense_layers: DefenseLayer[];
  sample_set?: string;           // 使用的样本集
  max_rounds?: number;
  status: ExperimentStatus;
  progress?: ExperimentProgress;
  is_proxy?: boolean;            // 是否经 defense_proxy → 真实 LLM
  is_manual?: boolean;          // 是否手动导入
  agent_type?: string;          // Agent 类型: "chat"/"tool"/"rag"/"langroid_rag"/"autogen_tool"
  created_at: string;
  started_at?: string;
  finished_at?: string;
}

export interface ExperimentProgress {
  total_samples: number;
  completed: number;
  failed: number;
  percentage: number;
  current_family?: AttackFamily;
  current_target?: string;
}

export interface ExperimentTimelineEvent {
  timestamp: string;
  event_type: 'attack_send' | 'defense_block' | 'defense_pass' |
              'defense_warn' | 'response_received' | 'score_computed' |
              'error' | 'status_change';
  target_id: string;
  attack_family: AttackFamily;
  case_id?: string;
  variant_id?: string;
  message: string;
  detail?: Record<string, unknown>;
}

// --------------------- 评估相关 ---------------------

export interface LayerStat {
  total_runs: number;
  blocked: number;
  avg_risk: number;
  block_rate: number;
  avg_trust: number;
}

export interface EvaluationSummary {
  run_id: string;
  total_attacks: number;
  // 攻击效果指标
  asr: number;                   // 攻击成功率
  blocked: number;
  // 防御效果指标
  dsr: number;                   // 防御拦截率
  fpr: number;                   // 误报率
  fnr: number;                   // 漏报率
  task_drift_rate: number | null; // 任务偏移率 (需独立观测系统)
  refusal_rate: number;          // 拒答率 (Proxy模式)
  // 持续污染指标 (null = 当前实验未采集)
  prp: number | null;            // 污染召回比例
  btr: number | null;            // 偏移触发率
  h_cum: number | null;          // 累计危害分 (参数待标定)
  // 引擎运行时指标
  risk_score: number;            // 引擎累积风险分 (来自 cumulative_risk)
  risk_level: RiskLevel;
  layer_stats: Record<string, LayerStat>;  // 逐层统计
  family_layer_stats?: Record<string, Record<string, { total_runs: number; blocked: number; block_rate: number }>>; // 逐族×层
  hit_rules: { rule_id: string; hits: number; rule_name?: string }[];
  // Proxy 模式专属
  is_proxy?: boolean;
  defense_block_rate?: number;
  compromised_count?: number;
  // 按攻击族分拆
  by_family: Record<string, FamilyEvaluation>;
  // Verdict 分布（逐样本判决统计）
  verdict_counts?: {
    attack: Record<string, number>;
    benign: Record<string, number>;
  };
  // 引擎风险分分布（low/mid/high 三桶）
  risk_distribution?: { low: number; mid: number; high: number };
  // 延迟 (ms)
  latency_p50?: number;
  latency_p99?: number;
  // Agent 对比 (Exp2等)
  agent_comparison?: {
    labels: string[];
    dsr: number[];
    blocked: number[];
    refused: number[];
    compromised: number[];
    fpr: number[];
  };
  agent_family_matrix?: Record<string, Record<string, number>>;
}

export interface FamilyEvaluation {
  family: AttackFamily;
  label: string;
  asr: number;
  dsr: number;
  risk_score: number;
  risk_level: RiskLevel;
  sample_count: number;
  success_count: number;
}

export interface EvaluationTrendPoint {
  timestamp: string;
  asr: number;
  dsr: number;
  risk_score: number;
  h_cum?: number | null;
  prp?: number | null;
}

export interface EvaluationCompare {
  run_ids: string[];
  metrics: Record<string, EvaluationSummary>;
}

// --------------------- 通用 ---------------------

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}
