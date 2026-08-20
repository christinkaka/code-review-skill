/**
 * 安全示例：SSRF 防护 - TypeScript
 *
 * 安全说明：
 * 通过白名单机制校验用户提供的 URL，
 * 仅允许请求预定义的可信域名，拒绝所有其他请求。
 *
 * 预期检出：无（不应被检出为漏洞）
 */

import { URL } from "url";
import dns from "dns";
import { promisify } from "util";

const dnsResolve = promisify(dns.resolve);

// 允许的域名白名单
const ALLOWED_HOSTS = new Set([
  "api.example.com",
  "cdn.example.com",
  "data.example.com",
]);

/**
 * 安全：使用域名白名单校验 URL
 */
async function fetchUserData(url: string): Promise<Response> {
  const parsed = new URL(url);

  // 安全：白名单校验域名
  if (!ALLOWED_HOSTS.has(parsed.hostname)) {
    throw new Error(`Host not allowed: ${parsed.hostname}`);
  }

  // 安全：仅允许 HTTPS 协议
  if (parsed.protocol !== "https:") {
    throw new Error(`Protocol not allowed: ${parsed.protocol}`);
  }

  const response = await fetch(url);
  return response;
}

/**
 * 安全：DNS 解析后校验 IP，防止 DNS Rebinding 攻击
 */
async function isSafeHost(hostname: string): Promise<boolean> {
  // 安全：DNS 解析后检查 IP 是否为内网地址
  const addresses = await dnsResolve(hostname);
  const blockedPrefixes = ["10.", "172.16.", "172.17.", "192.168.", "127.", "0.", "169.254."];

  for (const addr of addresses) {
    if (blockedPrefixes.some((prefix) => addr.startsWith(prefix))) {
      return false;
    }
  }
  return true;
}

/**
 * 安全：完整的 SSRF 防护（白名单 + DNS 校验）
 */
async function safeProxyRequest(targetUrl: string): Promise<void> {
  const parsed = new URL(targetUrl);

  // 安全：白名单校验
  if (!ALLOWED_HOSTS.has(parsed.hostname)) {
    throw new Error(`Host not allowed: ${parsed.hostname}`);
  }

  // 安全：DNS 解析校验
  const safe = await isSafeHost(parsed.hostname);
  if (!safe) {
    throw new Error(`DNS resolution points to internal network: ${parsed.hostname}`);
  }

  // 安全：仅允许 HTTPS
  if (parsed.protocol !== "https:") {
    throw new Error("Only HTTPS is allowed");
  }

  await fetch(targetUrl);
}
