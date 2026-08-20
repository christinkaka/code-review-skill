/**
 * 漏洞示例：SSRF（Server-Side Request Forgery）服务端请求伪造 - TypeScript
 *
 * 问题说明：
 * 使用用户输入的 URL 发起服务端请求，未做任何校验，
 * 攻击者可以让服务器访问内网资源或元数据服务。
 *
 * 预期检出：
 * - 行号：21, 33, 44
 * - 规则 ID：ssrf-ts-fetch-user-input
 * - 严重级别：ERROR
 */

import https from "https";
import http from "http";

/**
 * 漏洞：fetch 使用用户输入的 URL
 */
async function fetchUserData(url: string): Promise<Response> {
  // 漏洞：直接使用用户输入的 URL 发起请求，未校验目标地址
  const response = await fetch(url); // 第 22 行 - SSRF 漏洞点
  return response;
}

/**
 * 漏洞：http.get 使用用户输入的 URL
 */
function proxyRequest(targetUrl: string): void {
  // 漏洞：直接使用用户输入的 URL 发起 HTTP 请求
  http.get(targetUrl, (res) => { // 第 30 行 - SSRF 漏洞点
    let data = "";
    res.on("data", (chunk) => {
      data += chunk;
    });
  });
}

/**
 * 漏洞：axios 使用用户输入的 URL
 */
async function fetchData(apiUrl: string): Promise<unknown> {
  // 漏洞：直接使用用户输入的 URL
  const response = await fetch(apiUrl, { // 第 44 行 - SSRF 漏洞点
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
  return response.json();
}

/**
 * 漏洞：仅做简单字符串检查，可被绕过
 */
async function fetchWithWeakCheck(url: string): Promise<Response> {
  // 漏洞：仅检查是否包含 "localhost"，可被 127.0.0.1 或 0.0.0.0 绕过
  if (url.includes("localhost")) {
    throw new Error("Blocked");
  }
  return await fetch(url); // 第 59 行 - SSRF 漏洞点（不完整的过滤）
}
