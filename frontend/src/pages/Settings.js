import React, { useState, useEffect } from 'react';
import { Card, Form, Input, Select, Button, Space, Tag, message, Spin, Divider, Alert, Typography } from 'antd';
import { KeyOutlined, ApiOutlined, ThunderboltOutlined, CheckCircleOutlined, SettingOutlined } from '@ant-design/icons';
import { getAIConfig, setAIKey, setAIProvider, setAIModel, testAIConnection } from '../services/api';

const { Title, Text } = Typography;

export default function Settings() {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [form] = Form.useForm();

  useEffect(() => { loadConfig(); }, []);

  const loadConfig = async () => {
    setLoading(true);
    try {
      const res = await getAIConfig();
      const cfg = res.data.data;
      setConfig(cfg);
      form.setFieldsValue({
        api_key: '',
        provider: cfg.provider,
        model: cfg.model,
      });
    } catch { message.error('加载配置失败'); }
    setLoading(false);
  };

  const handleSaveKey = async (values) => {
    if (!values.api_key) return message.warning('请输入API Key');
    try {
      const res = await setAIKey(values.api_key);
      if (res.data.data.ok) message.success(res.data.data.msg);
      form.setFieldsValue({ api_key: '' });
      loadConfig();
    } catch (e) { message.error('保存失败'); }
  };

  const handleProviderChange = async (value) => {
    try {
      const res = await setAIProvider(value);
      if (res.data.data.ok) message.success(res.data.data.msg);
      loadConfig();
    } catch { message.error('切换失败'); }
  };

  const handleModelChange = async (value) => {
    try {
      const res = await setAIModel(value);
      if (res.data.data.ok) message.success(res.data.data.msg);
      loadConfig();
    } catch { message.error('设置失败'); }
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await testAIConnection();
      setTestResult(res.data.data);
      message.success('测试完成');
    } catch (e) {
      setTestResult({ ok: false, msg: '请求失败: ' + e.message });
    }
    setTesting(false);
  };

  const providers = [
    { value: 'openai', label: 'OpenAI (GPT-4.1 / o4)' },
    { value: 'claude', label: 'Anthropic Claude 4' },
    { value: 'deepseek', label: 'DeepSeek 深度求索' },
    { value: 'kimi', label: 'Kimi 月之暗面' },
    { value: 'doubao', label: '豆包 字节跳动' },
    { value: 'qwen', label: '通义千问 阿里云 (Qwen3)' },
  ];

  const modelMap = {
    openai: [
      { value: 'gpt-4.1', label: 'GPT-4.1 ⭐ 最新旗舰 (2025.04)' },
      { value: 'gpt-4.1-mini', label: 'GPT-4.1 Mini (轻量高效)' },
      { value: 'gpt-4.1-nano', label: 'GPT-4.1 Nano (极速便宜)' },
      { value: 'gpt-4o', label: 'GPT-4o (多模态)' },
      { value: 'gpt-4o-mini', label: 'GPT-4o Mini (快+省)' },
      { value: 'o4-mini', label: 'o4-mini (深度推理)' },
      { value: 'o3', label: 'o3 (最强推理)' },
    ],
    claude: [
      { value: 'claude-sonnet-4-20250514', label: 'Claude 4 Sonnet ⭐ 最新 (2025.05)' },
      { value: 'claude-3-5-sonnet-20241022', label: 'Claude 3.5 Sonnet (经典)' },
      { value: 'claude-3-5-haiku-20241022', label: 'Claude 3.5 Haiku (快速)' },
      { value: 'claude-3-opus-20240229', label: 'Claude 3 Opus (深度)' },
    ],
    deepseek: [
      { value: 'deepseek-chat', label: 'DeepSeek-V3 (671B MoE)' },
      { value: 'deepseek-v4-pro', label: 'DeepSeek-V4 Pro ⭐ 最新旗舰 (2025.12)' },
      { value: 'deepseek-v4-flash', label: 'DeepSeek-V4 Flash (极速便宜)' },
      { value: 'deepseek-reasoner', label: 'DeepSeek-R1 (深度推理)' },
    ],
    kimi: [
      { value: 'kimi-latest', label: 'Kimi 最新版 ⭐ (自动指向最新)' },
      { value: 'moonshot-v1-128k', label: 'Moonshot v1 128K (超长上下文)' },
      { value: 'moonshot-v1-32k', label: 'Moonshot v1 32K' },
      { value: 'moonshot-v1-8k', label: 'Moonshot v1 8K (基础)' },
    ],
    doubao: [
      { value: 'doubao-pro-256k', label: '豆包 Pro 256K ⭐ 最新旗舰' },
      { value: 'doubao-pro-128k', label: '豆包 Pro 128K' },
      { value: 'doubao-pro-32k', label: '豆包 Pro 32K' },
      { value: 'doubao-lite-128k', label: '豆包 Lite 128K (轻量)' },
      { value: 'doubao-lite-32k', label: '豆包 Lite 32K (极速)' },
      { value: 'doubao-1.5-pro-256k', label: '豆包 1.5 Pro 256K' },
    ],
    qwen: [
      { value: 'qwen3-235b-a22b', label: 'Qwen3 235B ⭐ 最新旗舰' },
      { value: 'qwen3-235b-a22b-thinking', label: 'Qwen3 235B 思考版 (推理增强)' },
      { value: 'qwen-plus', label: '通义千问 Plus (均衡)' },
      { value: 'qwen-max', label: '通义千问 Max (最强理解)' },
      { value: 'qwen-turbo', label: '通义千问 Turbo (快速便宜)' },
      { value: 'qwen-long', label: '通义千问 Long (长文档1000万Token)' },
      { value: 'qwen-vl-plus', label: '通义千问 VL (多模态视觉)' },
    ],
  };

  const modelOptions = modelMap[config?.provider] || modelMap.openai;

  return (
    <div>
      <Title level={4}><SettingOutlined /> 系统设置</Title>

      <Spin spinning={loading}>
        <Card title={<><ApiOutlined /> AI模型配置</>} style={{ marginBottom: 16 }}>
          <Alert
            message={config?.enabled ? '✅ AI已启用' : '⚠️ 未配置API Key，当前使用Mock模式'}
            type={config?.enabled ? 'success' : 'warning'}
            showIcon
            style={{ marginBottom: 16 }}
          />

          <Form form={form} layout="vertical" onFinish={handleSaveKey}>
            <Form.Item label="API Key" name="api_key">
              <Input.Password
                prefix={<KeyOutlined />}
                placeholder="sk-... 或 sk-ant-..."
                addonAfter={
                  <Button type="link" size="small" onClick={() => form.submit()}>保存</Button>
                }
                onPressEnter={() => form.submit()}
              />
            </Form.Item>
            {config?.api_key_masked && config.api_key_masked !== '未设置' && (
              <Tag color="blue">当前Key: {config.api_key_masked}</Tag>
            )}

            <Divider />

            <Form.Item label="AI提供商" name="provider">
              <Select
                options={providers}
                onChange={handleProviderChange}
                style={{ width: 300 }}
              />
            </Form.Item>

            <Form.Item label="模型" name="model">
              <Select
                options={modelOptions}
                onChange={handleModelChange}
                style={{ width: 300 }}
              />
            </Form.Item>

            <Divider />

            <Button
              type="primary"
              icon={<ThunderboltOutlined />}
              onClick={handleTest}
              loading={testing}
              disabled={!config?.enabled}
            >
              测试连接
            </Button>

            {testResult && (
              <div style={{ marginTop: 16 }}>
                {testResult.ok ? (
                  <Alert
                    type="success"
                    showIcon
                    icon={<CheckCircleOutlined />}
                    message="连接成功!"
                    description={
                      <div>
                        <Text copyable>{JSON.stringify(testResult.sample?.titles?.[0] || testResult.sample, null, 2)}</Text>
                      </div>
                    }
                  />
                ) : (
                  <Alert type="error" showIcon message="连接失败" description={testResult.msg} />
                )}
              </div>
            )}
          </Form>
        </Card>

        <Card title="📋 获取 API Key">
          <Space direction="vertical">
            <div>
              <Tag color="green">OpenAI</Tag>
              <a href="https://platform.openai.com/api-keys" target="_blank" rel="noreferrer">
                https://platform.openai.com/api-keys
              </a>
            </div>
            <div>
              <Tag color="purple">Claude</Tag>
              <a href="https://console.anthropic.com/keys" target="_blank" rel="noreferrer">
                https://console.anthropic.com/keys
              </a>
            </div>
            <div>
              <Tag color="blue">DeepSeek</Tag>
              <a href="https://platform.deepseek.com/api_keys" target="_blank" rel="noreferrer">
                https://platform.deepseek.com/api_keys
              </a>
            </div>
            <div>
              <Tag color="orange">Kimi</Tag>
              <a href="https://platform.moonshot.cn/console/api-keys" target="_blank" rel="noreferrer">
                https://platform.moonshot.cn/console/api-keys
              </a>
            </div>
            <div>
              <Tag color="magenta">豆包</Tag>
              <a href="https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey" target="_blank" rel="noreferrer">
                火山引擎 Ark 控制台
              </a>
            </div>
            <div>
              <Tag color="cyan">通义千问</Tag>
              <a href="https://dashscope.console.aliyun.com/apiKey" target="_blank" rel="noreferrer">
                https://dashscope.console.aliyun.com/apiKey
              </a>
            </div>
          </Space>
        </Card>
      </Spin>
    </div>
  );
}
