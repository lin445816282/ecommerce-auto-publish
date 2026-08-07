import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Table, Button, Modal, Form, Input, InputNumber, Space, Tag, message,
  Select, Drawer, Descriptions, Upload, Tooltip, Progress, Typography,
} from 'antd';
import {
  PlusOutlined, CloudDownloadOutlined, ThunderboltOutlined, EyeOutlined,
  ReloadOutlined, SearchOutlined, UploadOutlined, DownloadOutlined,
  FileExcelOutlined,
} from '@ant-design/icons';
import { getProductDetail, createProduct, crawlProduct, runPipeline, searchProducts, importCsv, exportCsv } from '../services/api';

const { Text } = Typography;

const STATUS_MAP = { 0: '草稿', 1: '待审核', 2: '已生成草稿', 3: '部分上架', 4: '全部上架', 5: '作废' };
const STATUS_COLOR = { 0: 'default', 1: 'orange', 2: 'blue', 3: 'cyan', 4: 'green', 5: 'red' };

const PAGE_SIZE = 15;

export default function ProductManager() {
  const [products, setProducts] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [statusFilter, setStatusFilter] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [crawlUrl, setCrawlUrl] = useState('');
  const [crawling, setCrawling] = useState(false);
  const [publishing, setPublishing] = useState({});
  const [detail, setDetail] = useState(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState(null);
  const [exporting, setExporting] = useState(false);
  const timerRef = useRef(null);
  const [form] = Form.useForm();

  // Load with search + status filter
  const loadProducts = useCallback(async (q = searchText, status = statusFilter, p = page) => {
    setLoading(true);
    try {
      const res = await searchProducts(q, status, (p - 1) * PAGE_SIZE, PAGE_SIZE);
      const data = res.data.data;
      setProducts(data.items || []);
      setTotal(data.total || 0);
    } catch (e) {
      // fallback to old API
      try {
        const { getProductList } = await import('../services/api');
        const res = await getProductList((p - 1) * PAGE_SIZE, 200);
        let data = res.data.data || [];
        if (status !== null && status !== undefined) data = data.filter(x => x.status === status);
        if (q) data = data.filter(x => (x.title || '').includes(q) || (x.inner_sku || '').includes(q));
        setProducts(data);
        setTotal(data.length);
      } catch { message.error('无法连接后端服务'); }
    }
    setLoading(false);
  }, [searchText, statusFilter, page]);

  useEffect(() => { loadProducts(); }, [page, statusFilter]);

  // Debounced search
  const handleSearch = (val) => {
    setSearchText(val);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      setPage(1);
      loadProducts(val, statusFilter, 1);
    }, 400);
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
      message.success('抓取成功，商品ID: ' + res.data.data.master_id);
      setCrawlUrl('');
      loadProducts();
    } catch (e) { message.error('抓取失败: ' + (e.response?.data?.detail || e.message)); }
    setCrawling(false);
  };

  const handlePublish = async (id) => {
    setPublishing(prev => ({ ...prev, [id]: true }));
    try {
      const res = await runPipeline(id, 'taobao,douyin,pdd,amazon');
      message.success('发布完成: 4平台中 ' + res.data.data.summary.published + ' 个成功');
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

  // CSV Import
  const handleImport = async (file) => {
    setImporting(true);
    setImportResult(null);
    try {
      const res = await importCsv(file);
      const d = res.data.data;
      setImportResult(d);
      if (d.imported > 0) {
        message.success('导入完成: ' + d.imported + ' 条成功, ' + d.skipped + ' 条跳过');
        loadProducts();
      } else {
        message.warning('没有导入任何商品');
      }
    } catch (e) {
      message.error('导入失败: ' + (e.response?.data?.detail || e.message));
    }
    setImporting(false);
    return false; // prevent default upload
  };

  // CSV Export
  const handleExport = async () => {
    setExporting(true);
    try {
      const res = await exportCsv(statusFilter);
      const blob = new Blob([res.data], { type: 'text/csv;charset=utf-8' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'products_export.csv';
      a.click();
      window.URL.revokeObjectURL(url);
      message.success('导出成功');
    } catch (e) {
      message.error('导出失败');
    }
    setExporting(false);
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 50, sorter: (a, b) => a.id - b.id },
    { title: 'SKU', dataIndex: 'inner_sku', width: 140, ellipsis: true },
    { title: '商品标题', dataIndex: 'title', ellipsis: true,
      render: (t, r) => <a onClick={() => showDetail(r.id)}>{t}</a> },
    { title: '售价', dataIndex: 'price', width: 90, render: v => v > 0 ? <span style={{ color: '#cf1322', fontWeight: 500 }}>¥{v}</span> : '-' },
    { title: '库存', dataIndex: 'stock', width: 70, render: v => v ?? '-' },
    { title: '状态', dataIndex: 'status', width: 90,
      render: s => <Tag color={STATUS_COLOR[s]}>{STATUS_MAP[s] || s}</Tag> },
    { title: '来源', dataIndex: 'source_type', width: 80, render: s => s === 'manual' ? '手动' : s === '1688' ? '1688' : s === 'csv_import' ? 'CSV导入' : s },
    { title: '操作', key: 'actions', width: 170, fixed: 'right',
      render: (_, r) => (
        <Space size="small">
          <Button size="small" icon={<EyeOutlined />} onClick={() => showDetail(r.id)}>详情</Button>
          <Button size="small" type="primary" icon={<ThunderboltOutlined />}
            loading={publishing[r.id]} disabled={r.status === 5}
            onClick={() => handlePublish(r.id)}>发布</Button>
        </Space>
      ),
    },
  ];

  const statusOptions = Object.entries(STATUS_MAP).map(([k, v]) => ({ value: Number(k), label: v }));

  return (
    <div>
      {/* Toolbar */}
      <Space style={{ marginBottom: 12 }} wrap size="middle">
        <Input.Search
          prefix={<SearchOutlined />}
          placeholder="搜索标题/SKU..."
          allowClear
          value={searchText}
          onChange={e => handleSearch(e.target.value)}
          onSearch={v => { setPage(1); loadProducts(v, statusFilter, 1); }}
          style={{ width: 260 }}
        />
        <Select placeholder="全部状态" allowClear style={{ width: 120 }}
          options={statusOptions} value={statusFilter}
          onChange={v => { setStatusFilter(v); setPage(1); }} />
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>手动录入</Button>
        <Space.Compact>
          <Input value={crawlUrl} onChange={e => setCrawlUrl(e.target.value)}
            placeholder="1688链接..." style={{ width: 260 }}
            onPressEnter={handleCrawl} />
          <Button icon={<CloudDownloadOutlined />} onClick={handleCrawl} loading={crawling}>抓取</Button>
        </Space.Compact>
        <Upload accept=".csv" showUploadList={false} beforeUpload={handleImport}>
          <Button icon={<UploadOutlined />} loading={importing}>
            <Tooltip title="CSV格式: title,price,cost_price,stock,desc">批量导入</Tooltip>
          </Button>
        </Upload>
        <Button icon={<DownloadOutlined />} onClick={handleExport} loading={exporting}>导出CSV</Button>
        <Button icon={<ReloadOutlined />} onClick={() => loadProducts()}>刷新</Button>
        <Tag color="blue">{total} 条</Tag>
      </Space>

      {/* Import result feedback */}
      {importResult && (
        <div style={{ marginBottom: 12, padding: '8px 16px', background: '#f6ffed', borderRadius: 6, border: '1px solid #b7eb8f' }}>
          <Space>
            <FileExcelOutlined style={{ color: '#52c41a' }} />
            <Text>导入完成: <Text strong style={{ color: '#3f8600' }}>{importResult.imported} 条成功</Text>, {importResult.skipped} 条跳过</Text>
            <Button size="small" type="link" onClick={() => setImportResult(null)}>关闭</Button>
          </Space>
          {importResult.errors?.length > 0 && (
            <div style={{ marginTop: 4 }}>
              {importResult.errors.slice(0, 5).map((e, i) => (
                <Tag key={i} color="orange" style={{ margin: 2 }}>行{e.row}: {e.error}</Tag>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Table */}
      <Table
        columns={columns} dataSource={products} rowKey="id"
        loading={loading} size="small"
        scroll={{ x: 820 }}
        pagination={{
          current: page, pageSize: PAGE_SIZE, total,
          onChange: setPage,
          showTotal: t => '共 ' + t + ' 条',
          showSizeChanger: false,
        }}
      />

      {/* Create Modal */}
      <Modal title="录入新商品" open={modalOpen} onCancel={() => setModalOpen(false)}
        onOk={() => form.submit()} destroyOnClose>
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="inner_sku" label="SKU" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="title" label="标题" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="price" label="售价" rules={[{ required: true }]}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="cost_price" label="成本价"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="stock" label="库存"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="desc" label="描述"><Input.TextArea rows={3} /></Form.Item>
        </Form>
      </Modal>

      {/* Detail Drawer */}
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
