import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Table, Button, Space, Tag, Modal, Form, Input, Select, App, Badge, Switch, Progress,
  InputNumber, Divider, Collapse, Row, Col,
} from 'antd';
import {
  PlusOutlined, PlayCircleOutlined, StopOutlined, EyeOutlined, BarChartOutlined,
  ImportOutlined, ClearOutlined,
} from '@ant-design/icons';
import type { Experiment } from '../../api/types';
import { useExperimentStore } from '../../store/experimentStore';
import { useTargetStore } from '../../store/targetStore';
import { formatDateTime } from '../../utils/formatters';
import {
  AttackFamilyLabel, DefenseLayerLabel, ExperimentStatus as ExpStatus,
  AttackFamily, DefenseLayer,
} from '../../utils/constants';
import { experimentStatusColor, attackFamilyColor } from '../../utils/colorMap';

const statusLabel: Record<string, string> = {
  draft: '草稿', pending: '等待中', running: '运行中',
  completed: '已完成', failed: '失败', stopped: '已停止',
};

export default function ExperimentCenter() {
  const navigate = useNavigate();
  const { message: msg } = App.useApp();
  const { experiments, loading, fetchExperiments, createExperiment, startExperiment, stopExperiment, createManualExperiment } = useExperimentStore();
  const { targets, fetchTargets } = useTargetStore();
  const [modalOpen, setModalOpen] = useState(false);
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [form] = Form.useForm();
  const [importForm] = Form.useForm();
  const [advOpen, setAdvOpen] = useState(false);

  useEffect(() => {
    fetchExperiments();
    fetchTargets();
  }, []);

  // 轮询: 有 running 状态的实验时每 2s 刷新
  useEffect(() => {
    const hasRunning = experiments.some((e) => e.status === ExpStatus.RUNNING);
    if (!hasRunning) return;
    const timer = setInterval(() => fetchExperiments(), 2000);
    return () => clearInterval(timer);
  }, [experiments, fetchExperiments]);

  const handleCreate = async () => {
    const values = await form.validateFields();
    await createExperiment({
      ...values,
      use_proxy: values.use_proxy || false,
    });
    msg.success(values.use_proxy ? 'Proxy 实验已启动，正在后台执行...' : '实验创建成功');
    setModalOpen(false);
    form.resetFields();
  };

  const handleStart = async (runId: string) => {
    await startExperiment(runId);
    msg.success('实验已启动');
  };

  const handleStop = async (runId: string) => {
    await stopExperiment(runId);
    msg.warning('实验已停止');
  };

  // ---- 手动导入 ----

  const generateTemplate = () => {
    const name = importForm.getFieldValue('name') || '手动实验';
    importForm.setFieldsValue({
      dsr: 0.95, asr: 0.05, fpr: 0.02,
      total_samples: 28, attack_samples: 23, benign_samples: 5,
      attack_blocked: 21, benign_blocked: 0,
      l1_blocked: 5, l2_blocked: 8, l3_blocked: 3, l4_blocked: 4, l5_blocked: 1,
      pi_dsr: 1.0, jb_dsr: 1.0, eo_dsr: 0.67, zw_dsr: 1.0, ce_dsr: 0.5, pii_dsr: 1.0, tm_dsr: 1.0, mp_dsr: 0.67, mc_dsr: 1.0,
      attack_refused: 0, attack_compromised: 0,
      defense_block_rate: 0, refusal_rate: 0,
      latency_p50: 1.5, latency_p99: 3.2,
      accuracy: 0.93,
    });
  };

  const validateJson = (_: unknown, value: string) => {
    if (!value) return Promise.resolve();
    try {
      const obj = JSON.parse(value);
      if (obj.metrics && typeof obj.metrics !== 'object') {
        return Promise.reject('metrics 字段必须是对象');
      }
      return Promise.resolve();
    } catch (e) {
      return Promise.reject(`JSON 格式错误: ${(e as Error).message}`);
    }
  };

  const handleImport = async () => {
    const values = await importForm.validateFields();

    // 构造 metrics dict
    const metrics: Record<string, unknown> = {
      dsr: values.dsr ?? 0,
      fpr: values.fpr ?? 0,
      total_samples: values.total_samples ?? 0,
      attack_samples: values.attack_samples ?? 0,
      benign_samples: values.benign_samples ?? 0,
      attack_blocked: values.attack_blocked ?? 0,
      benign_blocked: values.benign_blocked ?? 0,
      layer_blocked: {
        source_governance: values.l1_blocked ?? 0,
        model_interaction: values.l2_blocked ?? 0,
        memory_control: values.l3_blocked ?? 0,
        tool_constraint: values.l4_blocked ?? 0,
        decision_supervision: values.l5_blocked ?? 0,
      },
      family_dsr: {} as Record<string, unknown>,
      confusion_matrix: {
        TP: (values.attack_blocked ?? 0),
        FP: (values.benign_blocked ?? 0),
        FN: (values.attack_samples ?? 0) - (values.attack_blocked ?? 0),
        TN: (values.benign_samples ?? 0) - (values.benign_blocked ?? 0),
      },
      accuracy: values.accuracy ?? 0,
      latency_p50: values.latency_p50 ?? 0,
      latency_p99: values.latency_p99 ?? 0,
    };

    // 攻击族 DSR
    const familyKeys = ['prompt_injection', 'jailbreak', 'encoding_obfuscation', 'zero_width',
      'context_escalation', 'pii_leakage', 'tool_misuse', 'memory_poisoning', 'multi_turn_composite'];
    const familyFields: Record<string, number> = {
      prompt_injection: values.pi_dsr, jailbreak: values.jb_dsr,
      encoding_obfuscation: values.eo_dsr, zero_width: values.zw_dsr,
      context_escalation: values.ce_dsr, pii_leakage: values.pii_dsr,
      tool_misuse: values.tm_dsr, memory_poisoning: values.mp_dsr,
      multi_turn_composite: values.mc_dsr,
    };
    for (const fk of familyKeys) {
      (metrics.family_dsr as Record<string, unknown>)[fk] = {
        total: 3, blocked: Math.round((familyFields[fk] ?? 0) * 3), rate: familyFields[fk] ?? 0,
      };
    }

    // Proxy 模式额外字段
    if (values.is_proxy) {
      metrics.asr = values.asr ?? 0;
      metrics.refusal_rate = values.refusal_rate ?? 0;
      metrics.defense_block_rate = values.defense_block_rate ?? 0;
      metrics.attack_refused = values.attack_refused ?? 0;
      metrics.attack_compromised = values.attack_compromised ?? 0;
      metrics.is_proxy = true;
    }

    // 高级 JSON
    let results: unknown[] = [];
    let timeline: unknown[] = [];
    if (values.json_data) {
      const advanced = JSON.parse(values.json_data);
      if (advanced.results) results = advanced.results;
      if (advanced.timeline) timeline = advanced.timeline;
      // 高级 JSON 中的 metrics 覆盖表单 metrics
      if (advanced.metrics) Object.assign(metrics, advanced.metrics);
    }

    await createManualExperiment({
      name: values.name,
      mode: values.mode || 'balanced',
      is_proxy: values.is_proxy || false,
      attack_families: values.attack_families || [],
      metrics,
      results,
      timeline,
    });
    msg.success('实验导入成功');
    setImportModalOpen(false);
    importForm.resetFields();
    setAdvOpen(false);
  };

  const columns = [
    { title: '实验ID', dataIndex: 'run_id', key: 'run_id', width: 160, render: (id: string) => <code>{id}</code> },
    {
      title: '名称', dataIndex: 'name', key: 'name', width: 280, ellipsis: { showTitle: true },
      render: (name: string, r: Experiment) => (
        <Space size={4}>
          <span>{name}</span>
          {r.is_manual && <Tag color="blue" style={{ fontSize: 11 }}>手动</Tag>}
        </Space>
      ),
    },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 120,
      render: (s: string, r: Experiment) => {
        const isRunning = s === 'running';
        return (
          <Space size={4}>
            <Badge status={isRunning ? 'processing' : (s === 'completed' ? 'success' : (s === 'failed' ? 'error' : 'default'))}
              text={<Tag color={experimentStatusColor[s]}>{statusLabel[s] || s}</Tag>}
            />
            {r.is_proxy && <Tag color="purple" style={{ fontSize: 10 }}>PROXY</Tag>}
            {r.agent_type && <Tag color="cyan" style={{ fontSize: 10 }}>Agent {r.agent_type}</Tag>}
          </Space>
        );
      },
    },
    {
      title: '测试目标', key: 'targets', width: 120,
      render: (_: unknown, r: Experiment) => (
        <Space size={[2, 2]} wrap>{r.target_ids.map((id) => <Tag key={id}>{id}</Tag>)}</Space>
      ),
    },
    {
      title: '攻击族', key: 'attacks', width: 200,
      render: (_: unknown, r: Experiment) => (
        <Space size={[2, 2]} wrap>
          {r.attack_families.map((f) => (
            <Tag key={f} color={attackFamilyColor[f]}>{(AttackFamilyLabel[f] || f).slice(0, 8)}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '进度', dataIndex: 'progress', key: 'progress', width: 140,
      render: (p?: { percentage: number; completed?: number; total_samples?: number }) => {
        if (!p) return '-';
        return (
          <div>
            <Progress percent={p.percentage} size="small" style={{ width: 100 }} />
            {p.completed !== undefined && p.total_samples !== undefined && (
              <div style={{ fontSize: 11, color: '#888' }}>{p.completed}/{p.total_samples}</div>
            )}
          </div>
        );
      },
    },
    {
      title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 160,
      render: (v: string) => formatDateTime(v),
    },
    {
      title: '操作', key: 'actions', width: 220, fixed: 'right' as const,
      render: (_: unknown, r: Experiment) => (
        <Space size={4}>
          {r.status === ExpStatus.DRAFT || r.status === ExpStatus.PENDING ? (
            <Button size="small" type="primary" icon={<PlayCircleOutlined />} onClick={() => handleStart(r.run_id)}>启动</Button>
          ) : null}
          {r.status === ExpStatus.RUNNING ? (
            <Button size="small" danger icon={<StopOutlined />} onClick={() => handleStop(r.run_id)}>停止</Button>
          ) : null}
          <Button size="small" icon={<EyeOutlined />} onClick={() => navigate(`/experiments/${r.run_id}`)}>详情</Button>
          {(r.status === ExpStatus.COMPLETED || r.status === ExpStatus.RUNNING) && (
            <Button size="small" icon={<BarChartOutlined />} onClick={() => navigate(`/results/${r.run_id}`)}>结果</Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>实验编排中心</h2>
        <Space>
          <Button icon={<ImportOutlined />} onClick={() => setImportModalOpen(true)}>
            手动导入
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
            创建新实验
          </Button>
        </Space>
      </div>

      <Table
        dataSource={experiments}
        columns={columns}
        rowKey="run_id"
        loading={loading}
        scroll={{ x: 1400 }}
      />

      <Modal
        title="创建新实验"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleCreate}
        width={640}
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="实验名称" rules={[{ required: true }]}>
            <Input placeholder="例如：第N轮：目标X-攻击族Y测试" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="target_ids" label="测试目标" rules={[{ required: true }]}>
            <Select mode="multiple" placeholder="选择Agent目标">
              {targets.map((t) => (
                <Select.Option key={t.id} value={t.id}>{t.name} ({t.id})</Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="attack_families" label="攻击族" rules={[{ required: true }]}>
            <Select mode="multiple" placeholder="选择攻击类型（按Ctrl多选）">
              {Object.entries(AttackFamilyLabel).map(([k, v]) => (
                <Select.Option key={k} value={k}>{v}</Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="defense_layers" label="防御层">
            <Select mode="multiple" placeholder="选择启用的防御层（留空=全部启用）">
              {Object.entries(DefenseLayerLabel).map(([k, v]) => (
                <Select.Option key={k} value={k}>{v}</Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="agent_type" label="Agent 类型">
            <Select placeholder="选择 Agent（留空=直接 HTTP 请求 defense_proxy）" allowClear>
              <Select.Option value="chat">Agent A — 纯对话 (ChatAgent)</Select.Option>
              <Select.Option value="tool">Agent B — 工具调用 (ToolAgent)</Select.Option>
              <Select.Option value="rag">Agent C — RAG 知识助手 (RAGAgent)</Select.Option>
            </Select>
            <span style={{ marginLeft: 8, color: '#888', fontSize: 12 }}>
              Agent D/E 请用独立脚本 (<code>D:\defense_venv</code>)
            </span>
          </Form.Item>
          <Form.Item name="use_proxy" label="Proxy 模式" valuePropName="checked">
            <Switch
              checkedChildren="经真实 LLM"
              unCheckedChildren="规则引擎"
            />
            <span style={{ marginLeft: 8, color: '#888', fontSize: 12 }}>
              开启后样本经 defense_proxy → DeepSeek，获取真实 ASR / refusal_rate（约1-2分钟）
            </span>
          </Form.Item>
        </Form>
      </Modal>

      {/* ---- 手动导入 Modal ---- */}
      <Modal
        title="手动导入实验数据"
        open={importModalOpen}
        onCancel={() => { setImportModalOpen(false); importForm.resetFields(); setAdvOpen(false); }}
        onOk={handleImport}
        width={760}
        destroyOnClose
        okText="导入"
        cancelText="取消"
      >
        <Form form={importForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="实验名称" rules={[{ required: true, message: '请输入实验名称' }]}>
            <Input placeholder="例如：论文实验1-规则基准-STRICT模式" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="mode" label="防御模式" initialValue="balanced">
                <Select>
                  <Select.Option value="balanced">BALANCED (默认)</Select.Option>
                  <Select.Option value="strict">STRICT</Select.Option>
                  <Select.Option value="permissive">PERMISSIVE</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="is_proxy" label="Proxy 模式" valuePropName="checked" initialValue={false}>
                <Switch checkedChildren="Proxy" unCheckedChildren="规则" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="attack_families" label="攻击族">
            <Select mode="multiple" placeholder="选择攻击族（留空=全部）" allowClear>
              {Object.entries(AttackFamilyLabel).map(([k, v]) => (
                <Select.Option key={k} value={k}>{v}</Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Divider plain style={{ fontSize: 13, color: '#888' }}>汇总指标</Divider>
          <Row gutter={12}>
            <Col span={8}>
              <Form.Item name="dsr" label="DSR" initialValue={0}><InputNumber min={0} max={1} step={0.01} style={{ width: '100%' }} /></Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="asr" label="ASR" initialValue={0}><InputNumber min={0} max={1} step={0.01} style={{ width: '100%' }} /></Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="fpr" label="FPR" initialValue={0}><InputNumber min={0} max={1} step={0.01} style={{ width: '100%' }} /></Form.Item>
            </Col>
          </Row>
          <Row gutter={12}>
            <Col span={8}>
              <Form.Item name="total_samples" label="总样本"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="attack_samples" label="攻击样本"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="benign_samples" label="良性样本"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
            </Col>
          </Row>
          <Row gutter={12}>
            <Col span={8}>
              <Form.Item name="attack_blocked" label="拦截数"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="benign_blocked" label="误拦数"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="accuracy" label="准确率" initialValue={0}><InputNumber min={0} max={1} step={0.01} style={{ width: '100%' }} /></Form.Item>
            </Col>
          </Row>

          {/* Proxy 专属字段 */}
          <Form.Item noStyle shouldUpdate={(prev, cur) => prev.is_proxy !== cur.is_proxy}>
            {({ getFieldValue }) =>
              getFieldValue('is_proxy') ? (
                <Row gutter={12}>
                  <Col span={6}>
                    <Form.Item name="defense_block_rate" label="Proxy拦截率" initialValue={0}><InputNumber min={0} max={1} step={0.01} style={{ width: '100%' }} /></Form.Item>
                  </Col>
                  <Col span={6}>
                    <Form.Item name="refusal_rate" label="拒答率" initialValue={0}><InputNumber min={0} max={1} step={0.01} style={{ width: '100%' }} /></Form.Item>
                  </Col>
                  <Col span={6}>
                    <Form.Item name="attack_refused" label="LLM拒绝数"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
                  </Col>
                  <Col span={6}>
                    <Form.Item name="attack_compromised" label="攻破数"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
                  </Col>
                </Row>
              ) : null
            }
          </Form.Item>

          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="latency_p50" label="P50延迟(ms)"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="latency_p99" label="P99延迟(ms)"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
            </Col>
          </Row>

          <Divider plain style={{ fontSize: 13, color: '#888' }}>各层拦截分布</Divider>
          <Row gutter={12}>
            <Col span={4}>
              <Form.Item name="l1_blocked" label="L1 源头"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
            </Col>
            <Col span={5}>
              <Form.Item name="l2_blocked" label="L2 交互"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item name="l3_blocked" label="L3 记忆"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
            </Col>
            <Col span={5}>
              <Form.Item name="l4_blocked" label="L4 工具"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="l5_blocked" label="L5 决策"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
            </Col>
          </Row>

          <Divider plain style={{ fontSize: 13, color: '#888' }}>各攻击族 DSR</Divider>
          <Row gutter={12}>
            <Col span={8}>
              <Form.Item name="pi_dsr" label="提示注入" initialValue={0}><InputNumber min={0} max={1} step={0.01} style={{ width: '100%' }} /></Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="jb_dsr" label="越狱" initialValue={0}><InputNumber min={0} max={1} step={0.01} style={{ width: '100%' }} /></Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="eo_dsr" label="编码混淆" initialValue={0}><InputNumber min={0} max={1} step={0.01} style={{ width: '100%' }} /></Form.Item>
            </Col>
          </Row>
          <Row gutter={12}>
            <Col span={8}>
              <Form.Item name="zw_dsr" label="零宽字符" initialValue={0}><InputNumber min={0} max={1} step={0.01} style={{ width: '100%' }} /></Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="ce_dsr" label="上下文越权" initialValue={0}><InputNumber min={0} max={1} step={0.01} style={{ width: '100%' }} /></Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="pii_dsr" label="PII泄露" initialValue={0}><InputNumber min={0} max={1} step={0.01} style={{ width: '100%' }} /></Form.Item>
            </Col>
          </Row>
          <Row gutter={12}>
            <Col span={8}>
              <Form.Item name="tm_dsr" label="工具滥用" initialValue={0}><InputNumber min={0} max={1} step={0.01} style={{ width: '100%' }} /></Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="mp_dsr" label="记忆投毒" initialValue={0}><InputNumber min={0} max={1} step={0.01} style={{ width: '100%' }} /></Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="mc_dsr" label="复合攻击" initialValue={0}><InputNumber min={0} max={1} step={0.01} style={{ width: '100%' }} /></Form.Item>
            </Col>
          </Row>

          <Collapse
            activeKey={advOpen ? ['adv'] : []}
            onChange={(keys) => setAdvOpen(keys.length > 0)}
            items={[{
              key: 'adv',
              label: '高级 — 粘贴 results / timeline JSON',
              children: (
                <div>
                  <div style={{ marginBottom: 8 }}>
                    <Space>
                      <Button size="small" onClick={generateTemplate}>生成模板</Button>
                      <Button size="small" icon={<ClearOutlined />} onClick={() => importForm.setFieldValue('json_data', '')}>清空</Button>
                    </Space>
                    <span style={{ marginLeft: 8, color: '#888', fontSize: 12 }}>
                      将 defense_proxy 返回的完整 results/timeline 直接贴入
                    </span>
                  </div>
                  <Form.Item name="json_data" rules={[{ validator: validateJson }]}>
                    <Input.TextArea
                      rows={10}
                      placeholder={`粘贴完整 results 和 timeline JSON...\n\n{"results": [...], "timeline": [...]}`}
                      style={{ fontFamily: 'Consolas, Monaco, monospace', fontSize: 12 }}
                    />
                  </Form.Item>
                </div>
              ),
            }]}
          />
        </Form>
      </Modal>
    </div>
  );
}
