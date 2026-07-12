// 防御模块 API
// 支持双模式: Mock 数据 (默认) / 真实后端 (VITE_USE_MOCK=false)

import type {
  DefenseLayerConfig, DefenseRule,
  DefenseTestRequest, DefenseTestResult,
  DefenseStats, DefenseStrategy,
} from './types';
import {
  mockDefenseLayers, mockDefenseTestResult,
  mockDefenseStats, mockDefenseStrategies,
} from './mock';
import { DefenseLayer } from '../utils/constants';
import client from './client';
import { USE_MOCK } from './config';

// ================================================================
// 真实 API 实现
// ================================================================

async function realGetDefenseLayers(): Promise<DefenseLayerConfig[]> {
  const res = await client.get('/defenses/layers');
  return (res as any).data;
}

async function realGetDefenseConfig(): Promise<{ enabled_layers: Record<string, boolean>; rule_count: number; enabled_rule_count: number }> {
  const res = await client.get('/defenses/config');
  return (res as any).data;
}

async function realUpdateDefenseConfig(data: { layer: DefenseLayer; enabled: boolean; params?: Record<string, unknown> }): Promise<{ layer: string; enabled: boolean }> {
  const res = await client.put('/defenses/config', data);
  return (res as any).data;
}

async function realGetDefenseRules(layer?: DefenseLayer): Promise<DefenseRule[]> {
  // 后端规则嵌入在 layers 响应中, 前端统一从 layers 提取
  const layers = await realGetDefenseLayers();
  if (layer) {
    const l = layers.find((l) => l.layer === layer);
    return l ? [...l.rules] : [];
  }
  return layers.flatMap((l) => l.rules);
}

async function realAddDefenseRule(
  layer: DefenseLayer,
  rule: Partial<DefenseRule> & { name: string },
): Promise<DefenseRule> {
  const res = await client.post('/defenses/rules', { layer, ...rule });
  return (res as any).data;
}

async function realUpdateDefenseRule(ruleId: string, updates: Partial<DefenseRule>): Promise<DefenseRule> {
  const res = await client.put(`/defenses/rules/${ruleId}`, updates);
  return (res as any).data;
}

async function realDeleteDefenseRule(ruleId: string): Promise<void> {
  await client.delete(`/defenses/rules/${ruleId}`);
}

async function realTestDefense(req: DefenseTestRequest): Promise<DefenseTestResult> {
  const res = await client.post('/defenses/test', req);
  return (res as any).data;
}

async function realGetDefenseStats(): Promise<DefenseStats> {
  const res = await client.get('/defenses/stats');
  return (res as any).data;
}

async function realGetDefenseStrategies(): Promise<DefenseStrategy[]> {
  const res = await client.get('/defenses/strategies');
  return (res as any).data.strategies;
}

async function realApplyDefenseStrategy(name: string): Promise<{ enabled_layers: Record<string, boolean> }> {
  const res = await client.put(`/defenses/strategies/${encodeURIComponent(name)}/apply`);
  return (res as any).data;
}

// ================================================================
// Mock API 实现 (保留, 无需后端即可运行)
// ================================================================

function delay(ms = 300): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

async function mockGetDefenseLayers(): Promise<DefenseLayerConfig[]> {
  await delay();
  return mockDefenseLayers.map(l => ({ ...l }));
}

async function mockGetDefenseConfig(): Promise<{ enabled_layers: Record<string, boolean>; rule_count: number; enabled_rule_count: number }> {
  await delay();
  return {
    enabled_layers: Object.fromEntries(mockDefenseLayers.map(l => [l.layer, l.enabled])),
    rule_count: mockDefenseLayers.flatMap(l => l.rules).length,
    enabled_rule_count: mockDefenseLayers.flatMap(l => l.rules).filter(r => r.enabled).length,
  };
}

async function mockUpdateDefenseConfig(data: {
  layer: DefenseLayer;
  enabled: boolean;
  params?: Record<string, unknown>;
}): Promise<{ layer: string; enabled: boolean }> {
  await delay();
  const l = mockDefenseLayers.find((l) => l.layer === data.layer);
  if (!l) throw new Error(`Layer ${data.layer} not found`);
  l.enabled = data.enabled;
  if (data.params) l.params = { ...l.params, ...data.params };
  return { layer: data.layer, enabled: data.enabled };
}

async function mockGetDefenseRules(layer?: DefenseLayer): Promise<DefenseRule[]> {
  await delay();
  if (layer) {
    const l = mockDefenseLayers.find((l) => l.layer === layer);
    return l ? [...l.rules] : [];
  }
  return mockDefenseLayers.flatMap((l) => l.rules);
}

async function mockAddDefenseRule(
  layer: DefenseLayer,
  rule: Partial<DefenseRule> & { name: string },
): Promise<DefenseRule> {
  await delay();
  const l = mockDefenseLayers.find((l) => l.layer === layer);
  if (!l) throw new Error(`Layer ${layer} not found`);
  const prefix: Record<string, string> = {
    source_governance: 'SG', model_interaction: 'MI',
    memory_control: 'MC', tool_constraint: 'TC', decision_supervision: 'DS',
  };
  const newRule: DefenseRule = {
    rule_id: `${prefix[layer]}${Date.now().toString(36).toUpperCase()}`,
    name: rule.name,
    description: rule.description || '',
    enabled: rule.enabled ?? true,
    action: rule.action || 'log',
    priority: rule.priority || 99,
    pattern_type: rule.pattern_type || 'regex',
    pattern: rule.pattern || '',
    condition: rule.condition ?? undefined,
    target_fields: rule.target_fields || ['content'],
    hit_count: 0,
    version: 1,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
  l.rules.push(newRule);
  return newRule;
}

async function mockUpdateDefenseRule(ruleId: string, updates: Partial<DefenseRule>): Promise<DefenseRule> {
  await delay();
  for (const layer of mockDefenseLayers) {
    const rule = layer.rules.find(r => r.rule_id === ruleId);
    if (rule) {
      Object.assign(rule, updates, {
        updated_at: new Date().toISOString(),
        version: (rule.version || 1) + 1,
      });
      return rule;
    }
  }
  throw new Error(`Rule ${ruleId} not found`);
}

async function mockDeleteDefenseRule(ruleId: string): Promise<void> {
  await delay();
  for (const layer of mockDefenseLayers) {
    const idx = layer.rules.findIndex(r => r.rule_id === ruleId);
    if (idx !== -1) {
      layer.rules.splice(idx, 1);
      return;
    }
  }
  throw new Error(`Rule ${ruleId} not found`);
}

async function mockTestDefense(req: DefenseTestRequest): Promise<DefenseTestResult> {
  await delay(500);
  return { ...mockDefenseTestResult };
}

async function mockGetDefenseStats(): Promise<DefenseStats> {
  await delay();
  return { ...mockDefenseStats };
}

async function mockGetDefenseStrategies(): Promise<DefenseStrategy[]> {
  await delay();
  return [...mockDefenseStrategies];
}

async function mockApplyDefenseStrategy(name: string): Promise<{ enabled_layers: Record<string, boolean> }> {
  await delay();
  const strategy = mockDefenseStrategies.find(s => s.name === name);
  if (!strategy) throw new Error(`Strategy ${name} not found`);
  for (const [layerName, enabled] of Object.entries(strategy.layers)) {
    const l = mockDefenseLayers.find(l => l.layer === layerName);
    if (l) l.enabled = enabled;
  }
  return {
    enabled_layers: Object.fromEntries(mockDefenseLayers.map(l => [l.layer, l.enabled])),
  };
}

// ================================================================
// 统一导出 — 根据 USE_MOCK 自动切换
// ================================================================

export const getDefenseLayers      = USE_MOCK ? mockGetDefenseLayers      : realGetDefenseLayers;
export const getDefenseConfig      = USE_MOCK ? mockGetDefenseConfig      : realGetDefenseConfig;
export const updateDefenseConfig   = USE_MOCK ? mockUpdateDefenseConfig   : realUpdateDefenseConfig;
export const getDefenseRules       = USE_MOCK ? mockGetDefenseRules       : realGetDefenseRules;
export const addDefenseRule        = USE_MOCK ? mockAddDefenseRule        : realAddDefenseRule;
export const updateDefenseRule     = USE_MOCK ? mockUpdateDefenseRule     : realUpdateDefenseRule;
export const deleteDefenseRule     = USE_MOCK ? mockDeleteDefenseRule     : realDeleteDefenseRule;
export const testDefense           = USE_MOCK ? mockTestDefense           : realTestDefense;
export const getDefenseStats       = USE_MOCK ? mockGetDefenseStats       : realGetDefenseStats;
export const getDefenseStrategies  = USE_MOCK ? mockGetDefenseStrategies  : realGetDefenseStrategies;
export const applyDefenseStrategy  = USE_MOCK ? mockApplyDefenseStrategy  : realApplyDefenseStrategy;
