import * as vscode from 'vscode';

export class ApiClient {
    private baseUrl: string;

    constructor(port: number) {
        this.baseUrl = `http://127.0.0.1:${port}`;
    }

    async get(path: string): Promise<any> {
        const res = await fetch(`${this.baseUrl}${path}`);
        if (!res.ok) {
            throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }
        return res.json();
    }

    async post(path: string, body: object = {}): Promise<any> {
        const res = await fetch(`${this.baseUrl}${path}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (!res.ok) {
            throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }
        return res.json();
    }

    async init(config: { mode: string; provider: string; worldview?: string | null; style?: string }): Promise<any> {
        return this.post('/init', config);
    }

    async step(ticks: number): Promise<any> {
        return this.post('/step', { ticks });
    }

    async explain(): Promise<any> {
        return this.post('/explain');
    }

    async reroll(): Promise<any> {
        return this.post('/reroll');
    }

    async status(): Promise<any> {
        return this.get('/status');
    }

    async focus(target: string): Promise<any> {
        return this.post('/focus', { target });
    }

    async variant(tag: string | null): Promise<any> {
        return this.post('/variant', { tag: tag ?? null });
    }

    async reset(): Promise<any> {
        return this.post('/reset');
    }

    async save(name: string): Promise<any> {
        return this.post('/save', { name });
    }

    async load(name: string): Promise<any> {
        return this.post('/load', { name });
    }

    async shutdown(): Promise<any> {
        return this.post('/shutdown');
    }
}
