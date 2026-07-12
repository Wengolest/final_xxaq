import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card, Descriptions, Tag, Timeline, Progress, Button, Spin, Empty, Row, Col,
} from 'antd';
import {
  ArrowLeftOutlined, BarChartOutlined, ClockCircleOutlined,
  CheckCircleOutlined, CloseCircleOutlined, MinusCircleOutlined,
} from '@ant-design/icons';
import { useExperimentStore } from '../../store/experimentStore';
import * as experimentApi from '../../api/experiment';
import type { ExperimentTimelineEvent } from '../../api/types';
import {
  AttackFamilyLabel, ExperimentStatus, DefenseLayerLabel,
} from '../../utils/constants';
import { experimentStatusColor, attackFamilyColor } from '../../utils/colorMap';
import { formatDateTime } from '../../utils/formatters';

const statusLabel: Record<string, string> = {
  draft: '草稿', pending: '等待中', running: '运行中',
  completed: '已完成', failed: '失败', stopped: '已停止',
};

const eventIcons: Record<string, React.ReactNode> = {
  attack_send: <ClockCircleOutlined style={{ color: '#1677ff' }} />,
  defense_block: <CloseCircleOutlined style={{ color: '#f5222d' }} />,
  defense_pass: <MinusCircleOutlined style={{ color: '#faad14' }} />,
  defense_warn: <MinusCircleOutlined style={{ color: '#fa8c16' }} />,
  response_received: <CheckCircleOutlined style={{ color: '#13c2c2' }} />,
  score_computed: <BarChartOutlined style={{ color: '#52c41a' }} />,
  error: <CloseCircleOutlined style={{ color: '#f5222d' }} />,
  status_change: <ClockCircleOutlined style={{ color: '#999' }} />,
};

export default function ExperimentDetail() {
  const { runId } = useParams<{ runId: string }>();
  const navigate = useNavigate();
  const { currentExperiment, getExperiment } = useExperimentStore();
  const [timeline, setTimeline] = useState<ExperimentTimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!runId) return;
    setLoading(true);
    Promise.all([
      getExperiment(runId),
      experimentApi.getTimeline(runId),
    ]).then(([, t]) => {
      setTimeline(t);
      setLoading(false);
    });
  }, [runId]);

  const exp = currentExperiment;

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  if (!exp) return <Empty description="实验不存在" />;

  const isRunning = exp.status === ExperimentStatus.RUNNING;

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/experiments')}>返回</Button>
        <h2 style={{ margin: 0 }}>{exp.name}</h2>
        <Tag color={experimentStatusColor[exp.status]}>{statusLabel[exp.status]}</Tag>
        {exp.status === ExperimentStatus.COMPLETED && (
          <Button type="primary" icon={<BarChartOutlined />} onClick={() => navigate(`/results/${runId}`)}>
            查看评估结果
          </Button>
        )}
      </div>

      {/* 实验信息 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col span={16}>
          <Card title="实验信息" size="small">
            <Descriptions column={2} size="small">
              <Descriptions.Item label="实验ID"><code>{exp.run_id}</code></Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={experimentStatusColor[exp.status]}>{statusLabel[exp.status]}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="测试目标">
                {exp.target_ids.map((id) => <Tag key={id}>{id}</Tag>)}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">{formatDateTime(exp.created_at)}</Descriptions.Item>
              <Descriptions.Item label="攻击族" span={2}>
                {exp.attack_families.map((f) => (
                  <Tag key={f} color={attackFamilyColor[f]}>{AttackFamilyLabel[f]}</Tag>
                ))}
              </Descriptions.Item>
              <Descriptions.Item label="防御层" span={2}>
                {exp.defense_layers.map((d) => (
                  <Tag key={d}>{DefenseLayerLabel[d]}</Tag>
                ))}
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
        <Col span={8}>
          <Card title="执行进度" size="small">
            {exp.progress ? (
              <div style={{ textAlign: 'center' }}>
                <Progress
                  type="circle"
                  percent={exp.progress.percentage}
                  status={isRunning ? 'active' : 'success'}
                  size={140}
                />
                <p style={{ marginTop: 12, color: '#666' }}>
                  已完成 {exp.progress.completed} / {exp.progress.total_samples} 个样本
                </p>
                {exp.progress.current_family && (
                  <p style={{ color: '#999', fontSize: 12 }}>
                    当前: {AttackFamilyLabel[exp.progress.current_family]}
                    {exp.progress.current_target && ` | ${exp.progress.current_target}`}
                  </p>
                )}
              </div>
            ) : (
              <Empty description="等待启动" />
            )}
          </Card>
        </Col>
      </Row>

      {/* 事件时间线 */}
      <Card title="实验事件时间线" size="small">
        {timeline.length === 0 ? (
          <Empty description="暂无事件记录" />
        ) : (
          <Timeline
            pending={isRunning ? '实验进行中...' : undefined}
            items={timeline.map((e) => ({
              dot: eventIcons[e.event_type],
              children: (
                <div>
                  <small style={{ color: '#999' }}>{formatDateTime(e.timestamp)}</small>
                  <div style={{ marginTop: 2 }}>
                    <Tag color={attackFamilyColor[e.attack_family]} style={{ fontSize: 10 }}>
                      {AttackFamilyLabel[e.attack_family]?.slice(0, 8)}
                    </Tag>
                    {e.variant_id && <Tag style={{ fontSize: 10 }}>{e.variant_id}</Tag>}
                    {e.message}
                  </div>
                </div>
              ),
            }))}
          />
        )}
      </Card>
    </div>
  );
}
