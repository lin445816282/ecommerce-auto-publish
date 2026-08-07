import React, { useState, useEffect } from 'react';
import { Layout, Menu, theme, Button, Dropdown, Space, Typography } from 'antd';
import {
  DashboardOutlined, ShoppingOutlined, ThunderboltOutlined,
  RobotOutlined, AuditOutlined, SettingOutlined, PictureOutlined,
  UserOutlined, LogoutOutlined,
} from '@ant-design/icons';
import Dashboard from './pages/Dashboard';
import ProductManager from './pages/ProductManager';
import DispatchCenter from './pages/DispatchCenter';
import AITools from './pages/AITools';
import AuditPublish from './pages/AuditPublish';
import Settings from './pages/Settings';
import ImageTools from './pages/ImageTools';
import Login from './pages/Login';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

const menuItems = [
  { key: 'dashboard', icon: <DashboardOutlined />, label: '工作台' },
  { key: 'products', icon: <ShoppingOutlined />, label: '商品管理' },
  { key: 'dispatch', icon: <ThunderboltOutlined />, label: '调度分发' },
  { key: 'ai', icon: <RobotOutlined />, label: 'AI工具' },
  { key: 'images', icon: <PictureOutlined />, label: '图片处理' },
  { key: 'audit', icon: <AuditOutlined />, label: '审核发布' },
  { key: 'settings', icon: <SettingOutlined />, label: '系统设置' },
];

function App() {
  const [current, setCurrent] = useState('dashboard');
  const [user, setUser] = useState(null);
  const { token: { colorBgContainer, borderRadiusLG } } = theme.useToken();

  useEffect(() => {
    const saved = localStorage.getItem('user');
    if (saved) {
      try { setUser(JSON.parse(saved)); } catch {}
    }
  }, []);

  const handleLogin = (userData) => setUser(userData);

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    setUser(null);
    setCurrent('dashboard');
  };

  if (!user) return <Login onLogin={handleLogin} />;

  const renderPage = () => {
    switch (current) {
      case 'dashboard': return <Dashboard />;
      case 'products': return <ProductManager />;
      case 'dispatch': return <DispatchCenter />;
      case 'ai': return <AITools />;
      case 'images': return <ImageTools />;
      case 'audit': return <AuditPublish />;
      case 'settings': return <Settings />;
      default: return <Dashboard />;
    }
  };

  const userMenu = {
    items: [
      { key: 'role', label: <Text type="secondary">{user.role === 'admin' ? '管理员' : '操作员'}</Text>, disabled: true },
      { type: 'divider' },
      { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', danger: true },
    ],
    onClick: ({ key }) => { if (key === 'logout') handleLogout(); },
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
        <Header style={{ padding: '0 24px', background: colorBgContainer, fontSize: 18, fontWeight: 600, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>全平台AI自动上架管理系统</span>
          <Dropdown menu={userMenu} placement="bottomRight">
            <Button type="text" icon={<UserOutlined />}>
              {user?.full_name || user?.username}
            </Button>
          </Dropdown>
        </Header>
        <Content style={{ margin: 16, padding: 24, background: colorBgContainer, borderRadius: borderRadiusLG, overflow: 'auto' }}>
          {renderPage()}
        </Content>
      </Layout>
    </Layout>
  );
}

export default App;
