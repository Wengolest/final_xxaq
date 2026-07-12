// Agent目标管理 API
import type { TargetAgent, TargetHealth } from './types';
import { mockTargets, mockTargetHealth } from './mock';
import { TargetStatus } from '../utils/constants';

// TODO: 替换为真实API调用
// import client from './client';
// export const getTargets = () => client.get('/targets');

export async function getTargets(): Promise<TargetAgent[]> {
  await delay();
  return [...mockTargets];
}

export async function getTarget(id: string): Promise<TargetAgent | undefined> {
  await delay();
  return mockTargets.find((t) => t.id === id);
}

export async function createTarget(data: Partial<TargetAgent>): Promise<TargetAgent> {
  await delay();
  const newTarget: TargetAgent = {
    id: `http_agent_${String(mockTargets.length + 1).padStart(3, '0')}`,
    name: data.name || '',
    base_url: data.base_url || '',
    port: data.port || 8000,
    method: 'POST',
    input_field: data.input_field || 'query',
    output_field: data.output_field || 'answer',
    health_check_path: data.health_check_path || '/health',
    capabilities: data.capabilities || [],
    status: TargetStatus.REGISTERED,
    description: data.description,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
  mockTargets.push(newTarget);
  return newTarget;
}

export async function updateTarget(id: string, data: Partial<TargetAgent>): Promise<TargetAgent> {
  await delay();
  const idx = mockTargets.findIndex((t) => t.id === id);
  if (idx >= 0) {
    mockTargets[idx] = { ...mockTargets[idx], ...data, updated_at: new Date().toISOString() };
    return mockTargets[idx];
  }
  throw new Error(`Target ${id} not found`);
}

export async function deleteTarget(id: string): Promise<void> {
  await delay();
  const idx = mockTargets.findIndex((t) => t.id === id);
  if (idx >= 0) mockTargets.splice(idx, 1);
}

export async function checkTargetHealth(id: string): Promise<TargetHealth> {
  await delay(200);
  return mockTargetHealth[id] || {
    target_id: id, status: 'offline', response_time_ms: 0,
    last_checked: new Date().toISOString(), error_message: '未找到目标',
  };
}

function delay(ms = 300): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}
