# Compliance Mapping для AI систем

> **Уровень:** Продвинутый  
> **Время:** 45 минут  
> **Трек:** 07 — Governance  
> **Модуль:** 07.1 — Policies  
> **Версия:** 1.0

---

## Цели обучения

- [ ] Понять compliance frameworks для AI систем
- [ ] Реализовать маппинг policies → compliance controls
- [ ] Построить compliance reporting
- [ ] Интегрировать compliance tracking в SENTINEL

---

## 1. Обзор Compliance Frameworks

### 1.1 Основные фреймворки

```
┌────────────────────────────────────────────────────────────────────┐
│              AI COMPLIANCE ЛАНДШАФТ                                │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  EU AI Act                                                         │
│  ├── Risk-based классификация                                     │
│  ├── Требования прозрачности                                      │
│  └── Мандаты human oversight                                      │
│                                                                    │
│  NIST AI RMF                                                       │
│  ├── Govern, Map, Measure, Manage                                 │
│  ├── AI system risk assessment                                    │
│  └── Trustworthy AI характеристики                                │
│                                                                    │
│  ISO/IEC 42001                                                     │
│  ├── AI Management System                                         │
│  ├── Governance и accountability                                  │
│  └── Continuous improvement                                       │
│                                                                    │
│  Industry-Specific                                                 │
│  ├── HIPAA (Healthcare AI)                                        │
│  ├── SOC 2 (Cloud AI Services)                                    │
│  └── PCI-DSS (Financial AI)                                       │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 2. Compliance модель

### 2.1 Основные сущности

```rust
use chrono::{DateTime, Utc};

#[derive(Clone, Debug)]
enum Framework {
    EuAiAct,
    NistAiRmf,
    Iso42001,
    Hipaa,
    Soc2,
    PciDss,
    Custom,
}

#[derive(Clone, Debug, PartialEq)]
enum ControlStatus {
    NotImplemented,
    Partial,
    Implemented,
    NotApplicable,
}

#[derive(Clone, Debug)]
enum RiskLevel {
    Unacceptable, // EU AI Act: Prohibited
    High,
    Limited,
    Minimal,
}

/// Единичный compliance control
#[derive(Clone, Debug)]
struct ComplianceControl {
    control_id: String,
    framework: Framework,
    title: String,
    description: String,
    requirements: Vec<String>,

    // Статус
    status: ControlStatus,
    implementation_notes: String,

    // Доказательства
    evidence_links: Vec<String>,
    policy_mappings: Vec<String>,

    // Метаданные
    last_assessed: Option<DateTime<Utc>>,
    assessor: String,
}

/// Полный compliance framework
struct ComplianceFramework {
    framework_id: String,
    name: String,
    version: String,
    controls: Vec<ComplianceControl>,
}

impl ComplianceFramework {
    fn get_control(&self, control_id: &str) -> Option<&ComplianceControl> {
        self.controls.iter().find(|c| c.control_id == control_id)
    }

    fn get_compliance_score(&self) -> f64 {
        if self.controls.is_empty() {
            return 0.0;
        }

        let implemented = self.controls.iter()
            .filter(|c| c.status == ControlStatus::Implemented).count();
        let applicable = self.controls.iter()
            .filter(|c| c.status != ControlStatus::NotApplicable).count();

        if applicable > 0 { implemented as f64 / applicable as f64 } else { 0.0 }
    }
}
```

### 2.2 Определения фреймворков

```rust
/// Библиотека compliance frameworks
struct FrameworkLibrary;

impl FrameworkLibrary {
    /// EU AI Act compliance framework
    fn get_eu_ai_act() -> ComplianceFramework {
        ComplianceFramework {
            framework_id: "eu_ai_act_2024".into(),
            name: "EU AI Act".into(),
            version: "2024".into(),
            controls: vec![
                ComplianceControl {
                    control_id: "EU-AI-1".into(),
                    framework: Framework::EuAiAct,
                    title: "Risk Classification".into(),
                    description: "Классифицировать AI систему по уровню риска".into(),
                    requirements: vec![
                        "Выполнить оценку риска".into(),
                        "Документировать классификацию риска".into(),
                        "Периодически пересматривать классификацию".into(),
                    ],
                    status: ControlStatus::NotImplemented,
                    implementation_notes: String::new(),
                    evidence_links: vec![], policy_mappings: vec![],
                    last_assessed: None, assessor: String::new(),
                },
                ComplianceControl {
                    control_id: "EU-AI-2".into(),
                    framework: Framework::EuAiAct,
                    title: "Transparency".into(),
                    description: "Обеспечить прозрачность AI системы".into(),
                    requirements: vec![
                        "Информировать пользователей о взаимодействии с AI".into(),
                        "Предоставлять объяснения решений".into(),
                        "Документировать источники обучающих данных".into(),
                    ],
                    status: ControlStatus::NotImplemented,
                    implementation_notes: String::new(),
                    evidence_links: vec![], policy_mappings: vec![],
                    last_assessed: None, assessor: String::new(),
                },
                ComplianceControl {
                    control_id: "EU-AI-3".into(),
                    framework: Framework::EuAiAct,
                    title: "Human Oversight".into(),
                    description: "Реализовать механизмы human oversight".into(),
                    requirements: vec![
                        "Обеспечить человеческое вмешательство".into(),
                        "Предоставить возможности override".into(),
                        "Логировать действия oversight".into(),
                    ],
                    status: ControlStatus::NotImplemented,
                    implementation_notes: String::new(),
                    evidence_links: vec![], policy_mappings: vec![],
                    last_assessed: None, assessor: String::new(),
                },
                ComplianceControl {
                    control_id: "EU-AI-4".into(),
                    framework: Framework::EuAiAct,
                    title: "Data Governance".into(),
                    description: "Обеспечить надлежащее data governance".into(),
                    requirements: vec![
                        "Документировать источники данных".into(),
                        "Реализовать проверки качества данных".into(),
                        "Поддерживать data lineage".into(),
                    ],
                    status: ControlStatus::NotImplemented,
                    implementation_notes: String::new(),
                    evidence_links: vec![], policy_mappings: vec![],
                    last_assessed: None, assessor: String::new(),
                },
                ComplianceControl {
                    control_id: "EU-AI-5".into(),
                    framework: Framework::EuAiAct,
                    title: "Technical Documentation".into(),
                    description: "Поддерживать техническую документацию".into(),
                    requirements: vec![
                        "Документировать архитектуру системы".into(),
                        "Описать методологию обучения".into(),
                        "Записать процедуры тестирования".into(),
                    ],
                    status: ControlStatus::NotImplemented,
                    implementation_notes: String::new(),
                    evidence_links: vec![], policy_mappings: vec![],
                    last_assessed: None, assessor: String::new(),
                },
            ],
        }
    }

    /// NIST AI Risk Management Framework
    fn get_nist_ai_rmf() -> ComplianceFramework {
        ComplianceFramework {
            framework_id: "nist_ai_rmf_1_0".into(),
            name: "NIST AI RMF".into(),
            version: "1.0".into(),
            controls: vec![
                ComplianceControl {
                    control_id: "GOVERN-1".into(),
                    framework: Framework::NistAiRmf,
                    title: "Governance Structure".into(),
                    description: "Установить структуру AI governance".into(),
                    requirements: vec![
                        "Определить роли и обязанности".into(),
                        "Установить механизмы oversight".into(),
                        "Создать фреймворк accountability".into(),
                    ],
                    status: ControlStatus::NotImplemented,
                    implementation_notes: String::new(),
                    evidence_links: vec![], policy_mappings: vec![],
                    last_assessed: None, assessor: String::new(),
                },
                ComplianceControl {
                    control_id: "MAP-1".into(),
                    framework: Framework::NistAiRmf,
                    title: "Context Mapping".into(),
                    description: "Отобразить контекст и воздействия AI системы".into(),
                    requirements: vec![
                        "Идентифицировать stakeholders".into(),
                        "Документировать use cases".into(),
                        "Оценить потенциальные воздействия".into(),
                    ],
                    status: ControlStatus::NotImplemented,
                    implementation_notes: String::new(),
                    evidence_links: vec![], policy_mappings: vec![],
                    last_assessed: None, assessor: String::new(),
                },
                ComplianceControl {
                    control_id: "MEASURE-1".into(),
                    framework: Framework::NistAiRmf,
                    title: "Risk Measurement".into(),
                    description: "Измерять и отслеживать AI риски".into(),
                    requirements: vec![
                        "Определить метрики риска".into(),
                        "Реализовать мониторинг".into(),
                        "Отслеживать индикаторы риска".into(),
                    ],
                    status: ControlStatus::NotImplemented,
                    implementation_notes: String::new(),
                    evidence_links: vec![], policy_mappings: vec![],
                    last_assessed: None, assessor: String::new(),
                },
                ComplianceControl {
                    control_id: "MANAGE-1".into(),
                    framework: Framework::NistAiRmf,
                    title: "Risk Management".into(),
                    description: "Управлять идентифицированными рисками".into(),
                    requirements: vec![
                        "Приоритизировать риски".into(),
                        "Реализовать mitigations".into(),
                        "Пересматривать эффективность".into(),
                    ],
                    status: ControlStatus::NotImplemented,
                    implementation_notes: String::new(),
                    evidence_links: vec![], policy_mappings: vec![],
                    last_assessed: None, assessor: String::new(),
                },
            ],
        }
    }
}
```

---

## 3. Маппинг Policy-to-Control

### 3.1 Движок маппинга

```rust
use std::collections::HashMap;

/// Маппинг между policy и compliance control
#[derive(Clone, Debug)]
struct PolicyControlMapping {
    mapping_id: String,
    policy_id: String,
    control_id: String,
    framework: Framework,
    coverage: f64, // 0-1, насколько control покрыт
    notes: String,
}

/// Маппит policies на compliance controls
struct ComplianceMappingEngine {
    mappings: Vec<PolicyControlMapping>,
    frameworks: HashMap<String, ComplianceFramework>,
}

impl ComplianceMappingEngine {
    fn new() -> Self {
        Self {
            mappings: Vec::new(),
            frameworks: HashMap::new(),
        }
    }

    fn add_framework(&mut self, framework: ComplianceFramework) {
        self.frameworks.insert(framework.framework_id.clone(), framework);
    }

    fn add_mapping(&mut self, mapping: PolicyControlMapping) {
        self.mappings.push(mapping);
    }

    fn get_mappings_for_policy(&self, policy_id: &str) -> Vec<&PolicyControlMapping> {
        self.mappings.iter().filter(|m| m.policy_id == policy_id).collect()
    }

    fn get_mappings_for_control(&self, control_id: &str) -> Vec<&PolicyControlMapping> {
        self.mappings.iter().filter(|m| m.control_id == control_id).collect()
    }

    /// Рассчитать общее покрытие control из всех mapped policies
    fn calculate_control_coverage(&self, control_id: &str) -> f64 {
        let mappings = self.get_mappings_for_control(control_id);
        if mappings.is_empty() {
            return 0.0;
        }

        // Сумма coverage, ограничено 1.0
        let total: f64 = mappings.iter().map(|m| m.coverage).sum();
        total.min(1.0)
    }

    /// Получить coverage для всех controls в framework
    fn get_framework_coverage(&self, framework_id: &str) -> HashMap<String, f64> {
        let framework = match self.frameworks.get(framework_id) {
            Some(fw) => fw,
            None => return HashMap::new(),
        };

        framework.controls.iter().map(|c| {
            (c.control_id.clone(), self.calculate_control_coverage(&c.control_id))
        }).collect()
    }

    /// Найти controls с недостаточным coverage
    fn find_gaps(&self, framework_id: &str, threshold: f64) -> Vec<String> {
        let coverage = self.get_framework_coverage(framework_id);
        coverage.into_iter()
            .filter(|(_, cov)| *cov < threshold)
            .map(|(cid, _)| cid)
            .collect()
    }
}
```

### 3.2 Авто-маппинг

```rust
use std::collections::{HashMap, HashSet};

/// Автоматические предложения маппинга policy-to-control
struct AutoMapper {
    // Ключевые слова для каждой категории control
    control_keywords: HashMap<String, Vec<String>>,
}

impl AutoMapper {
    fn new() -> Self {
        let mut control_keywords = HashMap::new();
        control_keywords.insert("transparency".into(),
            vec!["log", "audit", "record", "document", "explain"]
                .into_iter().map(String::from).collect());
        control_keywords.insert("human_oversight".into(),
            vec!["approval", "review", "human", "override", "intervene"]
                .into_iter().map(String::from).collect());
        control_keywords.insert("data_governance".into(),
            vec!["data", "privacy", "retention", "quality", "source"]
                .into_iter().map(String::from).collect());
        control_keywords.insert("access_control".into(),
            vec!["permission", "role", "access", "authorize", "deny"]
                .into_iter().map(String::from).collect());
        control_keywords.insert("risk_management".into(),
            vec!["risk", "threat", "vulnerability", "mitigate", "assess"]
                .into_iter().map(String::from).collect());
        Self { control_keywords }
    }

    /// Предложить mappings на основе содержимого policy
    fn suggest_mappings(&self, policy: &Policy,
                        framework: &ComplianceFramework) -> Vec<PolicyControlMapping> {
        let mut suggestions = Vec::new();
        let policy_text = self.extract_policy_text(policy);

        for control in &framework.controls {
            let score = self.calculate_relevance(&policy_text, control);

            if score > 0.3 { // Порог для предложения
                suggestions.push(PolicyControlMapping {
                    mapping_id: format!("auto_{}_{}", policy.policy_id, control.control_id),
                    policy_id: policy.policy_id.clone(),
                    control_id: control.control_id.clone(),
                    framework: control.framework.clone(),
                    coverage: score,
                    notes: "Auto-suggested mapping".into(),
                });
            }
        }

        suggestions
    }

    /// Извлечь текст для поиска из policy
    fn extract_policy_text(&self, policy: &Policy) -> String {
        let mut parts = vec![policy.name.clone(), policy.description.clone()];
        for rule in &policy.rules {
            parts.push(rule.description.clone());
            parts.extend(rule.actions.clone());
        }
        parts.join(" ").to_lowercase()
    }

    /// Рассчитать score релевантности
    fn calculate_relevance(&self, policy_text: &str,
                           control: &ComplianceControl) -> f64 {
        let control_text = format!("{} {}", control.title, control.description).to_lowercase();

        // Простой keyword matching
        let policy_words: HashSet<&str> = policy_text.split_whitespace().collect();
        let control_words: HashSet<&str> = control_text.split_whitespace().collect();

        let common: HashSet<&&str> = policy_words.iter()
            .filter(|w| control_words.contains(**w)).collect();

        if control_words.is_empty() {
            return 0.0;
        }

        common.len() as f64 / control_words.len() as f64
    }
}
```

---

## 4. Compliance Reporting

### 4.1 Генератор отчётов

```rust
use chrono::{DateTime, Utc};
use std::collections::HashMap;

/// Отчёт о статусе compliance
struct ComplianceReport {
    framework_id: String,
    framework_name: String,
    generated_at: DateTime<Utc>,

    // Сводка
    total_controls: usize,
    implemented: usize,
    partial: usize,
    not_implemented: usize,
    not_applicable: usize,

    // Score
    compliance_score: f64,

    // Детали
    control_details: Vec<HashMap<String, serde_json::Value>>,
    gaps: Vec<String>,
    recommendations: Vec<String>,
}

/// Генерирует compliance отчёты
struct ComplianceReporter {
    engine: ComplianceMappingEngine,
}

impl ComplianceReporter {
    fn new(engine: ComplianceMappingEngine) -> Self {
        Self { engine }
    }

    /// Сгенерировать compliance отчёт для framework
    fn generate_report(&self, framework_id: &str) -> Result<ComplianceReport, String> {
        let framework = self.engine.frameworks.get(framework_id)
            .ok_or_else(|| format!("Framework {} not found", framework_id))?;

        // Подсчёт статусов
        let mut implemented = 0usize;
        let mut partial = 0usize;
        let mut not_implemented = 0usize;
        let mut not_applicable = 0usize;
        let mut control_details = Vec::new();

        for control in &framework.controls {
            match control.status {
                ControlStatus::Implemented => implemented += 1,
                ControlStatus::Partial => partial += 1,
                ControlStatus::NotImplemented => not_implemented += 1,
                ControlStatus::NotApplicable => not_applicable += 1,
            }

            let coverage = self.engine.calculate_control_coverage(&control.control_id);
            let mappings_count = self.engine.get_mappings_for_control(&control.control_id).len();

            let mut detail = HashMap::new();
            detail.insert("control_id".into(), json!(control.control_id));
            detail.insert("title".into(), json!(control.title));
            detail.insert("status".into(), json!(format!("{:?}", control.status)));
            detail.insert("coverage".into(), json!(coverage));
            detail.insert("mappings".into(), json!(mappings_count));
            control_details.push(detail);
        }

        // Найти gaps
        let gaps = self.engine.find_gaps(framework_id, 0.8);

        // Сгенерировать рекомендации
        let recommendations = self.generate_recommendations(framework, &gaps);

        Ok(ComplianceReport {
            framework_id: framework_id.into(),
            framework_name: framework.name.clone(),
            generated_at: Utc::now(),
            total_controls: framework.controls.len(),
            implemented,
            partial,
            not_implemented,
            not_applicable,
            compliance_score: framework.get_compliance_score(),
            control_details,
            gaps,
            recommendations,
        })
    }

    /// Сгенерировать рекомендации для gaps
    fn generate_recommendations(&self, framework: &ComplianceFramework,
                                gaps: &[String]) -> Vec<String> {
        let mut recommendations = Vec::new();

        for gap_id in gaps.iter().take(5) { // Топ 5 gaps
            if let Some(control) = framework.get_control(gap_id) {
                recommendations.push(format!(
                    "Реализовать policies покрывающие: {} - {}",
                    control.title, control.description
                ));
            }
        }

        recommendations
    }
}
```

---

## 5. Интеграция с SENTINEL

```rust
use std::collections::HashMap;

/// Конфигурация compliance engine
struct ComplianceConfig {
    enabled_frameworks: Vec<String>,
    auto_mapping: bool,
    gap_threshold: f64,
}

impl Default for ComplianceConfig {
    fn default() -> Self {
        Self {
            enabled_frameworks: vec!["eu_ai_act".into(), "nist_ai_rmf".into()],
            auto_mapping: true,
            gap_threshold: 0.8,
        }
    }
}

/// Compliance engine для SENTINEL
struct SENTINELComplianceEngine {
    config: ComplianceConfig,
    mapping_engine: ComplianceMappingEngine,
    reporter: ComplianceReporter,
    auto_mapper: AutoMapper,
}

impl SENTINELComplianceEngine {
    fn new(config: ComplianceConfig) -> Self {
        let mut mapping_engine = ComplianceMappingEngine::new();

        // Загрузить enabled frameworks
        if config.enabled_frameworks.contains(&"eu_ai_act".to_string()) {
            mapping_engine.add_framework(FrameworkLibrary::get_eu_ai_act());
        }
        if config.enabled_frameworks.contains(&"nist_ai_rmf".to_string()) {
            mapping_engine.add_framework(FrameworkLibrary::get_nist_ai_rmf());
        }

        let reporter = ComplianceReporter::new(mapping_engine.clone());
        let auto_mapper = AutoMapper::new();

        Self { config, mapping_engine, reporter, auto_mapper }
    }

    /// Замапить policy на compliance controls
    fn map_policy(&mut self, policy: &Policy, auto: Option<bool>) {
        let use_auto = auto.unwrap_or(self.config.auto_mapping);

        if use_auto {
            let frameworks: Vec<ComplianceFramework> = self.mapping_engine
                .frameworks.values().cloned().collect();
            for fw in &frameworks {
                let suggestions = self.auto_mapper.suggest_mappings(policy, fw);
                for mapping in suggestions {
                    self.mapping_engine.add_mapping(mapping);
                }
            }
        }
    }

    /// Вручную добавить mapping
    fn add_mapping(&mut self, policy_id: &str, control_id: &str,
                   framework: &str, coverage: f64) {
        let mapping = PolicyControlMapping {
            mapping_id: format!("manual_{}_{}", policy_id, control_id),
            policy_id: policy_id.into(),
            control_id: control_id.into(),
            framework: match framework {
                "eu_ai_act" => Framework::EuAiAct,
                "nist_ai_rmf" => Framework::NistAiRmf,
                "iso_42001" => Framework::Iso42001,
                _ => Framework::Custom,
            },
            coverage,
            notes: "Manual mapping".into(),
        };
        self.mapping_engine.add_mapping(mapping);
    }

    /// Сгенерировать compliance отчёт
    fn get_report(&self, framework_id: &str) -> Result<ComplianceReport, String> {
        self.reporter.generate_report(framework_id)
    }

    /// Получить compliance gaps
    fn get_gaps(&self, framework_id: &str) -> Vec<String> {
        self.mapping_engine.find_gaps(framework_id, self.config.gap_threshold)
    }

    /// Список всех frameworks со статусом
    fn get_all_frameworks(&self) -> Vec<HashMap<String, serde_json::Value>> {
        self.mapping_engine.frameworks.values().map(|fw| {
            let mut m = HashMap::new();
            m.insert("id".into(), json!(fw.framework_id));
            m.insert("name".into(), json!(fw.name));
            m.insert("controls".into(), json!(fw.controls.len()));
            m.insert("score".into(), json!(fw.get_compliance_score()));
            m
        }).collect()
    }
}
```

---

## 6. Итоги

| Компонент | Описание |
|-----------|----------|
| **Control** | Единица compliance requirement |
| **Framework** | Набор controls (EU AI Act, NIST) |
| **Mapping** | Связь Policy → control |
| **Coverage** | Степень покрытия control |
| **Report** | Отчёт о статусе compliance |

---

## Следующий урок

→ [Модуль 07.2: Audit Trail](../02-audit/README.md)

---

*AI Security Academy | Трек 07: Governance | Модуль 07.1: Policies*
