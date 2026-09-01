(function () {
    const vscode = acquireVsCodeApi();

    // DOM 元素
    const els = {
        tick: document.getElementById('status-tick'),
        focus: document.getElementById('status-focus'),
        variant: document.getElementById('status-variant'),
        narratives: document.getElementById('status-narratives'),
        tokens: document.getElementById('status-tokens'),
        entitiesBody: document.querySelector('#entities-table tbody'),
        logOutput: document.getElementById('log-output'),
        narrativeOutput: document.getElementById('narrative-output'),
        stepTicks: document.getElementById('step-ticks'),
        selectFocus: document.getElementById('select-focus'),
        selectVariant: document.getElementById('select-variant'),
        sessionName: document.getElementById('session-name'),
    };

    // 按钮事件绑定
    document.getElementById('btn-step').addEventListener('click', () => {
        const ticks = parseInt(els.stepTicks.value, 10) || 150;
        sendCommand('step', { ticks });
        log(`推进 ${ticks} ticks...`, 'info');
    });

    document.getElementById('btn-explain').addEventListener('click', () => {
        sendCommand('explain');
        log('生成叙事中...', 'info');
        els.narrativeOutput.innerHTML = '<p style="color:#858585">生成中...</p>';
    });

    document.getElementById('btn-reroll').addEventListener('click', () => {
        sendCommand('reroll');
        log('重新生成叙事...', 'info');
        els.narrativeOutput.innerHTML = '<p style="color:#858585">重新生成中...</p>';
    });

    document.getElementById('btn-reset').addEventListener('click', () => {
        if (confirm('确定要重置世界吗？叙事历史将清空。')) {
            sendCommand('reset');
            log('世界已重置', 'warn');
            els.narrativeOutput.innerHTML = '';
        }
    });

    document.getElementById('btn-focus').addEventListener('click', () => {
        const target = els.selectFocus.value;
        sendCommand('focus', { target });
        log(`聚焦已设置为: ${target}`, 'info');
    });

    document.getElementById('btn-variant').addEventListener('click', () => {
        const tag = els.selectVariant.value || null;
        sendCommand('variant', { tag });
        log(`变体已锁定为: ${tag || '无'}`, 'info');
    });

    document.getElementById('btn-save').addEventListener('click', () => {
        const name = els.sessionName.value.trim() || 'session';
        sendCommand('save', { name });
        log(`保存会话: ${name}`, 'info');
    });

    document.getElementById('btn-load').addEventListener('click', () => {
        const name = els.sessionName.value.trim() || 'session';
        sendCommand('load', { name });
        log(`加载会话: ${name}`, 'info');
    });

    // 接收 Extension 消息
    window.addEventListener('message', (event) => {
        const msg = event.data;
        switch (msg.type) {
            case 'status':
                updateStatus(msg.data);
                break;
            case 'result':
                handleResult(msg.command, msg.data);
                break;
            case 'error':
                log(`错误: ${msg.text}`, 'error');
                break;
        }
    });

    // 配置面板交互
    const configToggle = document.getElementById('config-toggle');
    const configBody = document.getElementById('config-body');
    const toggleIcon = configToggle.querySelector('.toggle-icon');
    let configOpen = true;
    configToggle.addEventListener('click', () => {
        configOpen = !configOpen;
        configBody.style.display = configOpen ? 'block' : 'none';
        toggleIcon.textContent = configOpen ? '▼' : '▶';
    });

    // API Key 显示/隐藏
    const apiKeyInput = document.getElementById('cfg-apikey');
    document.getElementById('btn-toggle-key').addEventListener('click', () => {
        apiKeyInput.type = apiKeyInput.type === 'password' ? 'text' : 'password';
    });

    // 应用配置
    document.getElementById('btn-apply-config').addEventListener('click', () => {
        const provider = document.getElementById('cfg-provider').value;
        const apiKey = document.getElementById('cfg-apikey').value.trim() || null;
        const worldview = document.getElementById('cfg-worldview').value || null;
        const mode = document.getElementById('cfg-mode').value;
        const style = document.getElementById('cfg-style').value;

        document.getElementById('cfg-status').textContent = '初始化中...';
        sendCommand('reinit', { provider, apiKey, worldview, mode, style });
        log(`重新初始化世界 | provider=${provider} mode=${mode} style=${style}`, 'info');
    });

    // 初始化时请求状态
    sendCommand('status');

    // ── 辅助函数 ──

    function sendCommand(command, payload = {}) {
        vscode.postMessage({ command, payload });
    }

    function updateStatus(data) {
        if (!data) return;
        els.tick.textContent = data.tick ?? 0;
        els.focus.textContent = data.camera?.focus ?? 'family';
        els.variant.textContent = data.camera?.variant_lock ?? '无';
        els.narratives.textContent = data.narrative_count ?? 0;
        els.tokens.textContent = data.tokens_used ?? 0;

        // 更新实体表格
        if (data.entities && data.entities.length > 0) {
            els.entitiesBody.innerHTML = data.entities.map(e => `
                <tr>
                    <td>${e.id}</td>
                    <td>${e.gua}</td>
                    <td>${e.protocol}</td>
                    <td>${e.phase}</td>
                    <td>${e.pot}</td>
                </tr>
            `).join('');
        }
    }

    function handleResult(command, data) {
        if (data.error) {
            log(`[${command}] 失败: ${data.error}`, 'error');
            return;
        }

        switch (command) {
            case 'step':
                if (data.error) {
                    log(`推进失败: ${data.error}`, 'error');
                } else {
                    const flip = data.flip_detected ? ` ⚡ ${data.new_flips?.length || 0} 次卦变` : ' 稳态';
                    log(`推进完成 | tick=${data.end_tick}${flip}`, 'success');
                }
                break;
            case 'explain':
                if (data.output) {
                    renderNarrative(data.output);
                    log(`叙事生成完成 | tokens=${data.tokens_used}`, 'success');
                }
                break;
            case 'reroll':
                if (data.output) {
                    renderNarrative(data.output);
                    log(`重新生成完成 | tokens=${data.tokens_used}`, 'success');
                }
                break;
            case 'reset':
                log('世界已重置', 'warn');
                els.narrativeOutput.innerHTML = '';
                break;
            case 'save':
                log(`会话已保存: ${data.path}`, 'success');
                break;
            case 'load':
                log(data.loaded ? '会话加载成功' : '会话加载失败', data.loaded ? 'success' : 'error');
                break;
            case 'focus':
                log(`聚焦: ${data.focus}`, 'info');
                break;
            case 'variant':
                log(`变体: ${data.variant_lock || '无'}`, 'info');
                break;
            case 'reinit':
                if (data.error) {
                    document.getElementById('cfg-status').textContent = '失败';
                    log(`初始化失败: ${data.error}`, 'error');
                } else {
                    document.getElementById('cfg-status').textContent = '已应用';
                    log(`世界已初始化 | provider=${data.provider} mode=${data.mode} tick=${data.tick}`, 'success');
                    els.narrativeOutput.innerHTML = '';
                }
                break;
        }
    }

    function renderNarrative(text) {
        // 简单 Markdown 渲染
        let html = escapeHtml(text)
            .replace(/^# (.*$)/gim, '<h1>$1</h1>')
            .replace(/^## (.*$)/gim, '<h2>$1</h2>')
            .replace(/^### (.*$)/gim, '<h3>$1</h3>')
            .replace(/^---$/gim, '<hr>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/^\s*[-*] (.*$)/gim, '<li>$1</li>')
            .replace(/<li>(.*?)<\/li>\n/g, '<ul><li>$1</li></ul>\n')
            .replace(/\n/g, '<br>');
        els.narrativeOutput.innerHTML = html;
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function log(text, type = 'info') {
        const entry = document.createElement('div');
        entry.className = `log-entry ${type}`;
        const time = new Date().toLocaleTimeString('zh-CN', { hour12: false });
        entry.textContent = `[${time}] ${text}`;
        els.logOutput.appendChild(entry);
        els.logOutput.scrollTop = els.logOutput.scrollHeight;
    }
})();
