import React, { useState } from 'react';
import { Card, Row, Col, Input, Button, Space, message, Tag, Spin, Typography, Form, Select } from 'antd';
import { RobotOutlined, ThunderboltOutlined, FileTextOutlined, SearchOutlined } from '@ant-design/icons';
import { aiAudit, aiGenTitle, aiOptimizeDesc, aiKeywords } from '../services/api';

const { TextArea } = Input;
const { Title, Text, Paragraph } = Typography;

export default function AITools() {
  const [title, setTitle] = useState('');
  const [desc, setDesc] = useState('');
  const [platform, setPlatform] = useState('通用');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState({});

  const runAI = async (fn, key) => {
    setLoading(true);
    try {
      let res;
      if (key === 'audit') res = await aiAudit(title, desc, {});
      else if (key === 'titles') res = await aiGenTitle({ title, desc }, platform);
      else if (key === 'desc_opt') res = await aiOptimizeDesc(title, desc, {});
      else if (key === 'keywords') res = await aiKeywords(title, desc);
      setResults(prev => ({ ...prev, [key]: res.data.data }));
      message.success('AI处理完成');
    } catch (e) {
      message.error('AI服务不可用: ' + (e.response?.data?.detail || e.message));
    }
    setLoading(false);
  };

  return (
    <div>
      <Title level={4}>🤖 AI智能工具</Title>

      <Card title="📝 输入商品信息" style={{ marginBottom: 16 }}>
        <Row gutter={16}>
          <Col span={12}>
            <Input placeholder="商品标题" value={title} onChange={e => setTitle(e.target.value)} />
          </Col>
          <Col span={8}>
            <Select value={platform} onChange={setPlatform} style={{ width: '100%' }}
              options={[{ value: '通用', label: '通用' }, { value: '淘宝', label: '淘宝' }, { value: '抖店', label: '抖店' }]} />
          </Col>
          <Col span={4}>
            <Spin spinning={loading} />
          </Col>
        </Row>
        <TextArea rows={3} placeholder="商品描述..." value={desc} onChange={e => setDesc(e.target.value)} style={{ marginTop: 12 }} />
      </Card>

      <Row gutter={16}>
        <Col span={12}>
          <Card title={<><RobotOutlined /> 智能审核</>} extra={<Button type="link" onClick={() => runAI(audit, 'audit')}>执行</Button>}>
            {results.audit ? (
              <div>
                <Tag color={results.audit.safe ? 'green' : 'red'}>{results.audit.safe ? '✅ 安全' : '⚠️ 违规'}</Tag>
                <Text>风险分: {results.audit.risk_score}/100</Text>
                {results.audit.issues?.map((i, idx) => (
                  <Paragraph key={idx} type="danger">• [{i.field}] {i.reason}</Paragraph>
                ))}
                {results.audit.suggestions?.map((s, idx) => (
                  <Paragraph key={idx} type="success">💡 {s}</Paragraph>
                ))}
              </div>
            ) : <Text type="secondary">输入商品信息后点击执行</Text>}
          </Card>
        </Col>

        <Col span={12}>
          <Card title={<><ThunderboltOutlined /> 标题生成</>} extra={<Button type="link" onClick={() => runAI(genTitle, 'titles')}>生成</Button>}>
            {results.titles ? (
              <div>
                {results.titles.titles?.map((t, idx) => (
                  <Paragraph key={idx} copyable style={{ background: '#f5f5f5', padding: 8, borderRadius: 4 }}>
                    <Tag color="blue">#{idx + 1}</Tag> {t}
                  </Paragraph>
                ))}
                <div>{results.titles.keywords?.map(k => <Tag key={k}>{k}</Tag>)}</div>
              </div>
            ) : <Text type="secondary">输入商品信息后点击生成</Text>}
          </Card>
        </Col>

        <Col span={12} style={{ marginTop: 16 }}>
          <Card title={<><FileTextOutlined /> 描述优化</>} extra={<Button type="link" onClick={() => runAI(optimizeDesc, 'desc_opt')}>优化</Button>}>
            {results.desc_opt ? (
              <div>
                <Paragraph copyable style={{ background: '#f5f5f5', padding: 12, borderRadius: 4 }}>{results.desc_opt.desc}</Paragraph>
                <Title level={5}>卖点</Title>
                {results.desc_opt.selling_points?.map((p, idx) => <Tag key={idx} color="green">{p}</Tag>)}
              </div>
            ) : <Text type="secondary">输入商品信息后点击优化</Text>}
          </Card>
        </Col>

        <Col span={12} style={{ marginTop: 16 }}>
          <Card title={<><SearchOutlined /> 关键词提取</>} extra={<Button type="link" onClick={() => runAI(keywords, 'keywords')}>提取</Button>}>
            {results.keywords ? (
              <div>{results.keywords.keywords?.map(k => <Tag key={k} color="purple" style={{ margin: 4 }}>{k}</Tag>)}</div>
            ) : <Text type="secondary">输入商品信息后点击提取</Text>}
          </Card>
        </Col>
      </Row>
    </div>
  );
}
