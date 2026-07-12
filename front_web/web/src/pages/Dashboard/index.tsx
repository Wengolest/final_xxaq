import { useEffect, useState, useMemo } from 'react';
import { Row, Col, Card, Table, Tag, Spin } from 'antd';
import ReactECharts from 'echarts-for-react';
import MetricCard from '../../components/MetricCard';
import { useTargetStore } from '../../store/targetStore';
import { useExperimentStore } from '../../store/experimentStore';
import * as evaluationApi from '../../api/evaluation';
import type { EvaluationSummary } from '../../api/types';
import { formatDateTime } from '../../utils/formatters';
import { experimentStatusColor } from '../../utils/colorMap';
import { ExperimentStatus } from '../../utils/constants';

const TOTAL_ATTACK_FAMILIES = 12;

const statusLabel: Record<string, string> = {
  draft: '草稿', pending: '等待中', running: '运行中',
  completed: '已完成', failed: '失败', stopped: '已停止',
};

export default function Dashboard() {
  const { targets, fetchTargets, checkAllHealth } = useTargetStore();
  const { experiments, loading: eLoading, fetchExperiments } = useExperimentStore();
  const [summary, setSummary] = useState<EvaluationSummary | null>(null);
  const [chartLoading, setChartLoading] = useState(false);
  const [loading, setLoading] = useState(true);

  // Step 1: 加载基础数据
  useEffect(() => {
    Promise.all([fetchTargets(), fetchExperiments(), checkAllHealth()])
      .finally(() => setLoading(false));
  }, []);

  // Step 2: 实验列表就绪后，取最近一次已完成实验的评估结果
  useEffect(() => {
    const latestCompleted = experiments
      .filter((e) => e.status === ExperimentStatus.COMPLETED)
      .sort((a, b) =>
        new Date(b.finished_at || '').getTime() - new Date(a.finished_at || '').getTime(),
      )[0];
    if (latestCompleted) {
      setChartLoading(true);
      evaluationApi
        .getEvaluationSummary(latestCompleted.run_id)
        .then(setSummary)
        .finally(() => setChartLoading(false));
    }
  }, [experiments]);

  // ---- 四个项目级指标卡片 ----

  const onlineCount = targets.filter((t) => t.status === 'online').length;

  const testedFamilies = useMemo(() => {
    const families = new Set(experiments.flatMap((e) => e.attack_families));
    return families.size;
  }, [experiments]);

  const completedCount = experiments.filter(
    (e) => e.status === ExperimentStatus.COMPLETED,
  ).length;

  const highThreatCount = summary?.by_family
    ? Object.values(summary.by_family).filter((f) => f.dsr < 0.5).length
    : 0;

  const recentExperiments = experiments.slice(0, 5);

  // ---- 图表 ----

  const familyLabels = summary?.by_family
    ? Object.values(summary.by_family).map((f) => f.label)
    : [];

  const trendOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['ASR', 'DSR', '风险评分'], bottom: 0 },
    grid: { left: 50, right: 20, top: 20, bottom: 40 },
    xAxis: {
      type: 'category',
      data: familyLabels,
      axisLabel: { fontSize: 11 },
    },
    yAxis: { type: 'value', max: 1, axisLabel: { formatter: (v: number) => `${(v * 100).toFixed(0)}%` } },
    series: [
      {
        name: 'ASR', type: 'bar',
        data: summary?.by_family
          ? Object.values(summary.by_family).map((f) => f.asr)
          : [],
        itemStyle: { color: '#f5222d' },
      },
      {
        name: 'DSR', type: 'bar',
        data: summary?.by_family
          ? Object.values(summary.by_family).map((f) => f.dsr)
          : [],
        itemStyle: { color: '#52c41a' },
      },
      {
        name: '风险评分', type: 'line', yAxisIndex: 0,
        data: summary?.by_family
          ? Object.values(summary.by_family).map((f) => f.risk_score)
          : [],
        itemStyle: { color: '#faad14' },
        symbol: 'diamond',
        lineStyle: { width: 2 },
      },
    ],
  };

  const expColumns = [
    { title: '实验名称', dataIndex: 'name', key: 'name', ellipsis: true },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 80,
      render: (s: string) => <Tag color={experimentStatusColor[s]}>{statusLabel[s] || s}</Tag>,
    },
    {
      title: '进度', dataIndex: 'progress', key: 'progress', width: 100,
      render: (p?: { percentage: number }) =>
        p ? `${p.percentage}%` : '-',
    },
    {
      title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 170,
      render: (v: string) => formatDateTime(v),
    },
  ];

  return (
    <Spin spinning={loading}>
      <h2 style={{ marginBottom: 24 }}>仪表盘</h2>

      {/* 项目健康度卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <MetricCard
            title="Agent 目标规模"
            value={targets.length}
            suffix={`在线 ${onlineCount}`}
            tooltip="已注册的 HTTP Target Agent 数量及在线状态"
            valueStyle={{ color: '#1677ff' }}
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <MetricCard
            title="攻击族覆盖度"
            value={testedFamilies}
            suffix={`/ ${TOTAL_ATTACK_FAMILIES}`}
            tooltip="所有实验累计已测试的攻击族种类数"
            valueStyle={{ color: testedFamilies >= 8 ? '#52c41a' : '#faad14' }}
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <MetricCard
            title="实验完成数"
            value={completedCount}
            suffix={`/ ${experiments.length}`}
            tooltip="已完成的实验数 / 实验总数"
            valueStyle={{ color: '#1677ff' }}
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <MetricCard
            title="高威胁发现数"
            value={highThreatCount}
            suffix="个攻击族"
            tooltip="最近一次已完成实验中 DSR < 50% 的攻击族数量（防御薄弱点）"
            valueStyle={{ color: highThreatCount > 0 ? '#f5222d' : '#52c41a' }}
          />
        </Col>
      </Row>

      {/* 图表 + 最近实验 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={14}>
          <Card title="历史攻击实验结果">
            <Spin spinning={chartLoading}>
              {familyLabels.length > 0 ? (
                <ReactECharts option={trendOption} style={{ height: 320 }} />
              ) : (
                <div style={{ height: 320, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
                  暂无实验数据
                </div>
              )}
            </Spin>
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card title="最近实验">
            <Table
              dataSource={recentExperiments}
              columns={expColumns}
              rowKey="run_id"
              size="small"
              pagination={false}
              loading={eLoading}
            />
          </Card>
        </Col>
      </Row>
    </Spin>
  );
}
