import React, { useState, useEffect, useCallback } from 'react';
import {
  Table, Button, Space, Tag, message, Select, Card, Row, Col, Statistic,
  Badge, Progress, Divider, Typography, Tabs, Tooltip,
} from 'antd';
import {
  ReloadOutlined, ThunderboltOutlined, CheckCircleOutlined,
  CloseCircleOutlined, ClockCircleOutlined, SyncOutlined,
  DashboardOutlined, UnorderedListOutlined,
} from '@ant-design/icons';
import { getMonitorSummary, getMonitorTasks, retryTask } from '../services/api';

const { Title, Text } = Typography;

const STATUS_CONFIG = {
  queued:    { color: 'default',  icon: <ClockCircleOutlined />, label: '排队中' },
  running:   { color: 'processing', icon: <SyncOutlined spin />, label: '执行中' },
  passed:    { color: 'success', icon: <CheckCircleOutlined />, label: '审核通过' },
  blocked:   { color: 'warning', icon: <ClockCircleOutlined />, label: '已拦截' },
  failed:    { color: 'error',   icon: <CloseCircleOutlined />, label: '失败' },
  published: { color: 'green',   icon: <CheckCircleOutlined />, label: '已发布' },
  success:   { color: 'green',   icon: <CheckCircleOutlined />, label: '成功' },
};

export default function DispatchCenter() {
  const [summary, setSummary] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [retrying, setRetrying] = useState({});
  const [statusFilter, setStatusFilter] = useState(null);
  const [platformFilter, setPlatformFilter] = useState(null);
  const [tab, setTab] = useState('overview');

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [sumRes, taskRes] = await Promise.all([
        getMonitorSummary(),
        getMonitorTasks(statusFilter, platformFilter),
      ]);
      setSummary(sumRes.data.data);
      setTasks(taskRes.data.data.items || []);
      setTotal(taskRes.data.data.total || 0);
    } catch { message.error('无法连接后端'); }
    setLoading(false);
  }, [statusFilter, platformFilter]);

  useEffect(() => { loadData(); }, [loadData]);

  // Auto-refresh every 10 seconds
  useEffect(() => {
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, [loadData]);

  const handleRetry = async (taskId) => {
    setRetrying(prev => ({ ...prev, [taskId]: true }));
    try {
      const res = await retryTask(taskId);
      message.success(res.data.data.message);
      loadData();
    } catch (e) { message.error('重试失败: ' + (e.response?.data?.detail || e.message)); }
    setRetrying(prev => ({ ...prev, [taskId]: false }));
  };

  const taskColumns = [
    { title: '任务ID', dataIndex: 'task_id', width: 100 },
    { title: '商品', dataIndex: 'master_id', width: 60,
      render: v => v ? '#' + v : '-' },
    { title: '平台', dataIndex: 'platform', width: 80,
      render: p => ({ taobao: '🍑', douyin: '🎵', pdd: '📦', amazon: '🌍' }[p] || p) + ' ' + (p || '-') },
    { title: '类型', dataIndex: 'job_type', width: 90,
      render: t => ({ crawl: '抓取', image_process: '图片', adapt: '适配', publish: '发布' }[t] || t) },
    { title: '状态', dataIndex: 'status', width: 100,
      render: s => {
        const cfg = STATUS_CONFIG[s] || STATUS_CONFIG.queued;
        return <Tag color={cfg.color} icon={cfg.icon}>{cfg.label}</Tag>;
      } },
    { title: '重试', dataIndex: 'retry_count', width: 60,
      render: (v, r) => <Text>{v || 0}/{r.max_retry || 3}</Text> },
    { title: '时间', dataIndex: 'create_time', width: 100,
      render: v => v ? v.slice(11, 19) : '-' },
    { title: '流水线', dataIndex: 'pipeline', width: 130,
      render: p => p ? <Tag color={p.status === 'published' ? 'green' : 'blue'}>{p.stage}</Tag> : '-' },
    { title: '操作', key: 'ops', width: 80,
      render: (_, r) => {
        if (r.status === 'failed' && r.retry_count < r.max_retry) {
          return (
            <Button size="small" type="primary" danger
              loading={retrying[r.id]} onClick={() => handleRetry(r.id)}>
              重试
            </Button>
          );
        }
        return null;
      } },
  ];

  const s = summary || {};
  const pipelineStats = s.pipeline || {};
  const byStatus = pipelineStats.by_status || {};

  return (
    <div>
      <Tabs activeKey={tab} onChange={setTab} items={[
        {
          key: 'overview',
          label: <span><DashboardOutlined /> 监控总览</span>,
          children: (
            <div>
              {/* Stats Row */}
              <Row gutter={16} style={{ marginBottom: 24 }}>
                <Col span={4}>
                  <Card size="small"><Statistic title="流水线任务" value={pipelineStats.total || 0} prefix={<ThunderboltOutlined />} /></Card>
                </Col>
                <Col span={4}>
                  <Card size="small"><Statistic title="成功/已发布" value={byStatus.published || 0} valueStyle={{ color: '#3f8600' }} prefix={<CheckCircleOutlined />} /></Card>
                </Col>
                <Col span={4}>
                  <Card size="small"><Statistic title="执行中" value={byStatus.running || 0} valueStyle={{ color: '#1890ff' }} prefix={<SyncOutlined spin />} /></Card>
                </Col>
                <Col span={4}>
                  <Card size="small"><Statistic title="失败" value={byStatus.failed || 0} valueStyle={{ color: '#cf1322' }} prefix={<CloseCircleOutlined />} /></Card>
                </Col>
                <Col span={4}>
                  <Card size="small"><Statistic title="已拦截" value={byStatus.blocked || 0} valueStyle={{ color: '#fa8c16' }} prefix={<ClockCircleOutlined />} /></Card>
                </Col>
                <Col span={4}>
                  <Card size="small"><Statistic title="DB任务" value={s.db_tasks?.total || 0} /></Card>
                </Col>
              </Row>

              {/* Product status */}
              <Card title="商品状态分布" size="small" style={{ marginBottom: 16 }}>
                <Row gutter={16}>
                  {Object.entries(s.products || {}).map(([status, count]) => (
                    <Col key={status} span={4} style={{ textAlign: 'center' }}>
                      <Statistic title={status} value={count} />
                    </Col>
                  ))}
                </Row>
              </Card>

              {/* Recent pipeline tasks */}
              <Card title="最近流水线" size="small">
                {(pipelineStats.recent || []).length > 0 ? (
                  pipelineStats.recent.slice(0, 6).map((t, i) => {
                    const cfg = STATUS_CONFIG[t.status] || STATUS_CONFIG.queued;
                    return (
                      <div key={i} style={{ display: 'flex', alignItems: 'center', marginBottom: 8, gap: 8 }}>
                        <Tag color={cfg.color} icon={cfg.icon}>{cfg.label}</Tag>
                        <Text type="secondary" style={{ width: 80 }}>{t.platform}</Text>
                        <Text style={{ flex: 1 }}>{t.stage}</Text>
                        <Text type="secondary" style={{ width: 60, textAlign: 'right' }}>#{t.master_id}</Text>
                        <Text type="secondary" style={{ width: 60, textAlign: 'right' }}>{t.created_at?.slice(11, 19)}</Text>
                      </div>
                    );
                  })
                ) : (
                  <Text type="secondary">暂无流水线记录，去商品管理页执行一次发布吧</Text>
                )}
              </Card>
            </div>
          ),
        },
        {
          key: 'tasks',
          label: <span><UnorderedListOutlined /> 任务列表 ({total})</span>,
          children: (
            <div>
              <Space style={{ marginBottom: 12 }} wrap>
                <Select placeholder="状态筛选" allowClear style={{ width: 120 }}
                  onChange={v => setStatusFilter(v || null)}
                  options={Object.entries(STATUS_CONFIG).map(([k, v]) => ({ value: k, label: v.label }))} />
                <Select placeholder="平台筛选" allowClear style={{ width: 120 }}
                  onChange={v => setPlatformFilter(v || null)}
                  options={[
                    { value: 'taobao', label: '🍑 淘宝' },
                    { value: 'douyin', label: '🎵 抖音' },
                    { value: 'pdd', label: '📦 拼多多' },
                    { value: 'amazon', label: '🌍 亚马逊' },
                  ]} />
                <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
              </Space>

              <Table
                columns={taskColumns} dataSource={tasks} rowKey="id"
                loading={loading} size="small"
                pagination={{ pageSize: 20, showTotal: t => '共 ' + t + ' 条' }}
              />

              {tasks.length === 0 && !loading && (
                <div style={{ textAlign: 'center', padding: 40 }}>
                  <Text type="secondary">暂无任务记录</Text>
                </div>
              )}
            </div>
          ),
        },
      ]} />
    </div>
  );
}
