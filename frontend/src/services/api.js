import axios from 'axios';

// 开发环境直连后端，生产环境 (Docker/nginx) 走反向代理 /api
const BASE = process.env.REACT_APP_API_URL || '/api';

const api = axios.create({
  baseURL: BASE,
  timeout: 15000,
});

// 产品源
export const crawlProduct = (url) => api.post('/product/crawl', { source_url: url });
export const createProduct = (data) => api.post('/product/manual/create', data);
export const getProductList = (skip = 0, limit = 20) => api.get('/product/master/list', { params: { skip, limit } });
export const getProductDetail = (id) => api.get(`/product/master/${id}`);

// 调度
export const dispatchProduct = (masterId, platforms) =>
  api.post(`/product/dispatch/${masterId}?platforms=${platforms}`);
export const createTask = (jobType, masterId, platform) =>
  api.post(`/task/create?job_type=${jobType}&master_id=${masterId}&platform=${platform}`);
export const getTaskList = () => api.get('/task/list');

// AI
export const aiAudit = (title, desc, attrs) => api.post('/ai/audit', { title, desc, attrs });
export const aiGenTitle = (productInfo, platform) => api.post('/ai/gen_title', { product_info: productInfo, platform });
export const aiOptimizeDesc = (title, desc, attrs) => api.post('/ai/optimize_desc', { title, desc, attrs });
export const aiKeywords = (title, desc) => api.post('/ai/keywords', { title, desc });

// 审核发布
export const getPendingAudit = () => api.get('/audit/pending/list');
export const submitAudit = (relId, approved, comment) =>
  api.post(`/audit/submit?rel_id=${relId}&approved=${approved}&comment=${comment}`);
export const publishProduct = (draftId, platform) =>
  api.post('/publish/execute', { draft_id: draftId, platform, user_id: 'admin' });
export const getPublishStatus = (draftId) => api.get(`/publish/status/${draftId}`);

// AI配置
export const getAIConfig = () => api.get('/ai/config');
export const setAIKey = (apiKey) => api.post('/ai/config/key', { api_key: apiKey });
export const setAIProvider = (provider) => api.post('/ai/config/provider', { provider });
export const setAIModel = (model) => api.post('/ai/config/model', { model });
export const testAIConnection = () => api.post('/ai/config/test');

// 流水线
export const runPipeline = (masterId, platforms) =>
  api.post('/pipeline/run', { master_id: masterId, platforms });
export const getPipelineTasks = () => api.get('/pipeline/tasks');
export const getPipelineTask = (taskId) => api.get(`/pipeline/task/${taskId}`);

// 工作台
export const getDashboardStats = () => api.get('/dashboard/stats');

// 图片处理
export const processImage = (file, operations, watermarkText, platform) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('operations', operations);
  formData.append('watermark_text', watermarkText || '');
  formData.append('platform', platform || 'taobao');
  return api.post('/image/process', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};
export const getImageSpecs = () => api.get('/image/specs');

export default api;
