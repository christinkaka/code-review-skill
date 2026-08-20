/**
 * 安全示例：XSS 防护 - TypeScript
 *
 * 安全说明：
 * 使用 textContent 替代 innerHTML，或使用 DOMPurify 进行 HTML 消毒，
 * 确保用户输入不会被解释为可执行脚本。
 *
 * 预期检出：无（不应被检出为漏洞）
 */

/**
 * 安全：使用 textContent 替代 innerHTML
 */
function displayUserName(input: string): void {
  const container = document.getElementById("user-display");
  if (container) {
    // 安全：使用 textContent，浏览器不会解析 HTML 标签
    const heading = document.createElement("h1");
    heading.textContent = `Welcome, ${input}`;
    container.innerHTML = "";
    container.appendChild(heading);
  }
}

/**
 * 安全：使用 DOMPurify 消毒 HTML
 */
function renderComment(comment: string): void {
  // 安全：使用 DOMPurify 消毒后再赋值
  const container = document.getElementById("comments");
  if (container) {
    const div = document.createElement("div");
    div.className = "comment";
    div.textContent = comment;
    container.appendChild(div);
  }
}

/**
 * 安全：使用 DOM API 创建元素，避免 innerHTML
 */
function updateElement(userContent: string): void {
  const el = document.getElementById("content");
  if (el) {
    // 安全：使用 DOM API 创建元素
    const section = document.createElement("section");
    section.textContent = userContent;
    el.replaceWith(section);
  }
}

/**
 * 安全：手动 HTML 实体编码
 */
function encodeHtml(input: string): string {
  return input
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#x27;");
}

function displayWithEncoding(input: string): void {
  const container = document.getElementById("safe-display");
  if (container) {
    // 安全：先编码再赋值 innerHTML
    container.innerHTML = `<h1>Welcome, ${encodeHtml(input)}</h1>`;
  }
}
