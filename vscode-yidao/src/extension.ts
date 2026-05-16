import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import * as child_process from 'child_process';
import { YidaoPanel } from './YidaoPanel';
import { ApiClient } from './apiClient';

let serverProcess: child_process.ChildProcess | null = null;
let apiClient: ApiClient | null = null;
let outputChannel: vscode.OutputChannel;

export function activate(context: vscode.ExtensionContext) {
    outputChannel = vscode.window.createOutputChannel('易道引擎');
    outputChannel.appendLine('[易道] 扩展已激活');

    // 命令：启动服务器
    const startServerCmd = vscode.commands.registerCommand('yidao.startServer', async () => {
        if (serverProcess) {
            vscode.window.showInformationMessage('推演服务器已在运行');
            return;
        }
        await startServer(context);
    });

    // 命令：停止服务器
    const stopServerCmd = vscode.commands.registerCommand('yidao.stopServer', () => {
        stopServer();
        vscode.window.showInformationMessage('推演服务器已停止');
    });

    // 命令：打开面板
    const openPanelCmd = vscode.commands.registerCommand('yidao.openPanel', async () => {
        if (!serverProcess) {
            const choice = await vscode.window.showInformationMessage(
                '推演服务器未运行，是否现在启动？',
                '启动', '取消'
            );
            if (choice === '启动') {
                await startServer(context);
            } else {
                return;
            }
        }
        if (apiClient) {
            YidaoPanel.createOrShow(context.extensionUri, apiClient);
        }
    });

    context.subscriptions.push(startServerCmd, stopServerCmd, openPanelCmd);
}

export function deactivate() {
    stopServer();
    outputChannel?.dispose();
}

async function startServer(context: vscode.ExtensionContext) {
    const config = vscode.workspace.getConfiguration('yidao');
    const pythonPath = config.get<string>('pythonPath', 'python');
    const port = config.get<number>('apiPort', 8765);
    const mode = config.get<string>('mode', 'family');
    const provider = config.get<string>('provider', 'deepseek');
    const worldview = config.get<string | null>('worldview', null);

    // 优先在当前扩展目录查找 api_server.py，否则去父目录（开发模式）
    let apiServerPath = path.join(context.extensionUri.fsPath, 'api_server.py');
    if (!fs.existsSync(apiServerPath)) {
        apiServerPath = path.join(context.extensionUri.fsPath, '..', 'api_server.py');
    }

    const args = [
        apiServerPath,
        '--port', String(port),
        '--mode', mode,
        '--provider', provider,
    ];
    if (worldview) {
        args.push('--worldview', worldview);
    }

    outputChannel.appendLine(`[易道] 启动服务器: ${pythonPath} ${args.join(' ')}`);

    serverProcess = child_process.spawn(pythonPath, args, {
        cwd: path.dirname(apiServerPath),
        detached: false,
    });

    serverProcess.stdout?.on('data', (data) => {
        outputChannel.append(data.toString());
    });
    serverProcess.stderr?.on('data', (data) => {
        outputChannel.append(data.toString());
    });
    serverProcess.on('close', (code) => {
        outputChannel.appendLine(`[易道] 服务器退出 (code ${code})`);
        serverProcess = null;
    });

    // 等待服务器启动
    apiClient = new ApiClient(port);
    let retries = 10;
    while (retries-- > 0) {
        await new Promise(r => setTimeout(r, 500));
        try {
            const status = await apiClient.status();
            if (status.initialized) {
                vscode.window.showInformationMessage('推演服务器已启动');
                return;
            }
        } catch {
            // 继续等待
        }
    }
    vscode.window.showErrorMessage('推演服务器启动超时，请检查输出面板');
}

function stopServer() {
    if (serverProcess) {
        serverProcess.kill('SIGTERM');
        serverProcess = null;
    }
    apiClient = null;
}
