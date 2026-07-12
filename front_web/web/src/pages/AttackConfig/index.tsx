import { useEffect, useState } from 'react';
import {
  Tabs, Card, Row, Col, Table, Tag, Button, Space, Popconfirm, App, Descriptions,
} from 'antd';
import {
  PlusOutlined, ThunderboltOutlined, BranchesOutlined, DeleteOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import type { AttackFamilyNode, AttackSample } from '../../api/types';
import { useTargetStore } from '../../store/targetStore';
import * as attackApi from '../../api/attack';
import {
  AttackFamily, AttackFamilyLabel, AttackCategory, RiskLevelLabel,
} from '../../utils/constants';
import { attackFamilyColor, riskLevelColor } from '../../utils/colorMap';
import { formatPercent, formatScore } from '../../utils/formatters';

// 攻击族分类（对应文档六大族系）
const DIRECT_FAMILIES: AttackFamily[] = [
  AttackFamily.PROMPT_INJECTION, AttackFamily.JAILBREAK,
  AttackFamily.ENCODING_OBFUSCATION, AttackFamily.PAYLOAD_SPLIT,
];
const ENV_FAMILIES: AttackFamily[] = [
  AttackFamily.RAG_POISONING, AttackFamily.MEMORY_POISONING,
  AttackFamily.TOOL_OUTPUT_POISONING, AttackFamily.SKILL_MCP_POISONING,
  AttackFamily.CHAIN_OF_THOUGHT_ATTACK, AttackFamily.OPINION_POISONING,
  AttackFamily.MULTI_AGENT_POISONING, AttackFamily.SUPPLY_CHAIN,
];

const categoryLabel: Record<AttackCategory, string> = {
  [AttackCategory.DIRECT_INPUT]: '直接输入类',
  [AttackCategory.ENVIRONMENTAL]: '环境/供应链式投毒',
};

export default function AttackConfig() {
  const { message: msg } = App.useApp();
  const { targets } = useTargetStore();
  const [families, setFamilies] = useState<AttackFamilyNode[]>([]);
  const [samples, setSamples] = useState<AttackSample[]>([]);
  const [fLoading, setFLoading] = useState(true);
  const [variantLoading, setVariantLoading] = useState<string | null>(null);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    setFLoading(true);
    const [f, s] = await Promise.all([attackApi.getAttackFamilies(), attackApi.getAttackSamples()]);
    setFamilies(f);
    setSamples(s);
    setFLoading(false);
  };

  const handleGenerateVariant = async (caseId: string) => {
    if (targets.length === 0) {
      msg.warning('请先在目标管理中注册至少一个Agent目标');
      return;
    }
    setVariantLoading(caseId);
    try {
      await attackApi.generateVariants(caseId, targets[0].id);
      msg.success('变体生成完成，请到"变体分析"页面查看');
    } catch {
      msg.error('变体生成失败');
    }
    setVariantLoading(null);
  };

  // 各攻击族风险气泡图（数据集中在右上区域，缩小坐标范围以分散气泡）
  const bubbleOption = {
    tooltip: {
      formatter: (p: { name: string; value: number[] }) => {
        const [x, y, size] = p.value;
        return `${p.name}<br/>ASR: ${formatPercent(x)} | Impact: ${formatPercent(y)} | Stealth: ${formatPercent(size)}`;
      },
    },
    grid: { left: 65, right: 40, top: 20, bottom: 50 },
    xAxis: {
      name: 'ASR (攻击成功率)',
      nameLocation: 'center',
      nameGap: 30,
      min: 0.3,
      max: 0.8,
      axisLabel: { formatter: (v: number) => formatPercent(v, 0) },
    },
    yAxis: {
      name: 'Impact (影响范围)',
      nameLocation: 'center',
      nameGap: 40,
      min: 0.5,
      max: 1.05,
      axisLabel: { formatter: (v: number) => formatPercent(v, 0) },
    },
    series: [{
      type: 'scatter',
      symbolSize: (data: number[]) => Math.max(12, (data[2] - 0.7) * 140 + 14),
      data: families.map((f) => ({
        name: f.label,
        value: [f.asr, f.impact, f.stealth],
        itemStyle: { color: attackFamilyColor[f.family] || '#999', opacity: 0.85 },
      })),
      label: {
        show: true,
        formatter: ({ name }: { name: string }) => name.length > 4 ? name.slice(0, 4) + '...' : name,
        fontSize: 10,
        position: 'top',
        distance: 6,
      },
      emphasis: { scale: 1.6 },
    }],
  };

  // 样本表格列
  const sampleColumns = [
    { title: 'ID', dataIndex: 'case_id', key: 'case_id', width: 100 },
    {
      title: '攻击族', dataIndex: 'family', key: 'family', width: 150,
      render: (f: AttackFamily) => (
        <Tag color={attackFamilyColor[f]}>{AttackFamilyLabel[f]}</Tag>
      ),
    },
    { title: '攻击目标', dataIndex: 'attack_goal', key: 'attack_goal', ellipsis: true },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 80,
      render: (s: string) => {
        const m: Record<string, { color: string; text: string }> = {
          active: { color: '#52c41a', text: '可用' },
          pending: { color: '#faad14', text: '待验证' },
          unstable: { color: '#fa8c16', text: '不稳定' },
          deprecated: { color: '#d9d9d9', text: '已废弃' },
        };
        return <Tag color={m[s]?.color}>{m[s]?.text || s}</Tag>;
      },
    },
    {
      title: '操作', key: 'actions', width: 200, fixed: 'right' as const,
      render: (_: unknown, r: AttackSample) => (
        <Space size={4}>
          <Button size="small" icon={<BranchesOutlined />}
            onClick={() => handleGenerateVariant(r.case_id)}
            loading={variantLoading === r.case_id}>
            生成变体
          </Button>
          <Popconfirm title="确定删除？" onConfirm={() => attackApi.deleteSample(r.case_id).then(loadData)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // 攻击族卡片
  const renderFamilyCards = (familyList: AttackFamily[]) => {
    return (
      <Row gutter={[16, 16]}>
        {familyList.map((fam) => {
          const f = families.find((x) => x.family === fam);
          if (!f) return null;
          return (
            <Col xs={24} sm={12} lg={8} key={f.family}>
              <Card
                size="small"
                title={
                  <Space>
                    <span style={{ color: attackFamilyColor[f.family], fontWeight: 600, fontSize: 14 }}>
                      {f.label}
                    </span>
                    <Tag color={riskLevelColor[f.risk_level]}>
                      Lv.{f.risk_level} {RiskLevelLabel[f.risk_level]}
                    </Tag>
                  </Space>
                }
              >
                <Descriptions column={1} size="small" colon={false}>
                  <Descriptions.Item label="分类">
                    <Tag>{categoryLabel[f.category as AttackCategory]}</Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="典型载体">
                    {f.typical_carriers.join(', ')}
                  </Descriptions.Item>
                  <Descriptions.Item label="风险评分">
                    <span style={{ fontWeight: 600, color: riskLevelColor[f.risk_level] }}>
                      {formatScore(f.risk_score)}
                    </span>
                    <span style={{ fontSize: 11, color: '#999', marginLeft: 4 }}>
                      (ASR:{formatPercent(f.asr)} Impact:{formatPercent(f.impact)} Stealth:{formatPercent(f.stealth)})
                    </span>
                  </Descriptions.Item>
                  <Descriptions.Item label="描述">{f.description}</Descriptions.Item>
                </Descriptions>
              </Card>
            </Col>
          );
        })}
      </Row>
    );
  };

  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>攻击配置</h2>

      <Tabs
        defaultActiveKey="families"
        items={[
          {
            key: 'families',
            label: <span><ThunderboltOutlined /> 攻击族谱系</span>,
            children: (
              <div>
                {/* 攻击族气泡图 */}
                <Card title="攻击族风险分布 (ASR × Impact × Stealth)" style={{ marginBottom: 16 }}>
                  <ReactECharts option={bubbleOption} style={{ height: 420 }} showLoading={fLoading} />
                </Card>

                {/* 直接输入类 */}
                <h3 style={{ margin: '16px 0 12px' }}>
                  <Tag color="#1677ff">直接输入类</Tag>
                  恶意内容主要通过当前用户请求进入系统
                </h3>
                {fLoading ? null : renderFamilyCards(DIRECT_FAMILIES)}

                {/* 环境/供应链式投毒 */}
                <h3 style={{ margin: '24px 0 12px' }}>
                  <Tag color="#fa8c16">环境/供应链式投毒</Tag>
                  攻击者先污染外部环境，再通过正常请求触发
                </h3>
                {fLoading ? null : renderFamilyCards(ENV_FAMILIES)}
              </div>
            ),
          },
          {
            key: 'samples',
            label: <span><BranchesOutlined /> 攻击样本 ({samples.length})</span>,
            children: (
              <div>
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
                  <Button type="primary" icon={<PlusOutlined />}
                    onClick={() => msg.info('样本编辑功能已预留，可在此扩展表单逻辑')}>
                    新建样本
                  </Button>
                </div>
                <Table
                  dataSource={samples}
                  columns={sampleColumns}
                  rowKey="case_id"
                  size="middle"
                  loading={fLoading}
                  expandable={{
                    expandedRowRender: (r) => (
                      <div style={{ padding: '0 16px 16px' }}>
                        <h4>载荷 (Payload)</h4>
                        <pre style={{
                          background: '#f5f5f5', padding: 12, borderRadius: 6,
                          maxHeight: 200, overflow: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-all',
                        }}>
                          {r.payload}
                        </pre>
                        {r.trigger_query && (
                          <>
                            <h4 style={{ marginTop: 8 }}>触发查询</h4>
                            <pre style={{
                              background: '#f5f5f5', padding: 12, borderRadius: 6,
                              whiteSpace: 'pre-wrap', wordBreak: 'break-all',
                            }}>
                              {r.trigger_query}
                            </pre>
                          </>
                        )}
                      </div>
                    ),
                  }}
                />
              </div>
            ),
          },
        ]}
      />
    </div>
  );
}
