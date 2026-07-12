import { Tag } from 'antd';
import { AttackFamily, AttackFamilyLabel } from '../../utils/constants';
import { attackFamilyColor } from '../../utils/colorMap';

interface AttackFamilyTagProps {
  family: AttackFamily;
  showLabel?: boolean;
}

export default function AttackFamilyTag({ family, showLabel = true }: AttackFamilyTagProps) {
  return (
    <Tag color={attackFamilyColor[family] || '#999'}>
      {showLabel ? (AttackFamilyLabel[family] || family) : family}
    </Tag>
  );
}
