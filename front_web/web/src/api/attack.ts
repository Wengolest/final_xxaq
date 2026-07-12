// 攻击模块 API
import type { AttackFamilyNode, AttackSample, AttackVariant } from './types';
import { mockAttackFamilies, mockAttackSamples, mockVariants } from './mock';
import { AttackFamily, SampleStatus } from '../utils/constants';

export async function getAttackFamilies(): Promise<AttackFamilyNode[]> {
  await delay();
  return [...mockAttackFamilies];
}

export async function getAttackSamples(params?: {
  family?: AttackFamily;
  status?: string;
}): Promise<AttackSample[]> {
  await delay();
  let samples = [...mockAttackSamples];
  if (params?.family) samples = samples.filter((s) => s.family === params.family);
  if (params?.status) samples = samples.filter((s) => s.status === params.status);
  return samples;
}

export async function createSample(data: Partial<AttackSample>): Promise<AttackSample> {
  await delay();
  const sample: AttackSample = {
    case_id: `A${Date.now()}`,
    family: data.family || AttackFamily.PROMPT_INJECTION,
    attack_goal: data.attack_goal || '',
    payload: data.payload || '',
    status: SampleStatus.PENDING,
    tags: data.tags || [],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
  mockAttackSamples.push(sample);
  return sample;
}

export async function updateSample(caseId: string, data: Partial<AttackSample>): Promise<AttackSample> {
  await delay();
  const idx = mockAttackSamples.findIndex((s) => s.case_id === caseId);
  if (idx >= 0) {
    mockAttackSamples[idx] = { ...mockAttackSamples[idx], ...data, updated_at: new Date().toISOString() };
    return mockAttackSamples[idx];
  }
  throw new Error(`Sample ${caseId} not found`);
}

export async function deleteSample(caseId: string): Promise<void> {
  await delay();
  const idx = mockAttackSamples.findIndex((s) => s.case_id === caseId);
  if (idx >= 0) mockAttackSamples.splice(idx, 1);
}

export async function generateVariants(caseId: string, targetId: string): Promise<AttackVariant[]> {
  await delay(1000);
  const sample = mockAttackSamples.find((s) => s.case_id === caseId);
  if (!sample) throw new Error('样本不存在');
  // 模拟生成2个变体
  const variants: AttackVariant[] = [
    {
      variant_id: `VAR_${Date.now()}_1`, case_id: caseId, family: sample.family,
      attack_goal: sample.attack_goal,
      variant_strategy: '角色包装：伪装成系统管理员通知',
      payload: sample.payload + '\n[变体：角色包装改写]',
      target_id: targetId, created_at: new Date().toISOString(),
    },
    {
      variant_id: `VAR_${Date.now()}_2`, case_id: caseId, family: sample.family,
      attack_goal: sample.attack_goal,
      variant_strategy: '上下文重排：先建立对话再注入',
      payload: '[变体：上下文重排改写] ' + sample.payload,
      target_id: targetId, created_at: new Date().toISOString(),
    },
  ];
  mockVariants.push(...variants);
  return variants;
}

export async function getVariants(caseId: string): Promise<AttackVariant[]> {
  await delay();
  return mockVariants.filter((v) => v.case_id === caseId);
}

function delay(ms = 300): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}
