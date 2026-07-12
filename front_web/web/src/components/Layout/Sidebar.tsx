import { useNavigate, useLocation } from 'react-router-dom';
import { Menu } from 'antd';
import {
  DashboardOutlined,
  AimOutlined,
  ThunderboltOutlined,
  SafetyOutlined,
  ExperimentOutlined,
  BranchesOutlined,
  AuditOutlined,
} from '@ant-design/icons';

const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: '仪表盘' },
  { key: '/targets', icon: <AimOutlined />, label: 'Agent目标管理' },
  { key: '/attacks', icon: <ThunderboltOutlined />, label: '攻击配置' },
  { key: '/defenses', icon: <SafetyOutlined />, label: '防御配置' },
  { key: '/experiments', icon: <ExperimentOutlined />, label: '实验编排' },
  { key: '/variants', icon: <BranchesOutlined />, label: '变体分析' },
  { key: '/audit', icon: <AuditOutlined />, label: '审计日志' },
];

export default function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();

  // 处理 /experiments/:runId 和 /results/:runId 路径高亮
  const selectedKey = (() => {
    const path = location.pathname;
    if (path.startsWith('/results')) return '/experiments';
    if (path.startsWith('/experiments')) return '/experiments';
    return path;
  })();

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ height: 64, display: 'flex', alignItems: 'center', justifyContent: 'center', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
        <SafetyOutlined style={{ fontSize: 24, color: '#fff', marginRight: 8 }} />
        <span style={{ color: '#fff', fontSize: 16, fontWeight: 600, whiteSpace: 'nowrap' }}>
          Agent安全评测平台
        </span>
      </div>
      <Menu
        theme="dark"
        mode="inline"
        selectedKeys={[selectedKey]}
        items={menuItems}
        onClick={({ key }) => navigate(key)}
        style={{ flex: 1, borderRight: 0 }}
      />
    </div>
  );
}
