/**
 * Test script for KiroSpecReader
 */
const fs = require('fs');
const path = require('path');

// Simulate workspace folders
const workspaceFolders = ['C:\\AISecurity', 'C:\\AISecurity\\sentinel-community'];

function getKiroSpecsPaths() {
    const paths = [];
    for (const folder of workspaceFolders) {
        const specsPath = path.join(folder, '.kiro', 'specs');
        if (fs.existsSync(specsPath)) {
            paths.push({ root: folder, specsPath });
        }
    }
    return paths;
}

function readSpecStatus(name, specPath, workspaceRoot) {
    const hasRequirements = fs.existsSync(path.join(specPath, 'requirements.md'));
    const hasDesign = fs.existsSync(path.join(specPath, 'design.md'));
    const hasTasks = fs.existsSync(path.join(specPath, 'tasks.md'));

    let phase = 'requirements';
    if (hasRequirements && !hasDesign) {
        phase = 'design';
    } else if (hasDesign && !hasTasks) {
        phase = 'tasks';
    } else if (hasTasks) {
        phase = 'implementation';
    }

    let taskProgress;
    if (hasTasks) {
        const content = fs.readFileSync(path.join(specPath, 'tasks.md'), 'utf-8');
        const totalMatch = content.match(/\[[ xX\/]\]/g);
        const completedMatch = content.match(/\[[xX]\]/g);
        taskProgress = {
            total: totalMatch?.length || 0,
            completed: completedMatch?.length || 0
        };
        if (taskProgress.completed === taskProgress.total && taskProgress.total > 0) {
            phase = 'complete';
        }
    }

    return {
        name,
        workspaceRoot: path.basename(workspaceRoot),
        phase,
        hasRequirements,
        hasDesign,
        hasTasks,
        taskProgress
    };
}

// Main test
console.log('Testing KiroSpecReader...\n');

const kiroPaths = getKiroSpecsPaths();
console.log('Found .kiro/specs paths:', kiroPaths.length);
console.log(kiroPaths);
console.log('');

const allSpecs = [];
for (const { root, specsPath } of kiroPaths) {
    const entries = fs.readdirSync(specsPath, { withFileTypes: true });
    for (const entry of entries) {
        if (entry.isDirectory()) {
            const specPath = path.join(specsPath, entry.name);
            const status = readSpecStatus(entry.name, specPath, root);
            allSpecs.push(status);
        }
    }
}

console.log('Specs found:', allSpecs.length);
console.log(JSON.stringify(allSpecs, null, 2));
