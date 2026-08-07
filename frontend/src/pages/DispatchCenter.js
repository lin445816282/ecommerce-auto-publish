import React, { useState, useEffect } from 'react';
import { Table, Button, Space, Tag, message, Select, Popconfirm, Card } from 'antd';
import { SendOutlined, ReloadOutlined } from '@ant-design/icons';
import { getProductList, dispatchProduct } from '../services/api';

const STATUS_MAP = { 0: '草稿', 1: '待审核', 2: '已生成草稿', 3: '部分上架', 4: '全部上架', 5: '作废' };

export default function DispatchCenter() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedPlatforms, setSelectedPlatforms] = useState('taobao,douyin');

  useEffect(() => { loadProducts(); }, []);

  const loadProducts = async () => {
    setLoading(true);
    try {
      const res = await getProductList();
      setProducts(res.data.data || []);
    } catch { message.error('无法连接后端'); }
    setLoading(false);
  };

  const handleDispatch = async (masterId) => {
    try {
      const res = await dispatchProduct(masterId, selectedPlatforms);
      const data = res.data.data;
      if (data.passed) {
        message.success(`分发成功 → ${Object.keys(data.platform_results).join(', ')}`);
      } else {
        message.warning(`被拦截: ${data.stage} ${JSON.stringify(data.errors)}`);
      }
      loadProducts();
    } catch (e) {
      message.error('分发失败: ' + (e.response?.data?.detail || e.message));
    }
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '标题', dataIndex: 'title', ellipsis: true },
    { title: '价格', dataIndex: 'price', render: v => `¥${v}` },
    { title: '状态', dataIndex: 'status', render: s => <Tag>{STATUS_MAP[s]}</Tag> },
    {
      title: '操作', key: 'action',
      render: (_, record) => (
        <Popconfirm title="确认分发？" description={`将商品#${record.id} 分发到 ${selectedPlatforms}`} onConfirm={() => handleDispatch(record.id)} disabled={record.status === 5}>
          <Button size="small" type="primary" icon={<SendOutlined />} disabled={record.status === 5}>分发</Button>
        </Popconfirm>
      ),
    },
  ];

  return (
    <div>
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space>
          <span>目标平台:</span>
          <Select mode="multiple" value={selectedPlatforms.split(',')} onChange={v => setSelectedPlatforms(v.join(','))} style={{ width: 300 }}
            options={[
              { value: 'taobao', label: '🍑 淘宝/天猫' },
              { value: 'douyin', label: '🎵 抖店' },
              { value: 'pdd', label: '📦 拼多多' },
              { value: 'amazon', label: '🌍 亚马逊' },
            ]}
          />
          <Button icon={<ReloadOutlined />} onClick={loadProducts}>刷新</Button>
        </Space>
      </Card>

      <Table columns={columns} dataSource={products} rowKey="id" loading={loading} size="small" />
    </div>
  );
}
