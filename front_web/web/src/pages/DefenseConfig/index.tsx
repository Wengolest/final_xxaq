import { useEffect, useState } from 'react';
import {
  Card, Steps, Switch, Table, Button, Space, Tag, Descriptions, App, Empty,
} from 'antd';
import {
  SafetyOutlined, DatabaseOutlined, RobotOutlined, BranchesOutlined,
  ToolOutlined, AuditOutlined, PlusOutlined,
} from '@ant-design/icons';
import type { DefenseLayerConfig, DefenseRule } from '../../api/types';
import * as defenseApi from '../../api/defense';
import { DefenseLayer, DefenseLayerLabel } from '../../utils/constants';

const layerIcons: Record<DefenseLayer, React.ReactNode> = {
  [DefenseLayer.SOURCE_GOVERNANCE]: <DatabaseOutlined />,
  [DefenseLayer.MODEL_INTERACTION]: <RobotOutlined />,
  [DefenseLayer.MEMORY_CONTROL]: <BranchesOutlined />,
  [DefenseLayer.TOOL_CONSTRAINT]: <ToolOutlined />,
  [DefenseLayer.DECISION_SUPERVISION]: <AuditOutlined />,
};

const layerColors: Record<DefenseLayer, string> = {
  [DefenseLayer.SOURCE_GOVERNANCE]: '#13c2c2',
  [DefenseLayer.MODEL_INTERACTION]: '#1677ff',
  [DefenseLayer.MEMORY_CONTROL]: '#2f54eb',
  [DefenseLayer.TOOL_CONSTRAINT]: '#5956d4',
  [DefenseLayer.DECISION_SUPERVISION]: '#722ed1',
};

const actionConfig: Record<string, { color: string; text: string }> = {
  block: { color: '#f5222d', text: '阻断' },
  warn: { color: '#faad14', text: '警告' },
  log: { color: '#1677ff', text: '日志' },
  quarantine: { color: '#fa8c16', text: '隔离' },
};

export default function DefenseConfig() {
  const { message: msg } = App.useApp();
  const [layers, setLayers] = useState<DefenseLayerConfig[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    defenseApi.getDefenseLayers().then((data) => {
      setLayers(data);
      setLoading(false);
    });
  }, []);

  const toggleLayer = async (layer: DefenseLayer, enabled: boolean) => {
    await defenseApi.updateDefenseConfig({ layer, enabled });
    setLayers((prev) => prev.map((l) => (l.layer === layer ? { ...l, enabled } : l)));
    msg.success(`${DefenseLayerLabel[layer]}: ${enabled ? '已启用' : '已禁用'}`);
  };

  // 当前激活的防御层
  const currentStep = (() => {
    const enabledLayers = layers.filter((l) => l.enabled);
    return enabledLayers.length;
  })();

  const ruleColumns = [
    { title: '规则ID', dataIndex: 'rule_id', key: 'rule_id', width: 100 },
    { title: '名称', dataIndex: 'name', key: 'name', width: 160 },
    { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
    {
      title: '动作', dataIndex: 'action', key: 'action', width: 80,
      render: (a: string) => {
        const cfg = actionConfig[a];
        return cfg ? <Tag color={cfg.color}>{cfg.text}</Tag> : a;
      },
    },
    {
      title: '优先级', dataIndex: 'priority', key: 'priority', width: 80,
    },
    {
      title: '启用', key: 'enabled', width: 80,
      render: (_: unknown, r: DefenseRule) => (
        <Switch size="small" checked={r.enabled} onChange={(v) => {
          r.enabled = v;
          setLayers([...layers]);
        }} />
      ),
    },
  ];

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>防御配置</h2>

      {/* 五层防御流程可视化 */}
      <Card title={<span><SafetyOutlined /> 五层防御架构概览</span>} style={{ marginBottom: 24 }} loading={loading}>
        <Steps
          current={currentStep}
          status={currentStep > 0 ? 'process' : 'wait'}
          direction="vertical"
          items={layers.map((l) => ({
            title: (
              <Space>
                <span style={{ fontWeight: 600, color: l.enabled ? layerColors[l.layer] : '#ccc' }}>
                  {l.label}
                </span>
                <Switch
                  size="small"
                  checked={l.enabled}
                  onChange={(v) => toggleLayer(l.layer, v)}
                />
              </Space>
            ),
            description: l.description,
            icon: l.enabled ? layerIcons[l.layer] : undefined,
            status: l.enabled ? ('process' as const) : ('wait' as const),
          }))}
        />
      </Card>

      {/* 每层展开的配置详情 */}
      {layers.map((l) => (
        <Card
          key={l.layer}
          title={
            <Space>
              <span style={{ color: layerColors[l.layer], fontWeight: 600 }}>
                {layerIcons[l.layer]} {l.label}
              </span>
              <Tag color={l.enabled ? '#52c41a' : '#d9d9d9'}>
                {l.enabled ? '已启用' : '已禁用'}
              </Tag>
            </Space>
          }
          style={{ marginBottom: 16 }}
        >
          <Descriptions column={2} size="small" style={{ marginBottom: 12 }}>
            <Descriptions.Item label="防护对象">{l.description}</Descriptions.Item>
            <Descriptions.Item label="参数">
              {Object.entries(l.params).map(([k, v]) => (
                <Tag key={k}>{k}: {JSON.stringify(v)}</Tag>
              ))}
            </Descriptions.Item>
          </Descriptions>
          <div style={{ marginBottom: 8, display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ fontWeight: 600 }}>防御规则</span>
            <Button
              size="small" type="dashed" icon={<PlusOutlined />}
              onClick={() => msg.info('添加规则功能已预留')}
            >
              添加规则
            </Button>
          </div>
          <Table
            dataSource={l.rules}
            columns={ruleColumns}
            rowKey="rule_id"
            size="small"
            pagination={false}
            locale={{ emptyText: <Empty description="暂无规则" /> }}
          />
        </Card>
      ))}
    </div>
  );
}
