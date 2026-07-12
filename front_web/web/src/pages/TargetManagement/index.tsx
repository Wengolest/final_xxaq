import { useEffect, useState } from 'react';
import {
  Table, Button, Space, Tag, Modal, Form, Input, InputNumber,
  Select, Popconfirm, Tooltip, Badge, App,
} from 'antd';
import {
  PlusOutlined, ReloadOutlined, EditOutlined, DeleteOutlined, LinkOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { TargetAgent } from '../../api/types';
import { useTargetStore } from '../../store/targetStore';
import { formatDateTime } from '../../utils/formatters';
import { AgentCapability, AgentCapabilityLabel } from '../../utils/constants';

const statusConfig: Record<string, { color: string; text: string }> = {
  online: { color: '#52c41a', text: '在线' },
  offline: { color: '#f5222d', text: '离线' },
  registered: { color: '#1677ff', text: '已注册' },
  unstable: { color: '#faad14', text: '不稳定' },
};

export default function TargetManagement() {
  const { message: msg } = App.useApp();
  const { targets, loading, healthMap, fetchTargets, createTarget, updateTarget, deleteTarget, checkAllHealth } = useTargetStore();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingTarget, setEditingTarget] = useState<TargetAgent | null>(null);
  const [form] = Form.useForm();

  useEffect(() => {
    fetchTargets();
    checkAllHealth();
  }, []);

  const openCreateModal = () => {
    setEditingTarget(null);
    form.resetFields();
    form.setFieldsValue({ method: 'POST', input_field: 'query', output_field: 'answer', health_check_path: '/health' });
    setModalOpen(true);
  };

  const openEditModal = (target: TargetAgent) => {
    setEditingTarget(target);
    form.setFieldsValue(target);
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    const values = await form.validateFields();
    if (editingTarget) {
      await updateTarget(editingTarget.id, values);
      msg.success('目标更新成功');
    } else {
      await createTarget(values);
      msg.success('目标注册成功');
    }
    setModalOpen(false);
  };

  const handleDelete = async (id: string) => {
    await deleteTarget(id);
    msg.success('目标已删除');
  };

  const columns: ColumnsType<TargetAgent> = [
    {
      title: 'ID', dataIndex: 'id', key: 'id', width: 150,
      render: (id: string) => <code>{id}</code>,
    },
    { title: '名称', dataIndex: 'name', key: 'name', width: 160 },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 90,
      render: (s: string) => {
        const cfg = statusConfig[s] || { color: '#999', text: s };
        return <Badge color={cfg.color} text={cfg.text} />;
      },
    },
    {
      title: '地址', key: 'address', width: 220,
      render: (_, r) => (
        <Tooltip title={`${r.base_url}:${r.port}${r.health_check_path}`}>
          <Space size={4}>
            <LinkOutlined />
            <span>{r.base_url}:{r.port}</span>
          </Space>
        </Tooltip>
      ),
    },
    {
      title: '能力标签', dataIndex: 'capabilities', key: 'capabilities', width: 200,
      render: (caps: AgentCapability[]) => (
        <Space size={[4, 4]} wrap>
          {caps.map((c) => (
            <Tag key={c} color="blue">{AgentCapabilityLabel[c]}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '响应时间', key: 'health', width: 100,
      render: (_, r) => {
        const h = healthMap[r.id];
        if (!h || h.status === 'registered') return '-';
        return h.response_time_ms > 0 ? `${h.response_time_ms}ms` : '超时';
      },
    },
    {
      title: '更新时间', dataIndex: 'updated_at', key: 'updated_at', width: 170,
      render: (v: string) => formatDateTime(v),
    },
    {
      title: '操作', key: 'actions', width: 200, fixed: 'right' as const,
      render: (_, record) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEditModal(record)}>编辑</Button>
          <Popconfirm title="确定删除此目标？" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>Agent目标管理</h2>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => { fetchTargets(); checkAllHealth(); }} loading={loading}>
            刷新
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>
            注册新目标
          </Button>
        </Space>
      </div>

      <Table
        dataSource={targets}
        columns={columns}
        rowKey="id"
        loading={loading}
        scroll={{ x: 1200 }}
        pagination={{ pageSize: 10 }}
      />

      {/* 注册/编辑弹窗 */}
      <Modal
        title={editingTarget ? `编辑目标: ${editingTarget.name}` : '注册新Agent目标'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSubmit}
        width={640}
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="Agent名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="例如：政务问答助手" />
          </Form.Item>
          <Space size={16}>
            <Form.Item name="base_url" label="Base URL" rules={[{ required: true, message: '请输入地址' }]}>
              <Input placeholder="http://localhost" style={{ width: 260 }} />
            </Form.Item>
            <Form.Item name="port" label="端口" rules={[{ required: true }]}>
              <InputNumber min={1} max={65535} />
            </Form.Item>
          </Space>
          <Space size={16}>
            <Form.Item name="input_field" label="输入字段" rules={[{ required: true }]}>
              <Input placeholder="query" style={{ width: 120 }} />
            </Form.Item>
            <Form.Item name="output_field" label="输出字段" rules={[{ required: true }]}>
              <Input placeholder="answer" style={{ width: 120 }} />
            </Form.Item>
            <Form.Item name="health_check_path" label="健康检查路径">
              <Input placeholder="/health" style={{ width: 140 }} />
            </Form.Item>
          </Space>
          <Form.Item name="capabilities" label="能力标签" rules={[{ required: true, message: '请选择至少一个能力' }]}>
            <Select mode="multiple" placeholder="选择能力标签">
              {Object.entries(AgentCapabilityLabel).map(([key, label]) => (
                <Select.Option key={key} value={key}>{label}</Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} placeholder="Agent功能描述" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
