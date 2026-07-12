// 评估结果 API — 双模式 (Mock / Real)

import type {
  EvaluationSummary, EvaluationTrendPoint, FamilyEvaluation,
  EvaluationCompare,
} from './types';
import { RiskLevel } from '../utils/constants';
import { mockEvaluationSummaries, mockTrendData } from './mock';
import client from './client';
import { USE_MOCK } from './config';

// ================================================================
// 攻击族标签映射 (后端 family → 前端 label)
// ================================================================

const FAMILY_LABEL_MAP: Record<string, string> = {
  'benign': '正常',
  'prompt_injection': '直接提示注入',
  'jailbreak': '越狱改写',
  'encoding_obfuscation': '编码混淆',
  'zero_width': '零宽字符',
  'context_escalation': '上下文越权',
  'pii_leakage': 'PII泄露',
  'memory_poisoning': '长期记忆投毒',
  'tool_misuse': '工具滥用',
  'multi_turn_composite': '复合攻击',
};

function _toRiskLevel(score: number): RiskLevel {
  if (score <= 0.2) return RiskLevel.LEVEL_1;
  if (score <= 0.4) return RiskLevel.LEVEL_2;
  if (score <= 0.6) return RiskLevel.LEVEL_3;
  if (score <= 0.8) return RiskLevel.LEVEL_4;
  return RiskLevel.LEVEL_5;
}

// ================================================================
// 真实 API 实现
// ================================================================

async function realGetEvaluationSummary(runId: string): Promise<EvaluationSummary> {
  const res = await client.get(`/experiments/${runId}`);
  const exp = (res as any).data;
  if (!exp || !exp.metrics) {
    throw new Error('Experiment not found or no metrics');
  }
  const m = exp.metrics;
  const isProxy = m.is_proxy === true;

  const dsr = m.dsr || 0;
  const fpr = m.fpr || 0;

  // ---- 真实 ASR / refusal_rate (仅 Proxy 模式) ----
  const realAsr: number | undefined = isProxy ? m.asr : undefined;
  const realRefusalRate: number | undefined = isProxy ? m.refusal_rate : undefined;
  const defenseBlockRate: number = isProxy ? (m.defense_block_rate || 0) : dsr;
  const attackCompromised: number = isProxy ? (m.attack_compromised || 0) : 0;

  // 按攻击族分拆 (排除 benign)
  const by_family: Record<string, FamilyEvaluation> = {};
  const fd = m.family_dsr || {};
  for (const [family, stats] of Object.entries(fd) as [string, any][]) {
    if (family === 'benign') continue;
    if (isProxy) {
      // Proxy 模式: 使用真实 compromised/blocked/refused
      const total = stats.total || 1;
      const blocked = stats.blocked || 0;
      const refused = stats.refused || 0;
      const compromised = stats.compromised || 0;
      const familyDsr = (blocked + refused) / total;
      const familyAsr = compromised / total;
      const riskScore = familyAsr;
      by_family[family] = {
        family: family as any,
        label: FAMILY_LABEL_MAP[family] || family,
        asr: Math.round(familyAsr * 10000) / 10000,
        dsr: Math.round(familyDsr * 10000) / 10000,
        risk_score: Math.round(riskScore * 10000) / 10000,
        risk_level: _toRiskLevel(riskScore),
        sample_count: total,
        success_count: compromised,
      };
    } else {
      // 规则模式: DSR 来自引擎, ASR = 1-DSR (近似)
      const rate = stats.rate || stats.blocked / Math.max(stats.total, 1) || 0;
      const riskScore = rate * 0.5;
      by_family[family] = {
        family: family as any,
        label: FAMILY_LABEL_MAP[family] || family,
        asr: Math.round((1 - rate) * 10000) / 10000,
        dsr: Math.round(rate * 10000) / 10000,
        risk_score: Math.round(riskScore * 10000) / 10000,
        risk_level: _toRiskLevel(riskScore),
        sample_count: stats.total || 0,
        success_count: (stats.total || 0) - (stats.blocked || 0),
      };
    }
  }

  // 计算汇总指标
  let asr: number;
  let refusalRate: number;
  let engineRiskScore: number;  // 来自 defense_proxy 的 cumulative_risk

  if (isProxy && realAsr !== undefined && realRefusalRate !== undefined) {
    asr = Math.round(realAsr * 10000) / 10000;
    refusalRate = Math.round(realRefusalRate * 10000) / 10000;
    // 引擎风险分: 优先使用 per-sample cumulative_risk 均值（由 enrichment 计算）
    engineRiskScore = typeof m.engine_risk_score === 'number'
      ? Math.round(m.engine_risk_score * 10000) / 10000
      : Math.round(dsr * 10000) / 10000;
  } else {
    // 规则模式: ASR 由 DSR 推导 (近似值), 无 LLM 参与
    asr = Math.round((1 - dsr) * 10000) / 10000;
    refusalRate = 0;
    engineRiskScore = typeof m.engine_risk_score === 'number'
      ? Math.round(m.engine_risk_score * 10000) / 10000
      : Math.round(dsr * 10000) / 10000;
  }

  return {
    run_id: runId,
    total_attacks: m.attack_samples || 0,
    asr,
    blocked: (m.attack_blocked || 0) + (m.attack_refused || 0),
    dsr: Math.round(dsr * 10000) / 10000,
    fpr: Math.round(fpr * 10000) / 10000,
    fnr: Math.round((1 - dsr) * 10000) / 10000,
    task_drift_rate: null as any,
    refusal_rate: refusalRate,
    prp: null as any,
    btr: null as any,
    h_cum: null as any,
    risk_score: engineRiskScore,
    risk_level: _toRiskLevel(engineRiskScore),
    is_proxy: isProxy,
    defense_block_rate: Math.round(defenseBlockRate * 10000) / 10000,
    compromised_count: attackCompromised,
    by_family,
    layer_stats: m.layer_stats || {},
    family_layer_stats: m.family_layer_stats || undefined,
    hit_rules: m.top_rules || [],
    verdict_counts: m.verdict_counts || undefined,
    risk_distribution: m.risk_distribution || undefined,
    latency_p50: m.latency_p50,
    latency_p99: m.latency_p99,
    agent_comparison: m.agent_comparison || undefined,
    agent_family_matrix: m.agent_family_matrix || undefined,
  } as EvaluationSummary;
}

async function realGetEvaluationMetrics(runId: string): Promise<{
  byFamily: Record<string, FamilyEvaluation>;
  task_drift_rate: number;
  refusal_rate: number;
  fpr: number;
  fnr: number;
}> {
  const summary = await realGetEvaluationSummary(runId);
  return {
    byFamily: summary.by_family,
    task_drift_rate: summary.task_drift_rate,
    refusal_rate: summary.refusal_rate,
    fpr: summary.fpr,
    fnr: summary.fnr,
  };
}

async function realGetTrend(runId: string): Promise<EvaluationTrendPoint[]> {
  try {
    // 先获取实验详情 (含 results)
    const expRes = await client.get(`/experiments/${runId}`);
    const exp = (expRes as any).data;
    const isProxy = exp?.metrics?.is_proxy === true;
    const results: any[] = exp?.results || [];

    // 如果有 results 直接用 results 重建趋势 (更准确)
    if (results.length > 0) {
      // ≤50 样本全显示，>50 才采样，避免小数据集跳过过多数据点
      const MAX_FULL_SHOW = 50;
      const step = results.length <= MAX_FULL_SHOW
        ? 1
        : Math.max(1, Math.floor(results.length / 8));
      const points: EvaluationTrendPoint[] = [];
      let cumBlocked = 0;
      let cumCompromised = 0;
      let cumAttackTotal = 0;  // 只统攻击样本，避免正常样本拉偏趋势

      // 收集真实时间戳
      const timestamps = results.map((r: any) => r.timestamp || null);
      const firstTs = timestamps[0] ? new Date(timestamps[0]).getTime() : 0;
      const lastTs = timestamps[timestamps.length - 1] ? new Date(timestamps[timestamps.length - 1]).getTime() : 0;
      const totalSpanMs = lastTs - firstTs;

      for (let i = 0; i < results.length; i++) {
        const r = results[i];
        // 只对攻击样本累积分母，避免正常样本稀释 DSR/ASR
        if (r.is_attack) {
          cumAttackTotal++;
          // blocked: proxy直接拦截; refused: LLM拒绝
          if (r.verdict === 'blocked' || r.verdict === 'refused') cumBlocked++;
          // compromised: 未被拦截也未拒绝（passed攻击样本 或 compromised标记）
          if (r.verdict === 'compromised' || r.verdict === 'passed') cumCompromised++;
        } else {
          // 正常样本被误拦也算入 FPR 统计（但不影响 DSR/ASR 分母）
          if (r.verdict === 'blocked') cumBlocked++;
        }

        if ((i + 1) % step === 0 || i === results.length - 1) {
          const dsr = cumAttackTotal > 0 ? cumBlocked / cumAttackTotal : 0;
          const asr = cumAttackTotal > 0 ? cumCompromised / cumAttackTotal : 0;
          const useTime = totalSpanMs > 1000;
          points.push({
            timestamp: useTime ? r.timestamp : `#${i + 1}`,
            asr: Math.round(asr * 10000) / 10000,
            dsr: Math.round(dsr * 10000) / 10000,
            // 引擎风险分: 每样本的 r.risk_score（defense_proxy 计算的累积风险）
            risk_score: Math.round((r.risk_score ?? 0) * 10000) / 10000,
          });
        }
      }
      if (points.length >= 2) return points;
    }

    // Fallback: 从 timeline 事件重建
    const res = await client.get(`/experiments/${runId}/timeline`);
    const timeline: any[] = (res as any).data || [];

    const scoreEvents = timeline.filter((e: any) =>
      e.event_type === 'score_computed' || e.event_type === 'defense_block' || e.event_type === 'defense_pass',
    );
    if (scoreEvents.length === 0) return [];

    const step2 = scoreEvents.length <= 50
      ? 1
      : Math.max(1, Math.floor(scoreEvents.length / 8));
    const points2: EvaluationTrendPoint[] = [];
    let cumBlocked2 = 0;
    let cumTotal2 = 0;
    // 检查时间跨度
    const firstEvt = scoreEvents[0]?.timestamp ? new Date(scoreEvents[0].timestamp).getTime() : 0;
    const lastEvt = scoreEvents[scoreEvents.length - 1]?.timestamp ? new Date(scoreEvents[scoreEvents.length - 1].timestamp).getTime() : 0;
    const useTime2 = (lastEvt - firstEvt) > 1000;

    for (let i = 0; i < scoreEvents.length; i++) {
      cumTotal2++;
      if (scoreEvents[i].event_type === 'defense_block') cumBlocked2++;
      if ((i + 1) % step2 === 0 || i === scoreEvents.length - 1) {
        const dsr = cumBlocked2 / cumTotal2;
        points2.push({
          timestamp: useTime2 ? scoreEvents[i].timestamp : `#${i + 1}`,
          asr: Math.round((1 - dsr) * 10000) / 10000,
          dsr: Math.round(dsr * 10000) / 10000,
          risk_score: Math.round(dsr * 10000) / 10000,
        });
      }
    }
    return points2.length >= 2 ? points2 : [];
  } catch {
    return [];
  }
}

async function realCompareEvaluations(runIds: string[]): Promise<EvaluationCompare> {
  const metrics: Record<string, EvaluationSummary> = {};
  for (const id of runIds) {
    try {
      metrics[id] = await realGetEvaluationSummary(id);
    } catch {
      // skip
    }
  }
  return { run_ids: runIds, metrics };
}

// ================================================================
// Mock 实现 (沿用原逻辑)
// ================================================================

const defaultSummary = mockEvaluationSummaries['RUN_20260428_001'];

async function mockGetEvaluationSummary(runId: string): Promise<EvaluationSummary> {
  await delay();
  return mockEvaluationSummaries[runId] || { ...defaultSummary, run_id: runId };
}

async function mockGetEvaluationMetrics(runId: string): Promise<{
  byFamily: Record<string, FamilyEvaluation>;
  task_drift_rate: number;
  refusal_rate: number;
  fpr: number;
  fnr: number;
}> {
  await delay();
  const s = mockEvaluationSummaries[runId] || defaultSummary;
  return {
    byFamily: s.by_family,
    task_drift_rate: s.task_drift_rate,
    refusal_rate: s.refusal_rate,
    fpr: s.fpr,
    fnr: s.fnr,
  };
}

async function mockGetTrend(_runId: string): Promise<EvaluationTrendPoint[]> {
  await delay();
  return [...mockTrendData];
}

async function mockCompareEvaluations(runIds: string[]): Promise<EvaluationCompare> {
  await delay();
  const metrics: Record<string, EvaluationSummary> = {};
  for (const id of runIds) {
    metrics[id] = mockEvaluationSummaries[id] || { ...defaultSummary, run_id: id };
  }
  return { run_ids: runIds, metrics };
}

function delay(ms = 300): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

// ================================================================
// 统一导出 — 根据 USE_MOCK 自动切换
// ================================================================

export const getEvaluationSummary = USE_MOCK ? mockGetEvaluationSummary : realGetEvaluationSummary;
export const getEvaluationMetrics = USE_MOCK ? mockGetEvaluationMetrics : realGetEvaluationMetrics;
export const getTrend            = USE_MOCK ? mockGetTrend            : realGetTrend;
export const compareEvaluations  = USE_MOCK ? mockCompareEvaluations  : realCompareEvaluations;
