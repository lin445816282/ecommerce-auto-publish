import React, { useState, useEffect } from 'react';
import { Table, Button, Modal, Form, Input, InputNumber, Space, Tag, message, Select, Drawer, Descriptions, Popconfirm } from 'antd';
import { PlusOutlined, CloudDownloadOutlined, ThunderboltOutlined, EyeOutlined, ReloadOutlined } from '@ant-design/icons';
import { getProductList, getProductDetail, createProduct, crawlProduct, runPipeline } from '../services/api';

const STATUS_MAP = { 0: '草稿', 1: '待审核', 2: '已生成草稿', 3: '部分上架', 4: '全部上架', 5: '作废' };
const STATUS_COLOR = { 0: 'default', 1: 'orange', 2: 'blue', 3: 'cyan', 4: 'green', 5: 'red' };
const PLATFORM_ICONS = { taobao: '🍑', douyin: '🎵', pdd: '📦', amazon: '🌍' };

export default function ProductManager() {
  const [products, setProducts] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [crawlUrl, setCrawlUrl] = useState('');
  const [crawling, setCrawling] = useState(false);
  const [publishing, setPublishing] = useState({});
  const [detail, setDetail] = useState(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => { loadProducts(); }, [page]);

  const loadProducts = async () => {
    setLoading(true);
    try {
      const res = await getProductList((page - 1) * 20, 200);
      let data = res.data.data || [];
      if (statusFilter !== null && statusFilter !== undefined) {
        data = data.filter(p => p.status === statusFilter);
      }
      setProducts(data);
      setTotal(data.length);
    } catch (e) { message.error('无法连接后端服务'); }
    setLoading(false);
  };

  const handleCreate = async (values) => {
    try {
      await createProduct(values);
      message.success('商品创建成功');
      setModalOpen(false);
      form.resetFields();
      loadProducts();
    } catch (e) { message.error('创建失败: ' + (e.response?.data?.detail || e.message)); }
  };

  const handleCrawl = async () => {
    if (!crawlUrl) return message.warning('请输入1688链接');
    setCrawling(true);
    try {
      const res = await crawlProduct(crawlUrl);
      message.success(`抓取成功，商品ID: ${res.data.data.master_id}`);
      setCrawlUrl('');
      loadProducts();
    } catch (e) { message.error('抓取失败: ' + (e.response?.data?.detail || e.message)); }
    setCrawling(false);
  };

  const handlePublish = async (id) => {
    setPublishing(prev => ({ ...prev, [id]: true }));
    try {
      const res = await runPipeline(id, 'taobao,douyin,pdd,amazon');
      const summary = res.data.data.summary;
      message.success(`发布完成: 4平台中 ${summary.published} 个成功`);
      loadProducts();
    } catch (e) { message.error('发布失败: ' + (e.response?.data?.detail || e.message)); }
    setPublishing(prev => ({ ...prev, [id]: false }));
  };

  const showDetail = async (id) => {
    try {
      const res = await getProductDetail(id);
      setDetail(res.data.data);
      setDrawerOpen(true);
    } catch (e) { message.error('获取详情失败'); }
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 50 },
    { title: '商品标题', dataIndex: 'title', ellipsis: true,
      render: (t, r) => <a onClick={() => showDetail(r.id)}>{t}</a> },
    { title: '价格', dataIndex: 'price', width: 80, render: v => v > 0 ? `¥${v}` : '-' },
    { title: '状态', dataIndex: 'status', width: 100,
      render: s => <Tag color={STATUS_COLOR[s]}>{STATUS_MAP[s] || s}</Tag> },
    { title: '操作', key: 'actions', width: 180,
      render: (_, r) => (
        <Space size="small">
          <Button size="small" icon={<EyeOutlined />} onClick={() => showDetail(r.id)}>详情</Button>
          <Button size="small" type="primary" icon={<ThunderboltOutlined />}
            loading={publishing[r.id]}
            disabled={r.status === 5}
            onClick={() => handlePublish(r.id)}>
            发布
          </Button>
        </Space>
      ),
    },
  ];

  const statusOptions = Object.entries(STATUS_MAP).map(([k, v]) => ({ value: Number(k), label: v }));

  return (
    <div>
      <Space style={{ marginBottom: 16 }} wrap>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>手动录入</Button>
        <Space.Compact>
          <Input value={crawlUrl} onChange={e => setCrawlUrl(e.target.value)}
            placeholder="https://detail.1688.com/offer/..." style={{ width: 300 }}
            onPressEnter={handleCrawl} />
          <Button icon={<CloudDownloadOutlined />} onClick={handleCrawl} loading={crawling}>1688抓取</Button>
        </Space.Compact>
        <Select placeholder="按状态筛选" allowClear style={{ width: 130 }}
          options={statusOptions} value={statusFilter} onChange={v => { setStatusFilter(v); setPage(1); setTimeout(loadProducts, 0); }} />
        <Button icon={<ReloadOutlined />} onClick={loadProducts}>刷新</Button>
        <Tag>{total} 条商品</Tag>
      </Space>

      <Table columns={columns} dataSource={products} rowKey="id" loading={loading} size="small"
        pagination={{ current: page, pageSize: 15, total, onChange: setPage, showTotal: t => `共 ${t} 条` }} />

      {/* 录入弹窗 */}
      <Modal title="录入新商品" open={modalOpen} onCancel={() => setModalOpen(false)} onOk={() => form.submit()} destroyOnClose>
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="inner_sku" label="SKU" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="title" label="标题" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="price" label="售价" rules={[{ required: true }]}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="cost_price" label="成本价"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="stock" label="库存"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="desc" label="描述"><Input.TextArea rows={3} /></Form.Item>
        </Form>
      </Modal>

      {/* 详情抽屉 */}
      <Drawer title="商品详情" open={drawerOpen} onClose={() => setDrawerOpen(false)} width={480}>
        {detail && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="SKU">{detail.inner_sku}</Descriptions.Item>
            <Descriptions.Item label="标题">{detail.title}</Descriptions.Item>
            <Descriptions.Item label="售价">¥{detail.price}</Descriptions.Item>
            <Descriptions.Item label="库存">{detail.stock}</Descriptions.Item>
            <Descriptions.Item label="状态"><Tag color={STATUS_COLOR[detail.status]}>{STATUS_MAP[detail.status]}</Tag></Descriptions.Item>
            <Descriptions.Item label="版本">{detail.version}</Descriptions.Item>
            <Descriptions.Item label="描述">{detail.desc || '-'}</Descriptions.Item>
            <Descriptions.Item label="属性">{detail.attrs ? JSON.stringify(detail.attrs) : '-'}</Descriptions.Item>
            <Descriptions.Item label="图片">{detail.images?.length || 0} 张</Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>
    </div>
  );
}
