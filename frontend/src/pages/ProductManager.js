import React, { useState, useEffect } from 'react';
import { Table, Button, Modal, Form, Input, InputNumber, Space, Tag, message, Popconfirm } from 'antd';
import { PlusOutlined, DeleteOutlined, CloudDownloadOutlined } from '@ant-design/icons';
import { getProductList, getProductDetail, createProduct, crawlProduct } from '../services/api';

const STATUS_MAP = { 0: '草稿', 1: '待审核', 2: '已生成草稿', 3: '部分上架', 4: '全部上架', 5: '作废' };
const STATUS_COLOR = { 0: 'default', 1: 'orange', 2: 'blue', 3: 'cyan', 4: 'green', 5: 'red' };

export default function ProductManager() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [crawlUrl, setCrawlUrl] = useState('');
  const [form] = Form.useForm();

  useEffect(() => { loadProducts(); }, []);

  const loadProducts = async () => {
    setLoading(true);
    try {
      const res = await getProductList();
      setProducts(res.data.data || []);
    } catch (e) {
      message.error('无法连接后端服务');
    }
    setLoading(false);
  };

  const handleCreate = async (values) => {
    try {
      await createProduct(values);
      message.success('商品创建成功');
      setModalOpen(false);
      form.resetFields();
      loadProducts();
    } catch (e) {
      message.error('创建失败: ' + (e.response?.data?.detail || e.message));
    }
  };

  const handleCrawl = async () => {
    if (!crawlUrl) return message.warning('请输入1688链接');
    try {
      const res = await crawlProduct(crawlUrl);
      message.success(`抓取成功，商品ID: ${res.data.data.master_id}`);
      setCrawlUrl('');
      loadProducts();
    } catch (e) {
      message.error('抓取失败: ' + (e.response?.data?.detail || e.message));
    }
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '商品标题', dataIndex: 'title', ellipsis: true },
    { title: '价格', dataIndex: 'price', render: v => v > 0 ? `¥${v}` : '-' },
    {
      title: '状态', dataIndex: 'status',
      render: s => <Tag color={STATUS_COLOR[s]}>{STATUS_MAP[s] || s}</Tag>
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>手动录入</Button>
        <Popconfirm title="输入1688商品链接" description={<Input value={crawlUrl} onChange={e => setCrawlUrl(e.target.value)} placeholder="https://detail.1688.com/offer/..." style={{ width: 360 }} />} onConfirm={handleCrawl} okText="抓取">
          <Button icon={<CloudDownloadOutlined />}>从1688抓取</Button>
        </Popconfirm>
        <Button onClick={loadProducts}>刷新</Button>
      </Space>

      <Table columns={columns} dataSource={products} rowKey="id" loading={loading} size="small" pagination={{ pageSize: 15 }} />

      <Modal title="录入新商品" open={modalOpen} onCancel={() => setModalOpen(false)} onOk={() => form.submit()}>
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="inner_sku" label="SKU" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="title" label="标题" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="price" label="售价" rules={[{ required: true }]}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="cost_price" label="成本价"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="stock" label="库存"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="desc" label="描述"><Input.TextArea rows={3} /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
