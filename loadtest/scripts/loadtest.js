// Stage 14 Day 1: k6 load test script
// 7 核心端点，read-heavy 80/20（5 read + 2 write 装饰）
// 设计：login + customers/products/commissions 列表 + dashboard/stats 聚合
//
// 用法：
//   k6 run --vus 10 --duration 30s scripts/loadtest.js                  # smoke
//   k6 run --out json=results/load-50vu.json scripts/loadtest.js        # load
//   k6 run --stage 30s:10,1m:50,30s:100,30s:0 scripts/loadtest.js      # ramp

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';
import { SharedArray } from 'k6/data';

const BASE = __ENV.BASE_URL || 'http://localhost:8080';
const USERNAME = __ENV.AIERP_LOGIN_USERNAME || 'admin';
const PASSWORD = __ENV.AIERP_LOGIN_PASSWORD || 'admin123';

// 自定义 metrics
const loginDuration = new Trend('login_duration', true);
const listDuration = new Trend('list_duration', true);
const detailDuration = new Trend('detail_duration', true);
const statsDuration = new Trend('stats_duration', true);
const errors = new Rate('errors');

export const options = {
  thresholds: {
    http_req_duration: ['p(95)<500'],   // P95 < 500ms
    http_req_failed: ['rate<0.01'],      // 错误率 < 1%
    errors: ['rate<0.05'],
  },
};

export function setup() {
  // 共享 token (但 k6 VU 隔离，每个 VU 仍需 login)
  return { base: BASE, username: USERNAME, password: PASSWORD };
}

function login() {
  const res = http.post(
    `${BASE}/api/v1/auth/login`,
    JSON.stringify({ username: USERNAME, password: PASSWORD }),
    { headers: { 'Content-Type': 'application/json' } }
  );
  loginDuration.add(res.timings.duration);
  const ok = check(res, {
    'login 200': (r) => r.status === 200,
    'login token': (r) => {
      try {
        const j = JSON.parse(r.body);
        return j && j.data && typeof j.data.token === 'string';
      } catch (e) {
        return false;
      }
    },
  });
  if (!ok) errors.add(1);
  else errors.add(0);
  if (res.status !== 200) return null;
  return JSON.parse(res.body).data.token;
}

function authHeaders(token) {
  return { headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' } };
}

// 主场景：80% 读 / 20% 列表
export default function () {
  // 1) login
  const token = login();
  if (!token) {
    sleep(1);
    return;
  }
  const h = authHeaders(token);

  // 2) customers list (page 1)  — 最常用
  const r1 = http.get(`${BASE}/api/v1/customers?page=1&page_size=20`, h);
  listDuration.add(r1.timings.duration);
  errors.add(r1.status !== 200);

  // 3) customers detail (随机 ID 1-355)
  const cid = Math.floor(Math.random() * 355) + 1;
  const r2 = http.get(`${BASE}/api/v1/customers/${cid}`, h);
  detailDuration.add(r2.timings.duration);
  errors.add(r2.status !== 200);

  // 4) products list
  const r3 = http.get(`${BASE}/api/v1/products?page=1&page_size=20`, h);
  listDuration.add(r3.timings.duration);
  errors.add(r3.status !== 200);

  // 5) commissions list
  const r4 = http.get(`${BASE}/api/v1/finance/commissions?page=1&page_size=20`, h);
  listDuration.add(r4.timings.duration);
  errors.add(r4.status !== 200);

  // 6) dashboard overview (聚合查询)
  const r5 = http.get(`${BASE}/api/v1/sales/dashboard/overview`, h);
  statsDuration.add(r5.timings.duration);
  errors.add(r5.status !== 200);

  // 7) inventory overview
  const r6 = http.get(`${BASE}/api/v1/inventory/overview`, h);
  statsDuration.add(r6.timings.duration);
  errors.add(r6.status !== 200);

  // 8) stats aggregations
  const r7 = http.get(`${BASE}/api/v1/customers/stats`, h);
  statsDuration.add(r7.timings.duration);
  errors.add(r7.status !== 200);

  sleep(0.5);  // 模拟用户思考时间
}
