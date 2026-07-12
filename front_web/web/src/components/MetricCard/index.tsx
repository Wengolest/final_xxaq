import { Card, Statistic, Tooltip } from 'antd';
import { QuestionCircleOutlined } from '@ant-design/icons';

interface MetricCardProps {
  title: string;
  value: number | string;
  suffix?: string;
  precision?: number;
  tooltip?: string;
  valueStyle?: React.CSSProperties;
  loading?: boolean;
}

export default function MetricCard({
  title, value, suffix, precision = 2, tooltip, valueStyle, loading,
}: MetricCardProps) {
  return (
    <Card loading={loading}>
      <Statistic
        title={
          tooltip ? (
            <span>
              {title}
              <Tooltip title={tooltip}>
                <QuestionCircleOutlined style={{ marginLeft: 4, color: '#999', fontSize: 12 }} />
              </Tooltip>
            </span>
          ) : title
        }
        value={value}
        suffix={suffix}
        precision={precision}
        valueStyle={valueStyle}
      />
    </Card>
  );
}
