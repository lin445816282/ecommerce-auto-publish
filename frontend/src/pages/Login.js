import React, { useState } from "react";
import { Card, Form, Input, Button, message, Typography } from "antd";
import { UserOutlined, LockOutlined, ThunderboltOutlined } from "@ant-design/icons";
import { login as apiLogin } from "../services/api";

const { Title, Text } = Typography;

export default function Login({ onLogin }) {
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();

  const handleSubmit = async (values) => {
    setLoading(true);
    try {
      const res = await apiLogin(values.username, values.password);
      const data = res.data.data;
      // Save tokens
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);
      localStorage.setItem("user", JSON.stringify(data.user));
      message.success("登录成功，欢迎 " + data.user.full_name);
      onLogin(data.user);
    } catch (e) {
      const msg = e.response?.data?.detail || "登录失败";
      message.error(msg);
    }
    setLoading(false);
  };

  return (
    <div style={{
      display: "flex", justifyContent: "center", alignItems: "center",
      minHeight: "100vh", background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
    }}>
      <Card style={{ width: 400, boxShadow: "0 8px 32px rgba(0,0,0,0.2)", borderRadius: 12 }}>
        <div style={{ textAlign: "center", marginBottom: 24 }}>
          <ThunderboltOutlined style={{ fontSize: 48, color: "#667eea" }} />
          <Title level={3} style={{ marginTop: 8, marginBottom: 4 }}>AI自动上架系统</Title>
          <Text type="secondary">全平台智能商品管理</Text>
        </div>
        <Form form={form} onFinish={handleSubmit} size="large">
          <Form.Item name="username" rules={[{ required: true, message: "请输入用户名" }]}>
            <Input prefix={<UserOutlined />} placeholder="用户名" autoFocus />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: "请输入密码" }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="密码" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              登录
            </Button>
          </Form.Item>
          <Text type="secondary" style={{ display: "block", textAlign: "center" }}>
            默认账户: admin / admin123
          </Text>
        </Form>
      </Card>
    </div>
  );
}
