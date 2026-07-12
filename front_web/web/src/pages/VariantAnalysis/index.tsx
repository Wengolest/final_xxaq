import { useEffect, useState } from 'react';
import { Table, Tag, Card, Empty, Spin } from 'antd';
import {
  CheckCircleOutlined, CloseCircleOutlined, BranchesOutlined,
} from '@ant-design/icons';
import type { AttackVariant } from '../../api/types';
import { mockVariants } from '../../api/mock';
import { AttackFamilyLabel } from '../../utils/constants';
import { attackFamilyColor } from '../../utils/colorMap';
import { formatDateTime, formatScore } from '../../utils/formatters';

export default function VariantAnalysis() {
  const [variants, setVariants] = useState<AttackVariant[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 当前使用 Mock 数据，后续接入真实 API：attackApi.getVariants(caseId)
    setTimeout(() => {
      setVariants(mockVariants);
      setLoading(false);
    }, 300);
  }, []);

  const columns = [
    {
      title: '变体ID', dataIndex: 'variant_id', key: 'variant_id', width: 120,
      render: (id: string) => <code>{id}</code>,
    },
    {
      title: '父样本', dataIndex: 'case_id', key: 'case_id', width: 100,
    },
    {
      title: '攻击族', dataIndex: 'family', key: 'family', width: 140,
      render: (f: string) => {
        const family = f as keyof typeof attackFamilyColor;
        return <Tag color={attackFamilyColor[family] || '#999'}>{(AttackFamilyLabel as Record<string, string>)[f] || f}</Tag>;
      },
    },
    { title: '攻击目标', dataIndex: 'attack_goal', key: 'attack_goal', ellipsis: true },
    {
      title: '变体策略', dataIndex: 'variant_strategy', key: 'variant_strategy', width: 200,
    },
    {
      title: '结果', key: 'result', width: 120,
      render: (_: unknown, r: AttackVariant) => {
        if (r.success === undefined) return <Tag>未知</Tag>;
        return r.success ? (
          <Tag color="#f5222d" icon={<CheckCircleOutlined />}>攻击成功</Tag>
        ) : (
          <Tag color="#52c41a" icon={<CloseCircleOutlined />}>已被拦截</Tag>
        );
      },
    },
    {
      title: '评分', dataIndex: 'score', key: 'score', width: 80,
      render: (v?: number) => v !== undefined ? formatScore(v) : '-',
    },
    {
      title: '反馈', dataIndex: 'feedback_summary', key: 'feedback', ellipsis: true,
    },
    {
      title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 160,
      render: (v: string) => formatDateTime(v),
    },
  ];

  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>攻击变体分析</h2>

      <Card
        title={<span><BranchesOutlined /> 变体效果对比</span>}
        style={{ marginBottom: 16 }}
        extra={
          <span style={{ fontSize: 12, color: '#999' }}>
            同一 case_id 下展示不同 variant 的测试效果
          </span>
        }
      >
        {loading ? (
          <Spin />
        ) : variants.length === 0 ? (
          <Empty description="暂无变体数据。请在[攻击配置]中对样本点击[生成变体]" />
        ) : (
          <Table
            dataSource={variants}
            columns={columns}
            rowKey="variant_id"
            size="middle"
            scroll={{ x: 1200 }}
            expandable={{
              expandedRowRender: (r) => (
                <div style={{ padding: '0 16px 16px' }}>
                  <h4>Payload</h4>
                  <pre style={{
                    background: '#f5f5f5', padding: 12, borderRadius: 6,
                    maxHeight: 200, overflow: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-all',
                    fontSize: 12,
                  }}>
                    {r.payload}
                  </pre>
                </div>
              ),
            }}
          />
        )}
      </Card>
    </div>
  );
}
