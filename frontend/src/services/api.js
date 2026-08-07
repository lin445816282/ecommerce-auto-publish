import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8800/api',
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

export default api;
