// 全局 API 配置 — 控制 Mock / 真实后端切换

/** 当前是否使用 Mock 数据 */
export const USE_MOCK: boolean = import.meta.env.VITE_USE_MOCK !== 'false';

/** 真实后端基础路径 (与 vite proxy 匹配) */
export const API_BASE = '/api';
