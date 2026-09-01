"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.YidaoPanel = void 0;
const vscode = __importStar(require("vscode"));
const path = __importStar(require("path"));
const fs = __importStar(require("fs"));
class YidaoPanel {
    constructor(panel, extensionUri, api) {
        this._disposables = [];
        this._panel = panel;
        this._extensionUri = extensionUri;
        this._api = api;
        this._panel.webview.html = this._getHtmlForWebview(this._panel.webview);
        this._panel.webview.onDidReceiveMessage(async (message) => {
            try {
                await this._handleMessage(message);
            }
            catch (err) {
                this._panel.webview.postMessage({
                    type: 'error',
                    text: err.message || String(err),
                });
            }
        }, null, this._disposables);
        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);
        // 定时刷新状态
        this._refreshStatus();
        const interval = setInterval(() => this._refreshStatus(), 3000);
        this._disposables.push({ dispose: () => clearInterval(interval) });
    }
    static createOrShow(extensionUri, api) {
        const column = vscode.ViewColumn.Two;
        if (YidaoPanel.currentPanel) {
            YidaoPanel.currentPanel._panel.reveal(column);
            return;
        }
        const panel = vscode.window.createWebviewPanel('yidaoPanel', '易道推演', column, {
            enableScripts: true,
            retainContextWhenHidden: true,
            localResourceRoots: [vscode.Uri.joinPath(extensionUri, 'media')],
        });
        YidaoPanel.currentPanel = new YidaoPanel(panel, extensionUri, api);
    }
    dispose() {
        YidaoPanel.currentPanel = undefined;
        this._panel.dispose();
        while (this._disposables.length) {
            const x = this._disposables.pop();
            if (x) {
                x.dispose();
            }
        }
    }
    async _handleMessage(message) {
        const { command, payload } = message;
        let result;
        switch (command) {
            case 'init':
            case 'reinit':
                result = await this._api.init(payload);
                break;
            case 'step':
                result = await this._api.step(payload.ticks);
                break;
            case 'explain':
                result = await this._api.explain();
                break;
            case 'reroll':
                result = await this._api.reroll();
                break;
            case 'status':
                result = await this._api.status();
                break;
            case 'focus':
                result = await this._api.focus(payload.target);
                break;
            case 'variant':
                result = await this._api.variant(payload.tag);
                break;
            case 'reset':
                result = await this._api.reset();
                break;
            case 'save':
                result = await this._api.save(payload.name);
                break;
            case 'load':
                result = await this._api.load(payload.name);
                break;
            default:
                return;
        }
        this._panel.webview.postMessage({
            type: 'result',
            command,
            data: result,
        });
        // 自动刷新状态
        if (['step', 'explain', 'reroll', 'reset', 'focus', 'variant', 'load'].includes(command)) {
            await this._refreshStatus();
        }
    }
    async _refreshStatus() {
        try {
            const status = await this._api.status();
            this._panel.webview.postMessage({
                type: 'status',
                data: status,
            });
        }
        catch {
            // 忽略状态刷新错误
        }
    }
    _getHtmlForWebview(webview) {
        const mediaPath = vscode.Uri.joinPath(this._extensionUri, 'media');
        const htmlUri = webview.asWebviewUri(vscode.Uri.joinPath(mediaPath, 'index.html'));
        const cssUri = webview.asWebviewUri(vscode.Uri.joinPath(mediaPath, 'style.css'));
        const jsUri = webview.asWebviewUri(vscode.Uri.joinPath(mediaPath, 'main.js'));
        // 直接读取 index.html 并替换路径
        const indexPath = path.join(this._extensionUri.fsPath, 'media', 'index.html');
        let html = fs.readFileSync(indexPath, 'utf-8');
        html = html.replace('{{styleUri}}', cssUri.toString());
        html = html.replace('{{scriptUri}}', jsUri.toString());
        return html;
    }
}
exports.YidaoPanel = YidaoPanel;
//# sourceMappingURL=YidaoPanel.js.map