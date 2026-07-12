// 实验编排 API — 双模式 (Mock / Real)

import type {
  Experiment, ExperimentTimelineEvent,
} from './types';
import { mockExperiments, mockTimelineEvents } from './mock';
import { AttackFamily, DefenseLayer, ExperimentStatus } from '../utils/constants';
import client from './client';
import { USE_MOCK } from './config';

// ================================================================
// 真实 API 实现
// ================================================================

async function realGetExperiments(): Promise<Experiment[]> {
  const res = await client.get('/experiments');
  const data = (res as any).data;
  return (Array.isArray(data) ? data : []).map(_mapBackendExperiment);
}

async function realGetExperiment(runId: string): Promise<Experiment | undefined> {
  try {
    const res = await client.get(`/experiments/${runId}`);
    return _mapBackendExperiment((res as any).data);
  } catch {
    return undefined;
  }
}

async function realCreateExperiment(data: {
  name: string;
  target_ids: string[];
  attack_families: AttackFamily[];
  defense_layers: DefenseLayer[];
  description?: string;
  use_proxy?: boolean;
  agent_type?: string;
}): Promise<Experiment> {
  const body = {
    name: data.name,
    target_ids: data.target_ids || [],
    attack_families: data.attack_families || [],
    defense_layers: data.defense_layers || [],
    defense_mode: 'balanced',
    description: data.description || '',
    use_proxy: data.use_proxy || false,
    agent_type: data.agent_type || '',
  };
  const res = await client.post('/experiments/run', body);
  return _mapBackendExperiment((res as any).data);
}

async function realStartExperiment(runId: string): Promise<Experiment> {
  // 真实后端 create 即执行, 此处直接返回已完成的实验
  const exp = await realGetExperiment(runId);
  if (!exp) throw new Error('实验不存在');
  return exp;
}

async function realStopExperiment(runId: string): Promise<Experiment> {
  // 同步实验不支持中途停止
  const exp = await realGetExperiment(runId);
  if (!exp) throw new Error('实验不存在');
  return exp;
}

async function realGetTimeline(runId: string): Promise<ExperimentTimelineEvent[]> {
  const res = await client.get(`/experiments/${runId}/timeline`);
  const data = (res as any).data;
  return Array.isArray(data) ? data : [];
}

// ================================================================
// Mock 实现 (保留原有逻辑)
// ================================================================

async function mockGetExperiments(): Promise<Experiment[]> {
  await delay();
  return [...mockExperiments].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );
}

async function mockGetExperiment(runId: string): Promise<Experiment | undefined> {
  await delay();
  return mockExperiments.find((e) => e.run_id === runId);
}

async function mockCreateExperiment(data: {
  name: string;
  target_ids: string[];
  attack_families: AttackFamily[];
  defense_layers: DefenseLayer[];
  description?: string;
}): Promise<Experiment> {
  await delay();
  const exp: Experiment = {
    run_id: `RUN_${new Date().toISOString().slice(0, 10).replace(/-/g, '')}_${String(mockExperiments.length + 1).padStart(3, '0')}`,
    name: data.name,
    target_ids: data.target_ids,
    attack_families: data.attack_families,
    defense_layers: data.defense_layers,
    description: data.description,
    status: ExperimentStatus.DRAFT,
    created_at: new Date().toISOString(),
  };
  mockExperiments.push(exp);
  return exp;
}

async function mockStartExperiment(runId: string): Promise<Experiment> {
  await delay();
  const exp = mockExperiments.find((e) => e.run_id === runId);
  if (!exp) throw new Error('实验不存在');
  exp.status = ExperimentStatus.RUNNING;
  exp.started_at = new Date().toISOString();
  exp.progress = { total_samples: exp.max_rounds || 50, completed: 0, failed: 0, percentage: 0 };
  return exp;
}

async function mockStopExperiment(runId: string): Promise<Experiment> {
  await delay();
  const exp = mockExperiments.find((e) => e.run_id === runId);
  if (!exp) throw new Error('实验不存在');
  exp.status = ExperimentStatus.STOPPED;
  exp.finished_at = new Date().toISOString();
  return exp;
}

async function mockGetTimeline(_runId: string): Promise<ExperimentTimelineEvent[]> {
  await delay();
  return mockTimelineEvents;
}

// ================================================================
// 类型转换 & 工具函数
// ================================================================

function _mapBackendExperiment(raw: any): Experiment {
  const backendStatus = raw.status || 'completed';
  const statusMap: Record<string, any> = {
    'running': ExperimentStatus.RUNNING,
    'completed': ExperimentStatus.COMPLETED,
    'failed': ExperimentStatus.FAILED,
    'stopped': ExperimentStatus.STOPPED,
    'draft': ExperimentStatus.DRAFT,
  };
  const progress = raw.progress || {};
  return {
    run_id: raw.run_id || '',
    name: raw.name || '',
    description: raw.description || '',
    target_ids: raw.target_ids || ['orchestrator'],
    attack_families: raw.attack_families || [],
    defense_layers: raw.defense_layers || [],
    status: statusMap[backendStatus] || ExperimentStatus.COMPLETED,
    progress: {
      total_samples: progress.total_samples || raw.total_samples || 0,
      completed: progress.completed || raw.completed || 0,
      failed: progress.failed || 0,
      percentage: progress.percentage || (raw.total_samples > 0 ? Math.round((raw.completed / raw.total_samples) * 100) : 0),
    },
    is_proxy: raw.is_proxy || false,
    agent_type: raw.agent_type || '',
    created_at: raw.created_at || new Date().toISOString(),
    started_at: raw.created_at,
    finished_at: backendStatus === 'completed' ? raw.created_at : undefined,
    max_rounds: raw.total_samples,
  };
}

function delay(ms = 300): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

async function realImportExperiment(data: Record<string, unknown>): Promise<Experiment> {
  const res = await client.post('/experiments/manual', data);
  return _mapBackendExperiment((res as any).data);
}

async function mockImportExperiment(data: Record<string, unknown>): Promise<Experiment> {
  await delay();
  const exp: Experiment = {
    run_id: `MANUAL_${Date.now()}`,
    name: (data.name as string) || '手动导入',
    description: '',
    target_ids: [],
    attack_families: (data.attack_families as AttackFamily[]) || [],
    defense_layers: [],
    status: ExperimentStatus.COMPLETED,
    progress: { total_samples: 0, completed: 0, failed: 0, percentage: 100 },
    is_proxy: (data.is_proxy as boolean) || false,
    is_manual: true,
    created_at: new Date().toISOString(),
    started_at: new Date().toISOString(),
    finished_at: new Date().toISOString(),
  };
  mockExperiments.unshift(exp);
  return exp;
}

// ================================================================
// 统一导出 — 根据 USE_MOCK 自动切换
// ================================================================

export const getExperiments    = USE_MOCK ? mockGetExperiments    : realGetExperiments;
export const getExperiment     = USE_MOCK ? mockGetExperiment     : realGetExperiment;
export const createExperiment  = USE_MOCK ? mockCreateExperiment  : realCreateExperiment;
export const startExperiment   = USE_MOCK ? mockStartExperiment   : realStartExperiment;
export const stopExperiment    = USE_MOCK ? mockStopExperiment    : realStopExperiment;
export const getTimeline       = USE_MOCK ? mockGetTimeline       : realGetTimeline;
export const importExperiment  = USE_MOCK ? mockImportExperiment  : realImportExperiment;
