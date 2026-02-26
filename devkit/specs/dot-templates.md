# DOT Flowchart Templates

> Исполняемые спецификации в формате DOT для Kiro design docs

## Назначение

DOT-диаграммы встраиваются в `design.md` как исполняемые спецификации. Они:
1. Визуализируют workflow для человека
2. Служат контрактом для реализации
3. Проверяются на Two-Stage Review

---

## Шаблон: Feature Workflow

```dot
digraph feature_workflow {
    rankdir=TB;
    node [shape=box, style=rounded];
    
    // States
    start [label="Trigger Event"];
    validate [label="Validate Input"];
    process [label="Process Logic"];
    success [label="✅ Success", style=filled, fillcolor=lightgreen];
    error [label="❌ Error", style=filled, fillcolor=salmon];
    
    // Transitions
    start -> validate;
    validate -> error [label="invalid"];
    validate -> process [label="valid"];
    process -> success;
    process -> error [label="exception"];
}
```

---

## Шаблон: Engine Detection Flow

```dot
digraph engine_detection {
    rankdir=LR;
    node [shape=box, style=rounded];
    
    input [label="Input Text"];
    preprocess [label="Preprocess\n(normalize, tokenize)"];
    detect [label="Detection Logic"];
    score [label="Calculate Score"];
    classify [label="Classify Categories"];
    result [label="EngineResult", style=filled, fillcolor=lightblue];
    
    input -> preprocess -> detect -> score -> classify -> result;
}
```

---

## Шаблон: QA Fix Loop

```dot
digraph qa_loop {
    rankdir=LR;
    node [shape=box, style=rounded];
    
    code [label="New Code"];
    review [label="Reviewer"];
    decision [shape=diamond, label="Issues?"];
    fix [label="Fixer"];
    done [label="✅ Merged", style=filled, fillcolor=lightgreen];
    escalate [label="⚠️ Escalate", style=filled, fillcolor=orange];
    
    code -> review;
    review -> decision;
    decision -> fix [label="Yes"];
    decision -> done [label="No"];
    fix -> review [label="iteration++"];
    fix -> escalate [label="iter > 3"];
}
```

---

## Шаблон: SDD Full Cycle

```dot
digraph sdd_cycle {
    rankdir=TB;
    node [shape=box, style=rounded];
    
    subgraph cluster_phase1 {
        label="Phase 1: Specification";
        style=dashed;
        req [label="Requirements"];
        design [label="Design"];
        tasks [label="Tasks"];
    }
    
    subgraph cluster_phase2 {
        label="Phase 2: Implementation";
        style=dashed;
        tdd [label="TDD\nRed→Green→Refactor"];
        review [label="Two-Stage Review"];
    }
    
    req -> design -> tasks;
    tasks -> tdd;
    tdd -> review;
    review -> merge [label="approved"];
    
    merge [label="✅ Merge", style=filled, fillcolor=lightgreen];
}
```

---

## Использование в Kiro Design

В `design.md` вставлять как:

````markdown
## Workflow Diagram

```dot
digraph my_feature {
    // ... DOT code
}
```
````

Two-Stage Review Stage 1 проверяет что реализация соответствует диаграмме.
