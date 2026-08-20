/**
 * 漏洞示例：XSS（Cross-Site Scripting）跨站脚本攻击 - TypeScript
 *
 * 问题说明：
 * 直接将用户输入赋值给 innerHTML 或使用 document.write，
 * 未进行任何编码或消毒，攻击者可以注入恶意脚本。
 *
 * 预期检出：
 * - 行号：20, 30, 39
 * - 规则 ID：xss-js-innerhtml
 * - 严重级别：ERROR
 */

/**
 * 漏洞：直接将用户输入赋值给 innerHTML
 */
function displayUserName(input: string): void {
  const container = document.getElementById("user-display");
  if (container) {
    // 漏洞：直接将用户输入赋值给 innerHTML，未进行消毒
    container.innerHTML = `<h1>Welcome, ${input}</h1>`; // 第 21 行 - XSS 漏洞点
  }
}

/**
 * 漏洞：使用 document.write 直接输出用户输入
 */
function renderComment(comment: string): void {
  // 漏洞：document.write 直接输出用户输入
  document.write(`<div class="comment">${comment}</div>`); // 第 30 行 - XSS 漏洞点
}

/**
 * 漏洞：使用 outerHTML 注入用户输入
 */
function updateElement(userContent: string): void {
  const el = document.getElementById("content");
  if (el) {
    // 漏洞：outerHTML 直接赋值用户输入
    el.outerHTML = `<section>${userContent}</section>`; // 第 39 行 - XSS 漏洞点
  }
}

/**
 * 漏洞：使用 dangerouslySetInnerHTML（React 场景）
 */
function createReactElement(userInput: string): string {
  // 漏洞：模拟 React 的 dangerouslySetInnerHTML
  const props = {
    dangerouslySetInnerHTML: { __html: userInput }, // 第 48 行 - XSS 漏洞点
  };
  return JSON.stringify(props);
}
