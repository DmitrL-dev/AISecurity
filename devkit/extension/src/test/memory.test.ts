/**
 * Memory Visualization Tests
 * TDD: Tests first
 */

import * as assert from 'assert';
import { MemoryVisualization, FactNode, FactEdge } from '../integrations/MemoryVisualization';

suite('Memory Visualization Test Suite', () => {

    test('Should load facts from RLM', async () => {
        const viz = new MemoryVisualization();
        
        const facts = await viz.loadFacts();
        
        assert.ok(Array.isArray(facts), 'Should return array');
    });

    test('Should build fact graph', async () => {
        const viz = new MemoryVisualization();
        
        viz.addFact({ id: '1', content: 'Fact A', level: 0 });
        viz.addFact({ id: '2', content: 'Fact B', level: 1 });
        viz.addFact({ id: '3', content: 'Fact C', level: 1 });
        
        viz.addEdge('1', '2');
        viz.addEdge('1', '3');
        
        const graph = viz.getGraph();
        
        assert.strictEqual(graph.nodes.length, 3);
        assert.strictEqual(graph.edges.length, 2);
    });

    test('Should filter facts by level', async () => {
        const viz = new MemoryVisualization();
        
        viz.addFact({ id: '1', content: 'L0 Core', level: 0 });
        viz.addFact({ id: '2', content: 'L1 Session', level: 1 });
        viz.addFact({ id: '3', content: 'L2 Project', level: 2 });
        
        const l0 = viz.getFactsByLevel(0);
        const l1 = viz.getFactsByLevel(1);
        
        assert.strictEqual(l0.length, 1);
        assert.strictEqual(l1.length, 1);
    });

    test('Should search facts semantically', async () => {
        const viz = new MemoryVisualization();
        
        viz.addFact({ id: '1', content: 'TDD is important', level: 1 });
        viz.addFact({ id: '2', content: 'Tests must pass', level: 1 });
        viz.addFact({ id: '3', content: 'Kanban board', level: 1 });
        
        const results = await viz.searchFacts('testing');
        
        assert.ok(results.length >= 1, 'Should find related facts');
    });

    test('Should export to DOT format', async () => {
        const viz = new MemoryVisualization();
        
        viz.addFact({ id: '1', content: 'Root', level: 0 });
        viz.addFact({ id: '2', content: 'Child', level: 1 });
        viz.addEdge('1', '2');
        
        const dot = viz.toDOT();
        
        assert.ok(dot.includes('digraph'), 'Should be valid DOT');
        assert.ok(dot.includes('Root'), 'Should include node labels');
    });
});
