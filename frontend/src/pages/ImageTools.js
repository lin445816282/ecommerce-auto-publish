import React, { useState } from 'react';
import { Card, Upload, Button, Select, Checkbox, Input, Space, Tag, message, Spin, Typography, Image, Row, Col, Divider } from 'antd';
import { UploadOutlined, ScissorOutlined, CopyrightOutlined, ThunderboltOutlined, PictureOutlined } from '@ant-design/icons';
import { processImage, getImageSpecs } from '../services/api';

const { Title, Text } = Typography;

const PLATFORMS = [
  { value: 'taobao', label: '淘宝/天猫', color: 'orange' },
  { value: 'douyin', label: '抖店', color: 'volcano' },
  { value: 'pdd', label: '拼多多', color: 'red' },
  { value: 'amazon', label: '亚马逊', color: 'blue' },
];

export default function ImageTools() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const [operations, setOperations] = useState(['remove_bg', 'watermark', 'optimize']);
  const [watermarkText, setWatermarkText] = useState('');
  const [platform, setPlatform] = useState('taobao');

  const handleUpload = (info) => {
    const f = info.file.originFileObj || info.file;
    setFile(f);
    setResult(null);
    const reader = new FileReader();
    reader.onload = (e) => setPreview(e.target.result);
    reader.readAsDataURL(f);
  };

  const handleProcess = async () => {
    if (!file) return message.warning('请先上传图片');
    if (operations.length === 0) return message.warning('请选择至少一项处理操作');
    setProcessing(true);
    try {
      const res = await processImage(
        file,
        operations.join(','),
        watermarkText,
        platform,
      );
      if (res.data.data.ok) {
        setResult(res.data.data);
        message.success('处理完成!');
      } else {
        message.error(res.data.data.error || '处理失败');
      }
    } catch (e) {
      message.error('处理失败: ' + (e.response?.data?.detail || e.message));
    }
    setProcessing(false);
  };

  const opsLabel = (op) => {
    switch (op) {
      case 'remove_bg': return 'AI抠图';
      case 'watermark': return '水印';
      case 'optimize': return '平台优化';
      default: return op;
    }
  };

  return (
    <div>
      <Title level={4}><PictureOutlined /> AI图片处理</Title>

      <Row gutter={16}>
        <Col span={12}>
          <Card title="原始图片" size="small">
            <Upload
              beforeUpload={() => false}
              onChange={handleUpload}
              maxCount={1}
              accept="image/*"
              listType="picture-card"
            >
              <UploadOutlined /> 上传图片
            </Upload>
            {preview && (
              <Image src={preview} style={{ maxWidth: '100%', marginTop: 12 }} />
            )}
          </Card>
        </Col>

        <Col span={12}>
          <Card title="处理结果" size="small">
            {processing ? (
              <div style={{ textAlign: 'center', padding: 40 }}>
                <Spin size="large" />
                <p style={{ marginTop: 12 }}>AI处理中...</p>
              </div>
            ) : result?.ok ? (
              <>
                <Image
                  src={`data:image/png;base64,${result.base64}`}
                  style={{ maxWidth: '100%' }}
                />
                <Divider />
                <Space direction="vertical" size="small">
                  <Text>尺寸: {result.original_size?.join('x')} → {result.final_size?.join('x')}</Text>
                  <Text>大小: {result.filesize_kb} KB</Text>
                  {result.bg_removed && <Tag color="green">{result.bg_method} 抠图完成</Tag>}
                  {result.watermarked && <Tag color="blue">水印已添加</Tag>}
                  {result.optimized && (
                    <Tag color="purple">
                      优化: {result.optimized?.actions?.join(', ')}
                    </Tag>
                  )}
                </Space>
              </>
            ) : (
              <div style={{ textAlign: 'center', color: '#999', padding: 40 }}>
                处理结果将显示在此处
              </div>
            )}
          </Card>
        </Col>
      </Row>

      <Card title="处理选项" style={{ marginTop: 16 }}>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <Text strong>处理操作：</Text>
            <Checkbox.Group
              options={[
                { value: 'remove_bg', label: '🤖 AI抠图 (去背景)' },
                { value: 'watermark', label: '©️ 添加水印' },
                { value: 'optimize', label: '⚡ 平台尺寸优化' },
              ]}
              value={operations}
              onChange={setOperations}
              style={{ marginLeft: 12 }}
            />
          </div>

          {operations.includes('watermark') && (
            <div>
              <Text strong>水印文字：</Text>
              <Input
                placeholder="输入水印文字，留空使用默认"
                value={watermarkText}
                onChange={(e) => setWatermarkText(e.target.value)}
                style={{ width: 260, marginLeft: 12 }}
              />
            </div>
          )}

          {operations.includes('optimize') && (
            <div>
              <Text strong>目标平台：</Text>
              <Select
                value={platform}
                onChange={setPlatform}
                style={{ width: 180, marginLeft: 12 }}
                options={PLATFORMS.map(p => ({
                  value: p.value,
                  label: <span><Tag color={p.color} style={{ marginRight: 4 }}>{p.label}</Tag></span>,
                }))}
              />
              <Text type="secondary" style={{ marginLeft: 12, fontSize: 12 }}>
                (自动适配平台图片尺寸规范)
              </Text>
            </div>
          )}

          <Button
            type="primary"
            size="large"
            icon={<ThunderboltOutlined />}
            onClick={handleProcess}
            loading={processing}
            disabled={!file}
          >
            开始AI处理
          </Button>
        </Space>
      </Card>
    </div>
  );
}

