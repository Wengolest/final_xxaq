import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card, Row, Col, Descriptions, Tag, Table, Button, Space, Spin, Empty, Tooltip,
} from 'antd';
import { ArrowLeftOutlined, QuestionCircleOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import type { EvaluationSummary, FamilyEvaluation, EvaluationTrendPoint, LayerStat } from '../../api/types';
import * as evaluationApi from '../../api/evaluation';
import { formatPercent, formatScore, formatDateTime } from '../../utils/formatters';
import { RiskLevelLabel, DefenseLayerLabel } from '../../utils/constants';
import { riskLevelColor, defenseLayerColor } from '../../utils/colorMap';

const LAYER_ORDER = ['source_governance', 'model_interaction', 'memory_control', 'tool_constraint', 'decision_supervision'] as const;

// 不可用指标展示 "—"
function fmtMaybe(v: number | null | undefined, formatter: (n: number) => string): string {
  if (v === null || v === undefined) return '—';
  return formatter(v);
}

export default function ResultAnalysis() {
  const { runId } = useParams<{ runId: string }>();
  const navigate = useNavigate();
  const [summary, setSummary] = useState<EvaluationSummary | null>(null);
  const [trend, setTrend] = useState<EvaluationTrendPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!runId) return;
    setLoading(true);
    Promise.all([
      evaluationApi.getEvaluationSummary(runId),
      evaluationApi.getTrend(runId),
    ]).then(([s, t]) => {
      setSummary(s);
      setTrend(t);
      setLoading(false);
    });
  }, [runId]);

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  if (!summary) return <Empty description="评估结果不存在" />;

  const familyList = Object.values(summary.by_family);
  const layerStats = summary.layer_stats || {};

  // ---- 逐层拦截贡献柱状图 ----
  const layerBarOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['拦截次数', '拦截率'], bottom: 0 },
    grid: { left: 50, right: 50, top: 20, bottom: 40 },
    xAxis: {
      type: 'category',
      data: LAYER_ORDER.map((ln) => DefenseLayerLabel[ln] || ln),
      axisLabel: { fontSize: 10 },
    },
    yAxis: [
      { type: 'value', name: '拦截次数', axisLabel: { fontSize: 10 } },
      { type: 'value', name: '拦截率', max: 1, axisLabel: { formatter: (v: number) => formatPercent(v, 0) } },
    ],
    series: [
      {
        name: '拦截次数', type: 'bar',
        data: LAYER_ORDER.map((ln) => layerStats[ln]?.blocked || 0),
        itemStyle: { color: '#1677ff' },
      },
      {
        name: '拦截率', type: 'bar', yAxisIndex: 1,
        data: LAYER_ORDER.map((ln) => layerStats[ln]?.block_rate || 0),
        itemStyle: { color: '#52c41a' },
      },
    ],
  };

  // ---- 攻击族 × 防御层 热力图 ----
  const heatFamilies = familyList.slice(0, 9);
  const fls = summary.family_layer_stats || {};
  const heatOption = {
    tooltip: { position: 'top', formatter: (params: any) => {
      const [li, fi] = params.data || [0, 0];
      const ln = LAYER_ORDER[li] || '';
      const fam = heatFamilies[fi];
      const famName = fam?.label || '';
      const stat = fls[fam?.family || '']?.[ln];
      const rate = stat?.block_rate ?? 0;
      return `${famName} × ${DefenseLayerLabel[ln] || ln}<br/>拦截率: ${(rate * 100).toFixed(1)}%<br/>拦截次数: ${stat?.blocked || 0} / ${stat?.total_runs || 0}`;
    }},
    grid: { left: 100, right: 20, top: 20, bottom: 30 },
    xAxis: {
      type: 'category',
      data: LAYER_ORDER.map((ln) => DefenseLayerLabel[ln]?.slice(0, 4) || ln),
      splitArea: { show: true },
    },
    yAxis: {
      type: 'category',
      data: heatFamilies.map((f) => f.label),
      splitArea: { show: true },
      axisLabel: { fontSize: 10 },
    },
    visualMap: {
      min: 0, max: 1,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      itemWidth: 12,
      itemHeight: 100,
      textStyle: { fontSize: 10 },
      inRange: { color: ['#f0f5ff', '#1677ff', '#002c8c'] },
    },
    series: [
      {
        name: '拦截率',
        type: 'heatmap',
        data: heatFamilies.flatMap((f, fi) =>
          LAYER_ORDER.map((ln, li) => [
            li,
            fi,
            fls[f.family]?.[ln]?.block_rate || 0,
          ])
        ),
        label: {
          show: true,
          fontSize: 10,
          formatter: (params: any) => {
            const v = params.data?.[2];
            return typeof v === 'number' && v > 0 ? `${(v * 100).toFixed(0)}%` : '';
          },
        },
        emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' } },
      },
    ],
  };

  // ---- cumulative_risk 分布直方图 ----
  const distBins = [
    { name: '[0, 0.3) 低风险', min: 0, max: 0.3, color: '#52c41a' },
    { name: '[0.3, 0.7) 中风险', min: 0.3, max: 0.7, color: '#faad14' },
    { name: '[0.7, 1.0] 高风险', min: 0.7, max: 1.0, color: '#f5222d' },
  ];
  const rd = summary.risk_distribution;
  const riskDistOption = {
    tooltip: { trigger: 'axis' },
    grid: { left: 50, right: 50, top: 20, bottom: 40 },
    xAxis: { type: 'category', data: distBins.map((b) => b.name), axisLabel: { fontSize: 10 } },
    yAxis: { type: 'value', name: '样本数' },
    series: [
      {
        name: '样本分布', type: 'bar',
        data: [
          { value: rd?.low ?? 0, itemStyle: { color: distBins[0].color } },
          { value: rd?.mid ?? 0, itemStyle: { color: distBins[1].color } },
          { value: rd?.high ?? 0, itemStyle: { color: distBins[2].color } },
        ],
      },
    ],
  };

  // ---- 命中规则 Top-N 表格 ----
  const hitRuleColumns = [
    { title: '规则ID', dataIndex: 'rule_id', key: 'rule_id', width: 100 },
    { title: '规则名称', dataIndex: 'rule_name', key: 'rule_name' },
    { title: '命中次数', dataIndex: 'hits', key: 'hits', width: 100 },
  ];

  // ---- 攻击族对比柱状图 ----
  const familyBarOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['ASR', 'DSR'], bottom: 0 },
    grid: { left: 60, right: 20, top: 20, bottom: 100 },
    xAxis: {
      type: 'category',
      data: familyList.map((f) => f.label),
      axisLabel: { rotate: 45, fontSize: 10 },
    },
    yAxis: { type: 'value', max: 1, axisLabel: { formatter: (v: number) => formatPercent(v, 0) } },
    series: [
      { name: 'ASR', type: 'bar', data: familyList.map((f) => f.asr), itemStyle: { color: '#f5222d' } },
      { name: 'DSR', type: 'bar', data: familyList.map((f) => f.dsr), itemStyle: { color: '#52c41a' } },
    ],
  };

  // ---- 趋势图 ----
  const isIndexAxis = trend.length > 0 && trend[0].timestamp.startsWith('#');
  const trendOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['ASR', 'DSR', '引擎风险分'], bottom: 0 },
    grid: { left: 50, right: 50, top: 20, bottom: 40 },
    xAxis: {
      type: 'category',
      name: isIndexAxis ? '样本序号 (瞬时完成)' : undefined,
      data: trend.map((p) =>
        isIndexAxis ? p.timestamp : formatDateTime(p.timestamp).slice(11, 19)
      ),
    },
    yAxis: { type: 'value', max: 1, min: 0 },
    series: [
      { name: 'ASR', type: 'line', data: trend.map((p) => p.asr), smooth: true, itemStyle: { color: '#f5222d' } },
      { name: 'DSR', type: 'line', data: trend.map((p) => p.dsr), smooth: true, itemStyle: { color: '#52c41a' } },
      { name: '引擎风险分', type: 'line', data: trend.map((p) => p.risk_score), smooth: true, itemStyle: { color: '#722ed1' }, lineStyle: { type: 'dashed' } },
    ],
  };

  // ---- 分族明细表 ----
  const familyColumns = [
    {
      title: '攻击族', dataIndex: 'label', key: 'label', width: 150,
      render: (label: string, r: FamilyEvaluation) => (
        <Tag color={riskLevelColor[r.risk_level]}>{label}</Tag>
      ),
    },
    {
      title: 'ASR', dataIndex: 'asr', key: 'asr', width: 90,
      render: (v: number) => <span style={{ color: v > 0.5 ? '#f5222d' : '#52c41a' }}>{formatPercent(v)}</span>,
    },
    {
      title: 'DSR', dataIndex: 'dsr', key: 'dsr', width: 90,
      render: (v: number) => <span style={{ color: v > 0.5 ? '#52c41a' : '#faad14' }}>{formatPercent(v)}</span>,
    },
    {
      title: '风险评分', dataIndex: 'risk_score', key: 'risk_score', width: 120,
      render: (v: number, r: FamilyEvaluation) => (
        <Space>
          <span style={{ fontWeight: 600, color: riskLevelColor[r.risk_level] }}>{formatScore(v)}</span>
          <Tag color={riskLevelColor[r.risk_level]}>Lv.{r.risk_level}</Tag>
          <span style={{ fontSize: 11, color: '#999' }}>{RiskLevelLabel[r.risk_level]}</span>
        </Space>
      ),
    },
    { title: '样本数', dataIndex: 'sample_count', key: 'sample_count', width: 80 },
    { title: '成功数', dataIndex: 'success_count', key: 'success_count', width: 80 },
  ];

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/experiments')}>返回</Button>
        <h2 style={{ margin: 0 }}>评估结果分析</h2>
        <Tag color={riskLevelColor[summary.risk_level]}>
          引擎风险 Lv.{summary.risk_level} ({RiskLevelLabel[summary.risk_level]})
        </Tag>
        {summary.is_proxy ? (
          <Tag color="purple">Proxy 模式（含 LLM 交互）</Tag>
        ) : (
          <Tag color="default">
            规则模式（纯引擎检测）
            <Tooltip title="ASR = 1 − DSR（近似值，无 LLM 参与）"><QuestionCircleOutlined style={{ marginLeft: 4 }} /></Tooltip>
          </Tag>
        )}
      </div>

      {/* 总览指标 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card size="small"><Descriptions column={1} size="small" title="攻击效果">
            <Descriptions.Item label={summary.is_proxy ? 'ASR (真实)' : 'ASR (≈1−DSR)'}>
              {formatPercent(summary.asr)}
            </Descriptions.Item>
            <Descriptions.Item label="拒答率">{formatPercent(summary.refusal_rate)}</Descriptions.Item>
            <Descriptions.Item label="任务偏移率">{fmtMaybe(summary.task_drift_rate, formatPercent)}</Descriptions.Item>
            {summary.is_proxy && (
              <Descriptions.Item label="攻击成功数">{summary.compromised_count ?? 0} / {summary.total_attacks}</Descriptions.Item>
            )}
          </Descriptions></Card>
        </Col>
        <Col span={6}>
          <Card size="small"><Descriptions column={1} size="small" title="防御效果">
            <Descriptions.Item label="DSR">{formatPercent(summary.dsr)}</Descriptions.Item>
            {summary.is_proxy && summary.defense_block_rate !== undefined && (
              <Descriptions.Item label="Proxy拦截率">{formatPercent(summary.defense_block_rate)}</Descriptions.Item>
            )}
            <Descriptions.Item label="误报率 (FPR)">{formatPercent(summary.fpr)}</Descriptions.Item>
            <Descriptions.Item label="漏报率 (FNR)">{formatPercent(summary.fnr)}</Descriptions.Item>
          </Descriptions></Card>
        </Col>
        <Col span={6}>
          <Card size="small"><Descriptions column={1} size="small" title="引擎运行时">
            <Descriptions.Item label="引擎风险分">
              <Tooltip title="来自 defense_proxy 的 cumulative_risk（跨层累积）">
                {formatScore(summary.risk_score)}
              </Tooltip>
            </Descriptions.Item>
            <Descriptions.Item label="主要拦截层">
              {(() => {
                const top = LAYER_ORDER
                  .map((ln) => ({ ln, blocked: layerStats[ln]?.blocked || 0 }))
                  .sort((a, b) => b.blocked - a.blocked)[0];
                return top?.blocked > 0 ? (DefenseLayerLabel[top.ln] || top.ln) : '—';
              })()}
            </Descriptions.Item>
            <Descriptions.Item label="实验ID"><code>{runId}</code></Descriptions.Item>
          </Descriptions></Card>
        </Col>
        <Col span={6}>
          <Card size="small"><Descriptions column={1} size="small" title="扩展指标">
            <Descriptions.Item label="PRP">
              <Tooltip title="需RAG检索日志支持，当前实验未采集">
                {fmtMaybe(summary.prp, formatPercent)}
              </Tooltip>
            </Descriptions.Item>
            <Descriptions.Item label="BTR">{fmtMaybe(summary.btr, formatPercent)}</Descriptions.Item>
            <Descriptions.Item label="H_cum">
              <Tooltip title="参数待标定">—</Tooltip>
            </Descriptions.Item>
          </Descriptions></Card>
        </Col>
      </Row>

      {/* Agent 对比 (Exp2 等) */}
      {summary.agent_comparison && (() => {
        const ac = summary.agent_comparison;
        const afm = summary.agent_family_matrix || {};
        const agents = ac.labels;
        const agentColors = ['#1677ff', '#52c41a', '#722ed1', '#fa8c16', '#f5222d'];
        const famOrder = ['prompt_injection','jailbreak','encoding_obfuscation','zero_width','context_escalation','pii_leakage','memory_poisoning','tool_misuse','multi_turn_composite'];
        const famLabels: Record<string,string> = {prompt_injection:'提示注入',jailbreak:'越狱改写',encoding_obfuscation:'编码混淆',zero_width:'零宽字符',context_escalation:'上下文越权',pii_leakage:'PII泄露',memory_poisoning:'记忆投毒',tool_misuse:'工具滥用',multi_turn_composite:'多轮复合'};

        // DSR bar chart
        const dsrBarOpt = {
          tooltip: { trigger: 'axis' as const, formatter: (p: any) => `${p[0].name}: ${(p[0].value*100).toFixed(1)}%` },
          grid: { left: 50, right: 20, top: 20, bottom: 30 },
          xAxis: { type: 'category' as const, data: agents, axisLabel: { fontSize: 10 } },
          yAxis: { type: 'value' as const, name: 'DSR', max: 1.1, axisLabel: { formatter: (v: number) => `${(v*100).toFixed(0)}%` } },
          series: [{
            type: 'bar', data: ac.dsr.map((v,i) => ({value: v, itemStyle: {color: agentColors[i]}})),
            label: { show: true, position: 'top' as const, formatter: (p: any) => `${(p.value*100).toFixed(1)}%` },
          }],
        };

        // Stacked verdict bar
        const stackOpt = {
          tooltip: { trigger: 'axis' as const },
          legend: { data: ['Blocked','Refused','Compromised'], bottom: 0 },
          grid: { left: 50, right: 20, top: 20, bottom: 40 },
          xAxis: { type: 'category' as const, data: agents, axisLabel: { fontSize: 10 } },
          yAxis: { type: 'value' as const, name: '样本数', max: 50 },
          series: [
            { name: 'Blocked', type: 'bar', stack: 't', data: ac.blocked, itemStyle: { color: '#f5222d' } },
            { name: 'Refused', type: 'bar', stack: 't', data: ac.refused, itemStyle: { color: '#fa8c16' } },
            { name: 'Compromised', type: 'bar', stack: 't', data: ac.compromised, itemStyle: { color: '#722ed1' } },
          ],
        };

        // Agent-family heatmap
        const heatData: [number,number,number][] = [];
        for (let fi=0; fi<famOrder.length; fi++) {
          for (let ai=0; ai<agents.length; ai++) {
            heatData.push([ai, fi, afm[famOrder[fi]]?.[agents[ai]] || 0]);
          }
        }
        const agentHeatOpt = {
          tooltip: { position: 'top' as const, formatter: (p: any) => { const [ai,fi,v]=p.data||[0,0,0]; return `${agents[ai]} × ${famLabels[famOrder[fi]]}<br/>DSR: ${(v*100).toFixed(1)}%`; }},
          grid: { left: 100, right: 40, top: 20, bottom: 30 },
          xAxis: { type: 'category' as const, data: agents.map((a: string) => a.slice(0,8)), splitArea: { show: true }, axisLabel: { fontSize: 9 } },
          yAxis: { type: 'category' as const, data: famOrder.map((f: string) => famLabels[f]||f), splitArea: { show: true }, axisLabel: { fontSize: 10 } },
          visualMap: { min: 0, max: 1, calculable: true, orient: 'horizontal' as const, left: 'center', bottom: 0, itemWidth: 12, itemHeight: 80, inRange: { color: ['#f0f5ff','#1677ff','#002c8c'] } },
          series: [{ type: 'heatmap', data: heatData, label: { show: true, fontSize: 10, formatter: (p: any) => p.data?.[2]>0?`${(p.data[2]*100).toFixed(0)}%`:'' } }],
        };

        return (<>
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col span={10}>
              <Card title="5 Agent DSR 对比" size="small">
                <ReactECharts option={dsrBarOpt} style={{ height: 300 }} />
              </Card>
            </Col>
            <Col span={14}>
              <Card title="Verdict 堆叠分布（Blocked / Refused / Compromised）" size="small">
                <ReactECharts option={stackOpt} style={{ height: 300 }} />
              </Card>
            </Col>
          </Row>
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col span={14}>
              <Card title="攻击族 × Agent DSR 热力图" size="small">
                <ReactECharts option={agentHeatOpt} style={{ height: 400 }} />
              </Card>
            </Col>
            <Col span={10}>
              <Card title="Agent 防御指标明细" size="small">
                <Table
                  dataSource={agents.map((agent: string, i: number) => ({
                    key: agent,
                    agent: agent.length > 14 ? agent.slice(0, 14) + '…' : agent,
                    dsr: ac.dsr[i],
                    blocked: ac.blocked[i],
                    refused: ac.refused[i],
                    compromised: ac.compromised[i],
                  }))}
                  columns={[
                    { title: 'Agent', dataIndex: 'agent', key: 'agent', width: 130 },
                    { title: 'DSR', dataIndex: 'dsr', key: 'dsr', width: 70, render: (v: number) => <span style={{ fontWeight: 600, color: v >= 0.9 ? '#52c41a' : v >= 0.7 ? '#faad14' : '#f5222d' }}>{(v * 100).toFixed(1)}%</span> },
                    { title: '拦截', dataIndex: 'blocked', key: 'blocked', width: 60 },
                    { title: '拒绝', dataIndex: 'refused', key: 'refused', width: 60 },
                    { title: '突破', dataIndex: 'compromised', key: 'compromised', width: 60 },
                  ]}
                  size="small"
                  pagination={false}
                />
                <div style={{ marginTop: 12, fontSize: 12, color: '#666' }}>
                  <div>• <b>拦截 (Blocked)</b>: defense_proxy 直接拦截</div>
                  <div>• <b>拒绝 (Refused)</b>: LLM 拒绝执行</div>
                  <div>• <b>突破 (Compromised)</b>: 攻击成功</div>
                  <div style={{ marginTop: 4 }}>DSR = (拦截 + 拒绝) / 总攻击样本</div>
                </div>
              </Card>
            </Col>
          </Row>
        </>);
      })()}

      {/* Verdict 分布饼图 + L1-L5 逐层拦截 (非Agent对比) */}
      {!summary.agent_comparison && (<>
      {(() => {
        const vc = summary.verdict_counts;
        const pieData: { name: string; value: number; itemStyle: { color: string } }[] = [];
        if (vc) {
          const vcAttack = vc.attack || {};
          const colorMap: Record<string, string> = {
            blocked: '#f5222d',
            refused: '#fa8c16',
            compromised: '#722ed1',
            warned: '#faad14',
            passed: '#52c41a',
            error: '#8c8c8c',
          };
          for (const [k, v] of Object.entries(vcAttack)) {
            if (v > 0) pieData.push({ name: k, value: v, itemStyle: { color: colorMap[k] || '#8c8c8c' } });
          }
          const vcBenign = vc.benign || {};
          const benignPassed = vcBenign.passed || 0;
          if (benignPassed > 0) {
            pieData.push({ name: 'benign_passed', value: benignPassed, itemStyle: { color: '#1677ff' } });
          }
        }
        if (pieData.length === 0) return null;

        const verdictPieOption = {
          tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
          legend: { orient: 'vertical', left: 0, top: 20 },
          series: [{
            name: 'Verdict', type: 'pie',
            radius: ['40%', '70%'], center: ['60%', '50%'],
            avoidLabelOverlap: false,
            label: { show: true, formatter: '{b}\n{c}' },
            emphasis: { label: { fontSize: 14, fontWeight: 'bold' } },
            data: pieData,
          }],
        };

        return (
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col span={8}>
              <Card title="样本 Verdict 分布" size="small">
                <ReactECharts option={verdictPieOption} style={{ height: 260 }} />
              </Card>
            </Col>
            <Col span={16} />
          </Row>
        );
      })()}

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Card title="L1-L5 逐层拦截贡献" size="small">
            <ReactECharts option={layerBarOption} style={{ height: 280 }} />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="攻击族 × 防御层 热力图" size="small">
            <ReactECharts option={heatOption} style={{ height: 280 }} />
          </Card>
        </Col>
      </Row>
      </>)}

      {/* 风险分布 + 命中规则 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card title="引擎累积风险分布" size="small">
            <ReactECharts option={riskDistOption} style={{ height: 220 }} />
          </Card>
        </Col>
        <Col span={8}>
          <Card title="命中规则 Top-10" size="small">
            <Table
              dataSource={summary.hit_rules?.slice(0, 10) || []}
              columns={hitRuleColumns}
              rowKey="rule_id"
              size="small"
              pagination={false}
              locale={{ emptyText: '无规则命中数据' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small" title="引擎运行时数据契约">
            <div style={{ fontSize: 12, color: '#666', lineHeight: 1.8 }}>
              <div>每层产出: passed / action / r<sub>i</sub> / flags / matched_rules / trust_level / ms</div>
              <div>累积: cumulative_risk = min(1.0, Σr<sub>i</sub>)</div>
              <div>信任衰减: trust<sub>new</sub> = max(0, trust<sub>in</sub> − r<sub>i</sub>)</div>
              <div style={{ marginTop: 4 }}>
                {LAYER_ORDER.map((ln) => {
                  const ls = layerStats[ln];
                  return ls ? (
                    <Tag key={ln} color={defenseLayerColor[ln] || 'default'} style={{ marginBottom: 4 }}>
                      {DefenseLayerLabel[ln]?.slice(0, 4)} trust: {ls.avg_trust?.toFixed(2)}
                    </Tag>
                  ) : null;
                })}
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      {/* 攻击族对比 + 趋势 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Card title="各攻击族 ASR / DSR 对比" size="small">
            <ReactECharts option={familyBarOption} style={{ height: 300 }} />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="指标变化趋势" size="small">
            <ReactECharts option={trendOption} style={{ height: 300 }} />
          </Card>
        </Col>
      </Row>

      {/* 攻击族明细表 */}
      <Card title="按攻击族分拆指标" size="small">
        <Table dataSource={familyList} columns={familyColumns} rowKey="family" size="small" pagination={false} />
      </Card>
    </div>
  );
}
