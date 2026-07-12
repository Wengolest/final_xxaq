import { create } from 'zustand';
import type { TargetAgent, TargetHealth } from '../api/types';
import * as targetApi from '../api/target';

interface TargetState {
  targets: TargetAgent[];
  healthMap: Record<string, TargetHealth>;
  loading: boolean;

  fetchTargets: () => Promise<void>;
  getTarget: (id: string) => TargetAgent | undefined;
  createTarget: (data: Partial<TargetAgent>) => Promise<TargetAgent>;
  updateTarget: (id: string, data: Partial<TargetAgent>) => Promise<void>;
  deleteTarget: (id: string) => Promise<void>;
  checkHealth: (id: string) => Promise<void>;
  checkAllHealth: () => Promise<void>;
}

export const useTargetStore = create<TargetState>((set, get) => ({
  targets: [],
  healthMap: {},
  loading: false,

  fetchTargets: async () => {
    set({ loading: true });
    const targets = await targetApi.getTargets();
    set({ targets, loading: false });
  },

  getTarget: (id: string) => get().targets.find((t) => t.id === id),

  createTarget: async (data) => {
    const target = await targetApi.createTarget(data);
    set((s) => ({ targets: [...s.targets, target] }));
    return target;
  },

  updateTarget: async (id, data) => {
    const updated = await targetApi.updateTarget(id, data);
    set((s) => ({ targets: s.targets.map((t) => (t.id === id ? updated : t)) }));
  },

  deleteTarget: async (id) => {
    await targetApi.deleteTarget(id);
    set((s) => ({ targets: s.targets.filter((t) => t.id !== id) }));
  },

  checkHealth: async (id) => {
    const health = await targetApi.checkTargetHealth(id);
    set((s) => ({ healthMap: { ...s.healthMap, [id]: health } }));
  },

  checkAllHealth: async () => {
    const { targets } = get();
    const results = await Promise.all(targets.map((t) => targetApi.checkTargetHealth(t.id)));
    const healthMap: Record<string, TargetHealth> = {};
    results.forEach((h) => { healthMap[h.target_id] = h; });
    set({ healthMap });
  },
}));
