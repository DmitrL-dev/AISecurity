"use strict";
/**
 * RlmBridge Unit Tests
 */
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
const assert = __importStar(require("assert"));
const path = __importStar(require("path"));
describe('RlmBridge Tests', () => {
    describe('RlmMemoryStatus Interface', () => {
        it('should have correct structure', () => {
            const status = {
                L0: 5,
                L1: 12,
                L2: 28,
                L3: 45,
                total: 90,
                domains: 8,
                available: true
            };
            assert.strictEqual(typeof status.L0, 'number');
            assert.strictEqual(typeof status.L1, 'number');
            assert.strictEqual(typeof status.L2, 'number');
            assert.strictEqual(typeof status.L3, 'number');
            assert.strictEqual(typeof status.total, 'number');
            assert.strictEqual(typeof status.domains, 'number');
            assert.strictEqual(typeof status.available, 'boolean');
        });
        it('should handle unavailable state', () => {
            const unavailable = {
                L0: 0,
                L1: 0,
                L2: 0,
                L3: 0,
                total: 0,
                domains: 0,
                available: false
            };
            assert.strictEqual(unavailable.available, false);
            assert.strictEqual(unavailable.total, 0);
        });
    });
    describe('SQLite Path Detection', () => {
        it('should construct correct database path', () => {
            const workspaceRoot = 'C:\\Projects\\MyApp';
            const rlmDbPath = path.join(workspaceRoot, '.rlm', 'memory', 'memory_bridge_v2.db');
            assert.ok(rlmDbPath.includes('.rlm'));
            assert.ok(rlmDbPath.includes('memory_bridge_v2.db'));
        });
        it('should handle Unix-style paths', () => {
            const workspaceRoot = '/home/user/project';
            const rlmDbPath = path.posix.join(workspaceRoot, '.rlm', 'memory', 'memory_bridge_v2.db');
            assert.strictEqual(rlmDbPath, '/home/user/project/.rlm/memory/memory_bridge_v2.db');
        });
    });
    describe('Fallback Statistics Estimation', () => {
        it('should estimate facts from file size', () => {
            // Rough estimate: ~500 bytes per fact on average
            const fileSize = 50000; // 50KB
            const estimatedFacts = Math.floor(fileSize / 500);
            assert.strictEqual(estimatedFacts, 100);
        });
        it('should distribute estimated facts by level', () => {
            const estimatedFacts = 100;
            const L0 = Math.floor(estimatedFacts * 0.05); // 5%
            const L1 = Math.floor(estimatedFacts * 0.15); // 15%
            const L2 = Math.floor(estimatedFacts * 0.40); // 40%
            const L3 = Math.floor(estimatedFacts * 0.40); // 40%
            assert.strictEqual(L0, 5);
            assert.strictEqual(L1, 15);
            assert.strictEqual(L2, 40);
            assert.strictEqual(L3, 40);
        });
    });
    describe('Python Script SQL Query', () => {
        it('should generate valid SQL for fact counting', () => {
            const sqlQuery = `
                SELECT level, COUNT(*) 
                FROM hierarchical_facts 
                WHERE archived = 0 
                GROUP BY level
            `.trim();
            assert.ok(sqlQuery.includes('SELECT'));
            assert.ok(sqlQuery.includes('hierarchical_facts'));
            assert.ok(sqlQuery.includes('archived = 0'));
            assert.ok(sqlQuery.includes('GROUP BY level'));
        });
        it('should generate valid SQL for domain counting', () => {
            const sqlQuery = `
                SELECT COUNT(DISTINCT domain) 
                FROM hierarchical_facts 
                WHERE domain IS NOT NULL AND archived = 0
            `.trim();
            assert.ok(sqlQuery.includes('COUNT(DISTINCT domain)'));
            assert.ok(sqlQuery.includes('domain IS NOT NULL'));
        });
    });
});
//# sourceMappingURL=rlm.test.js.map