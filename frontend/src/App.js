import React, { useState } from 'react';
import { Layout, Menu, theme } from 'antd';
import {
  DashboardOutlined, ShoppingOutlined, ThunderboltOutlined,
  RobotOutlined, AuditOutlined, SettingOutlined
} from '@ant-design/icons';
import Dashboard from './pages/Dashboard';
import ProductManager from './pages/ProductManager';
import DispatchCenter from './pages/DispatchCenter';
import AITools from './pages/AITools';
import AuditPublish from './pages/AuditPublish';
import Settings from './pages/Settings';

const { Header, Sider, Content } = Layout;

const menuItems = [
  { key: 'dashboard', icon: <DashboardOutlined />, label: '工作台' },
  { key: 'products', icon: <ShoppingOutlined />, label: '商品管理' },
  { key: 'dispatch', icon: <ThunderboltOutlined />, label: '调度分发' },
  { key: 'ai', icon: <RobotOutlined />, label: 'AI工具' },
  { key: 'audit', icon: <AuditOutlined />, label: '审核发布' },
  { key: 'settings', icon: <SettingOutlined />, label: '系统设置' },
];

function App() {
  const [current, setCurrent] = useState('dashboard');
  const { token: { colorBgContainer, borderRadiusLG } } = theme.useToken();

  const renderPage = () => {
    switch (current) {
      case 'dashboard': return <Dashboard />;
      case 'products': return <ProductManager />;
      case 'dispatch': return <DispatchCenter />;
      case 'ai': return <AITools />;
      case 'audit': return <AuditPublish />;
      case 'settings': return <Settings />;
      default: return <Dashboard />;
    }
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider collapsible>
        <div style={{ color: 'white', textAlign: 'center', padding: '16px 0', fontSize: 16, fontWeight: 'bold' }}>
          🤖 AI上架系统
        </div>
        <Menu
          theme="dark"
          selectedKeys={[current]}
          onClick={({ key }) => setCurrent(key)}
          items={menuItems}
        />
      </Sider>
      <Layout>
        <Header style={{ padding: '0 24px', background: colorBgContainer, fontSize: 18, fontWeight: 600 }}>
          全平台AI自动上架管理系统
        </Header>
        <Content style={{ margin: 16, padding: 24, background: colorBgContainer, borderRadius: borderRadiusLG, overflow: 'auto' }}>
          {renderPage()}
        </Content>
      </Layout>
    </Layout>
  );
}

export default App;
