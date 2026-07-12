import { Outlet } from 'react-router-dom';
import { Layout } from 'antd';
import { useUIStore } from '../../store/uiStore';
import Sidebar from './Sidebar';

const { Header, Sider, Content } = Layout;

export default function MainLayout() {
  const sidebarCollapsed = useUIStore((s) => s.sidebarCollapsed);

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={sidebarCollapsed}
        onCollapse={() => useUIStore.getState().toggleSidebar()}
        width={220}
        style={{ position: 'fixed', left: 0, top: 0, bottom: 0, zIndex: 10 }}
      >
        <Sidebar />
      </Sider>
      <Layout style={{ marginLeft: sidebarCollapsed ? 80 : 220, transition: 'margin-left 0.2s' }}>
        <Header style={{ padding: '0 24px', background: '#fff', borderBottom: '1px solid #f0f0f0', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: 14, color: '#999' }}>
            LLM Agent Security Evaluation Platform v0.1
          </span>
        </Header>
        <Content style={{ margin: 24 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
