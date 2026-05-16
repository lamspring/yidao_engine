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
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const path = __importStar(require("path"));
const fs = __importStar(require("fs"));
const child_process = __importStar(require("child_process"));
const YidaoPanel_1 = require("./YidaoPanel");
const apiClient_1 = require("./apiClient");
let serverProcess = null;
let apiClient = null;
let outputChannel;
function activate(context) {
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
            const choice = await vscode.window.showInformationMessage('推演服务器未运行，是否现在启动？', '启动', '取消');
            if (choice === '启动') {
                await startServer(context);
            }
            else {
                return;
            }
        }
        if (apiClient) {
            YidaoPanel_1.YidaoPanel.createOrShow(context.extensionUri, apiClient);
        }
    });
    context.subscriptions.push(startServerCmd, stopServerCmd, openPanelCmd);
}
function deactivate() {
    stopServer();
    outputChannel?.dispose();
}
async function startServer(context) {
    const config = vscode.workspace.getConfiguration('yidao');
    const pythonPath = config.get('pythonPath', 'python');
    const port = config.get('apiPort', 8765);
    const mode = config.get('mode', 'family');
    const provider = config.get('provider', 'deepseek');
    const worldview = config.get('worldview', null);
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
    apiClient = new apiClient_1.ApiClient(port);
    let retries = 10;
    while (retries-- > 0) {
        await new Promise(r => setTimeout(r, 500));
        try {
            const status = await apiClient.status();
            if (status.initialized) {
                vscode.window.showInformationMessage('推演服务器已启动');
                return;
            }
        }
        catch {
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
//# sourceMappingURL=extension.js.map