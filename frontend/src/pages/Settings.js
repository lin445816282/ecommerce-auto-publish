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
    { value: 'openai', label: 'OpenAI (GPT-4/3.5)' },
    { value: 'claude', label: 'Anthropic Claude 3.5' },
  ];

  const openaiModels = [
    { value: 'gpt-4', label: 'GPT-4' },
    { value: 'gpt-4-turbo', label: 'GPT-4 Turbo' },
    { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo (快速便宜)' },
  ];

  const claudeModels = [
    { value: 'claude-3-5-sonnet-20241022', label: 'Claude 3.5 Sonnet' },
    { value: 'claude-3-opus-20240229', label: 'Claude 3 Opus (最强)' },
    { value: 'claude-3-haiku-20240307', label: 'Claude 3 Haiku (最快便宜)' },
  ];

  const modelOptions = config?.provider === 'claude' ? claudeModels : openaiModels;

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

          <Form form={form} layout="vertical">
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
          </Space>
        </Card>
      </Spin>
    </div>
  );
}
