"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ApiClient = void 0;
class ApiClient {
    constructor(port) {
        this.baseUrl = `http://127.0.0.1:${port}`;
    }
    async get(path) {
        const res = await fetch(`${this.baseUrl}${path}`);
        if (!res.ok) {
            throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }
        return res.json();
    }
    async post(path, body = {}) {
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
    async init(config) {
        return this.post('/init', config);
    }
    async step(ticks) {
        return this.post('/step', { ticks });
    }
    async explain() {
        return this.post('/explain');
    }
    async reroll() {
        return this.post('/reroll');
    }
    async status() {
        return this.get('/status');
    }
    async focus(target) {
        return this.post('/focus', { target });
    }
    async variant(tag) {
        return this.post('/variant', { tag: tag ?? null });
    }
    async reset() {
        return this.post('/reset');
    }
    async save(name) {
        return this.post('/save', { name });
    }
    async load(name) {
        return this.post('/load', { name });
    }
    async shutdown() {
        return this.post('/shutdown');
    }
}
exports.ApiClient = ApiClient;
//# sourceMappingURL=apiClient.js.map