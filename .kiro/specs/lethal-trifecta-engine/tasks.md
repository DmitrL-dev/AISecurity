# Tasks: Lethal Trifecta Engine

## Phase 1: TDD Setup
- [ ] 1.1 Создать test file `sentinel-core/tests/lethal_trifecta_test.rs`
- [ ] 1.2 Написать тесты для data_access patterns (AC-1.1-1.4)
- [ ] 1.3 Написать тесты для external_comm patterns (AC-3.1-3.5)
- [ ] 1.4 Написать тесты для trifecta scoring (AC-4.1-4.4)

## Phase 2: Rust Implementation
- [ ] 2.1 Создать `sentinel-core/src/engines/lethal_trifecta.rs`
- [ ] 2.2 Реализовать `TrifectaFactors` struct
- [ ] 2.3 Реализовать `LethalTrifectaEngine::new()` с patterns
- [ ] 2.4 Реализовать `analyze()` method
- [ ] 2.5 Добавить в `mod.rs`

## Phase 3: PyO3 Bindings
- [ ] 3.1 Добавить `#[pyclass]` и `#[pymethods]` атрибуты
- [ ] 3.2 Экспортировать в `bindings.rs`
- [ ] 3.3 Обновить `sentinel_core.pyi` stubs

## Phase 4: Brain Integration
- [ ] 4.1 Создать `src/brain/engines/lethal_trifecta.py` adapter
- [ ] 4.2 Добавить в `engines/__init__.py`
- [ ] 4.3 Добавить Python тесты

## Phase 5: Verification
- [ ] 5.1 `cargo test` — все Rust тесты проходят
- [ ] 5.2 `maturin develop` — build bindings
- [ ] 5.3 `pytest` — Python интеграция работает
- [ ] 5.4 Docker test — работает в контейнере
