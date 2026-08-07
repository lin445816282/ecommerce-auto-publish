import React, { useState, useEffect } from 'react';
import { Table, Button, Space, Tag, message, Modal, Input } from 'antd';
import { CheckOutlined, CloseOutlined, SendOutlined, ReloadOutlined } from '@ant-design/icons';
import { getPendingAudit, submitAudit, publishProduct, getPublishStatus } from '../services/api';

export default function AuditPublish() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => { loadItems(); }, []);

  const loadItems = async () => {
    setLoading(true);
    try {
      const res = await getPendingAudit();
      setItems(res.data.data || []);
    } catch { /* empty */ }
    setLoading(false);
  };

  const handleAudit = async (relId, approved) => {
    try {
      await submitAudit(relId, approved, approved ? '审核通过' : '审核驳回');
      message.success(approved ? '已通过' : '已驳回');
      loadItems();
    } catch (e) {
      message.error('操作失败');
    }
  };

  const handlePublish = async (record) => {
    try {
      const draftId = `tb_draft_${record.master_id}_${Math.floor(Date.now() / 1000)}`;
      await publishProduct(draftId, record.platform);
      message.success(`已发布到${record.platform}`);
      loadItems();
    } catch (e) {
      message.error('发布失败: ' + (e.response?.data?.detail || e.message));
    }
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '商品ID', dataIndex: 'master_id', width: 80 },
    { title: '平台', dataIndex: 'platform', render: v => <Tag color="blue">{v}</Tag> },
    {
      title: '操作', key: 'action',
      render: (_, r) => (
        <Space>
          <Button size="small" type="primary" icon={<CheckOutlined />} onClick={() => handleAudit(r.id, true)}>通过</Button>
          <Button size="small" danger icon={<CloseOutlined />} onClick={() => handleAudit(r.id, false)}>驳回</Button>
          <Button size="small" icon={<SendOutlined />} onClick={() => handlePublish(r)}>发布</Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ReloadOutlined />} onClick={loadItems}>刷新</Button>
      </Space>
      <Table columns={columns} dataSource={items} rowKey="id" loading={loading} size="small" />
    </div>
  );
}
