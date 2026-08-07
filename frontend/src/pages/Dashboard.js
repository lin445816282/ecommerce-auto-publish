import React, { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, Typography, Space, Tag } from 'antd';
import { ShoppingCartOutlined, CheckCircleOutlined, ThunderboltOutlined, WarningOutlined } from '@ant-design/icons';
import { getProductList, getTaskList } from '../services/api';

const { Title } = Typography;

export default function Dashboard() {
  const [stats, setStats] = useState({ products: 0, published: 0, tasks: 0, alerts: 0 });

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const [prodRes, taskRes] = await Promise.allSettled([getProductList(), getTaskList()]);
      const products = prodRes.status === 'fulfilled' ? prodRes.value.data.data : [];
      const tasks = taskRes.status === 'fulfilled' ? taskRes.value.data.data : [];
      setStats({
        products: Array.isArray(products) ? products.length : 0,
        published: Array.isArray(products) ? products.filter(p => p.status === 4).length : 0,
        tasks: Array.isArray(tasks) ? tasks.length : 0,
        alerts: 0,
      });
    } catch { /* backend not running */ }
  };

  return (
    <div>
      <Title level={4}>📊 系统概览</Title>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card><Statistic title="商品总数" value={stats.products} prefix={<ShoppingCartOutlined />} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="已上架" value={stats.published} prefix={<CheckCircleOutlined />} valueStyle={{ color: '#3f8600' }} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="任务队列" value={stats.tasks} prefix={<ThunderboltOutlined />} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="预警" value={stats.alerts} prefix={<WarningOutlined />} valueStyle={{ color: '#cf1322' }} /></Card>
        </Col>
      </Row>
      <Card title="🚀 快速操作">
        <Space>
          <Tag color="blue">1. 左侧「商品管理」录入商品</Tag>
          <span>→</span>
          <Tag color="orange">2. 「调度分发」推送到平台</Tag>
          <span>→</span>
          <Tag color="purple">3. 「AI工具」智能优化</Tag>
          <span>→</span>
          <Tag color="green">4. 「审核发布」上架</Tag>
        </Space>
      </Card>
    </div>
  );
}
