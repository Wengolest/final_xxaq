import { useState } from 'react';
import {
  Table, Card, Tag, Select, Space, Timeline, Input, Row, Col, Empty,
} from 'antd';
import { SearchOutlined, AuditOutlined } from '@ant-design/icons';
import type { ExperimentTimelineEvent } from '../../api/types';
import { mockTimelineEvents } from '../../api/mock';
import { formatDateTime } from '../../utils/formatters';
import { AttackFamilyLabel } from '../../utils/constants';
import { attackFamilyColor } from '../../utils/colorMap';

const eventIcons: Record<string, string> = {
  attack_send: '⚔️',
  defense_block: '🚫',
  defense_pass: '⚠️',
  defense_warn: '⚡',
  response_received: '📥',
  score_computed: '📊',
  error: '❌',
  status_change: 'ℹ️',
};

const eventLabel: Record<string, string> = {
  attack_send: '发送攻击',
  defense_block: '防御拦截',
  defense_pass: '防御通过',
  defense_warn: '防御告警',
  response_received: '收到响应',
  score_computed: '评分计算',
  error: '错误',
  status_change: '状态变更',
};

export default function AuditLog() {
  const [events] = useState<ExperimentTimelineEvent[]>(mockTimelineEvents);
  const [filterType, setFilterType] = useState<string[]>([]);
  const [searchText, setSearchText] = useState('');

  const filtered = events.filter((e) => {
    if (filterType.length > 0 && !filterType.includes(e.event_type)) return false;
    if (searchText && !e.message.includes(searchText)) return false;
    return true;
  });

  const columns = [
    {
      title: '时间', dataIndex: 'timestamp', key: 'timestamp', width: 170,
      render: (v: string) => formatDateTime(v),
    },
    {
      title: '类型', dataIndex: 'event_type', key: 'event_type', width: 100,
      render: (t: string) => (
        <span>{eventIcons[t] || '▪️'} {eventLabel[t] || t}</span>
      ),
    },
    {
      title: '目标', dataIndex: 'target_id', key: 'target_id', width: 120,
      render: (id: string) => <code>{id}</code>,
    },
    {
      title: '攻击族', dataIndex: 'attack_family', key: 'attack_family', width: 130,
      render: (f: string) => {
        const family = f as keyof typeof attackFamilyColor;
        return <Tag color={attackFamilyColor[family] || '#999'}>{(AttackFamilyLabel as Record<string, string>)[f]?.slice(0, 8)}</Tag>;
      },
    },
    { title: '消息', dataIndex: 'message', key: 'message', ellipsis: true },
    {
      title: '关联', key: 'related', width: 120,
      render: (_: unknown, r: ExperimentTimelineEvent) => (
        <Space size={4}>
          {r.case_id && <Tag>{r.case_id}</Tag>}
          {r.variant_id && <Tag>{r.variant_id}</Tag>}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>审计与证据回溯</h2>

      <Row gutter={[16, 16]}>
        <Col span={18}>
          <Card
            title={<span><AuditOutlined /> 事件记录</span>}
            extra={
              <Space>
                <Select
                  mode="multiple"
                  placeholder="事件类型筛选"
                  style={{ width: 240 }}
                  value={filterType}
                  onChange={setFilterType}
                  options={Object.entries(eventLabel).map(([k, v]) => ({ value: k, label: `${eventIcons[k]} ${v}` }))}
                  maxTagCount={2}
                />
                <Input
                  prefix={<SearchOutlined />}
                  placeholder="搜索"
                  style={{ width: 160 }}
                  value={searchText}
                  onChange={(e) => setSearchText(e.target.value)}
                  allowClear
                />
              </Space>
            }
          >
            <Table
              dataSource={filtered}
              columns={columns}
              rowKey={(r) => `${r.timestamp}_${r.event_type}_${r.message}`}
              size="small"
              scroll={{ x: 900 }}
              pagination={{ pageSize: 15 }}
              locale={{ emptyText: <Empty description="无匹配事件" /> }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card title="审计摘要" size="small">
            <Timeline
              items={events
                .filter((e) => ['defense_block', 'defense_pass', 'attack_send', 'score_computed'].includes(e.event_type))
                .slice(0, 10)
                .map((e) => ({
                  color: e.event_type === 'defense_block' ? 'red' : e.event_type === 'score_computed' ? 'green' : 'blue',
                  children: (
                    <div>
                      <small style={{ color: '#999' }}>{formatDateTime(e.timestamp).slice(11, 19)}</small>
                      <div style={{ fontSize: 12 }}>{e.message}</div>
                    </div>
                  ),
                }))
              }
            />
            <p style={{ fontSize: 12, color: '#999', marginTop: 12 }}>
              提示：完整证据链路请查看对应实验的时间线页面。当前页面展示的是所有实验的汇总审计记录。
            </p>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
