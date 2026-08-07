import React, { useEffect, useState, useCallback } from 'react';
import { Row, Col, Card, Statistic, Typography, Space, Tag, Table, Spin, Button, Progress, Divider } from 'antd';
import {
  ShoppingCartOutlined, CheckCircleOutlined, ThunderboltOutlined,
  WarningOutlined, ReloadOutlined, GlobalOutlined, ClockCircleOutlined,
} from '@ant-design/icons';
import { getDashboardStats } from '../services/api';

const { Title, Text } = Typography;

const STATUS_COLORS = {
  '待处理': 'default', '待审核': 'orange', '草稿': 'blue',
  '部分上架': 'cyan', '全部上架': 'green', '作废': 'red',
};

const PLATFORM_ICONS = { taobao: '🍑', douyin: '🎵', pdd: '📦', amazon: '🌍' };

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);

  const loadStats = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getDashboardStats();
      setStats(res.data.data);
    } catch { /* backend not running */ }
    setLoading(false);
  }, []);

  useEffect(() => { loadStats(); }, [loadStats]);

  const pipelineColumns = [
    { title: '平台', dataIndex: 'platform', width: 80, render: p => PLATFORM_ICONS[p] || p },
    { title: '商品ID', dataIndex: 'master_id', width: 80 },
    { title: '状态', dataIndex: 'status', width: 100,
      render: s => <Tag color={s === 'published' ? 'green' : s === 'failed' ? 'red' : 'blue'}>{s}</Tag> },
    { title: '阶段', dataIndex: 'stage', width: 100 },
    { title: '时间', dataIndex: 'created_at', render: t => t?.slice(11, 19) || '' },
  ];

  if (!stats) return <Spin size="large" style={{ display: 'block', margin: '40px auto' }} />;

  const pubRate = stats.total > 0 ? Math.round((stats.published / stats.total) * 100) : 0;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>📊 系统概览</Title>
        <Button icon={<ReloadOutlined />} onClick={loadStats} loading={loading}>刷新</Button>
      </div>

      {/* 核心指标 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card hoverable>
            <Statistic title="商品总数" value={stats.total} prefix={<ShoppingCartOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card hoverable>
            <Statistic title="已上架" value={stats.published} prefix={<CheckCircleOutlined />}
              suffix={<Text type="secondary" style={{ fontSize: 14 }}>/ {stats.total}</Text>}
              valueStyle={{ color: '#3f8600' }} />
            <Progress percent={pubRate} size="small" strokeColor="#3f8600" style={{ marginTop: 4 }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card hoverable>
            <Statistic title="待审核" value={stats.pending} prefix={<ClockCircleOutlined />}
              valueStyle={{ color: stats.pending > 0 ? '#fa8c16' : '#3f8600' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card hoverable>
            <Statistic title="预警项" value={stats.alerts} prefix={<WarningOutlined />}
              valueStyle={{ color: stats.alerts > 0 ? '#cf1322' : '#3f8600' }} />
          </Card>
        </Col>
      </Row>

      <Row gutter={16}>
        {/* 商品状态分布 */}
        <Col span={8}>
          <Card title="商品状态分布" size="small">
            {Object.entries(stats.by_status || {}).map(([status, count]) => (
              <div key={status} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                <Tag color={STATUS_COLORS[status]}>{status}</Tag>
                <Text strong>{count}</Text>
              </div>
            ))}
            {Object.keys(stats.by_status || {}).length === 0 && <Text type="secondary">暂无数据</Text>}
          </Card>
        </Col>

        {/* 平台覆盖 */}
        <Col span={8}>
          <Card title={<><GlobalOutlined /> 平台覆盖</>} size="small">
            {Object.entries(stats.by_platform || {}).map(([platform, count]) => (
              <div key={platform} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                <span>{PLATFORM_ICONS[platform]} {platform}</span>
                <Text strong>{count} 条</Text>
              </div>
            ))}
            {Object.keys(stats.by_platform || {}).length === 0 && <Text type="secondary">暂无数据</Text>}
          </Card>
        </Col>

        {/* 快速操作 */}
        <Col span={8}>
          <Card title="🚀 一键流水线" size="small">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Tag color="blue">1. 商品管理 → 录入商品</Tag>
              <Tag color="orange">2. AI工具 → 智能优化标题/描述</Tag>
              <Tag color="purple">3. 图片处理 → 抠图/水印/优化</Tag>
              <Tag color="green">4. 调度分发 → 一键上架4平台</Tag>
            </Space>
          </Card>
        </Col>
      </Row>

      {/* 最近流水线 */}
      <Card title={<><ThunderboltOutlined /> 最近执行记录</>} style={{ marginTop: 16 }} size="small">
        {stats.recent_pipelines?.length > 0 ? (
          <Table
            columns={pipelineColumns}
            dataSource={stats.recent_pipelines}
            rowKey="task_id"
            pagination={false}
            size="small"
          />
        ) : (
          <Text type="secondary">暂无流水线执行记录，去「调度分发」页面执行一次吧</Text>
        )}
      </Card>
    </div>
  );
}
