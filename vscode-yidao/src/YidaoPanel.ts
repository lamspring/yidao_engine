import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { ApiClient } from './apiClient';

export class YidaoPanel {
    public static currentPanel: YidaoPanel | undefined;
    private readonly _panel: vscode.WebviewPanel;
    private readonly _extensionUri: vscode.Uri;
    private _api: ApiClient;
    private _disposables: vscode.Disposable[] = [];

    private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri, api: ApiClient) {
        this._panel = panel;
        this._extensionUri = extensionUri;
        this._api = api;

        this._panel.webview.html = this._getHtmlForWebview(this._panel.webview);

        this._panel.webview.onDidReceiveMessage(
            async (message) => {
                try {
                    await this._handleMessage(message);
                } catch (err: any) {
                    this._panel.webview.postMessage({
                        type: 'error',
                        text: err.message || String(err),
                    });
                }
            },
            null,
            this._disposables
        );

        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);

        // 定时刷新状态
        this._refreshStatus();
        const interval = setInterval(() => this._refreshStatus(), 3000);
        this._disposables.push({ dispose: () => clearInterval(interval) } as vscode.Disposable);
    }

    public static createOrShow(extensionUri: vscode.Uri, api: ApiClient) {
        const column = vscode.ViewColumn.Two;
        if (YidaoPanel.currentPanel) {
            YidaoPanel.currentPanel._panel.reveal(column);
            return;
        }
        const panel = vscode.window.createWebviewPanel(
            'yidaoPanel',
            '易道推演',
            column,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
                localResourceRoots: [vscode.Uri.joinPath(extensionUri, 'media')],
            }
        );
        YidaoPanel.currentPanel = new YidaoPanel(panel, extensionUri, api);
    }

    public dispose() {
        YidaoPanel.currentPanel = undefined;
        this._panel.dispose();
        while (this._disposables.length) {
            const x = this._disposables.pop();
            if (x) { x.dispose(); }
        }
    }

    private async _handleMessage(message: any) {
        const { command, payload } = message;
        let result: any;

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

    private async _refreshStatus() {
        try {
            const status = await this._api.status();
            this._panel.webview.postMessage({
                type: 'status',
                data: status,
            });
        } catch {
            // 忽略状态刷新错误
        }
    }

    private _getHtmlForWebview(webview: vscode.Webview): string {
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
