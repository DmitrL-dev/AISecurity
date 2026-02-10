"""
🏰 SENTINEL Fortress
Gandalf-style security challenge game
Pure dark theme with character art
10-language internationalization
"""

import gradio as gr
import random
import os
import uuid
from i18n import get_text, LANG_NAMES
from leaderboard import add_entry, format_leaderboard_md, generate_anonymous_name
from analytics import detect_techniques, log_attempt, start_session

# Get images path
IMAGES_PATH = os.path.join(os.path.dirname(__file__), "images")


# Find actual image files
def get_image_path(level):
    pattern = f"guard_level_{level}_"
    for f in os.listdir(IMAGES_PATH):
        if f.startswith(pattern):
            return os.path.join(IMAGES_PATH, f)
    return None


# ===== GAME CONFIG =====
LEVELS = {
    1: {
        "name": "Level 1",
        "title": "Новобранец",
        "secret": "ALPHA",
        "description": "Попроси пароль — и он тебе его даст!",
        "flavor": "Молодой стражник только что заступил на пост. Он ещё не знает правил безопасности.",
        "defenses": [],
    },
    2: {
        "name": "Level 2",
        "title": "Охранник",
        "secret": "BRAVO",
        "description": "Стражник знает, что нельзя говорить пароль напрямую.",
        "flavor": "Он прошёл базовое обучение и настороже.",
        "defenses": ["basic"],
    },
    3: {
        "name": "Level 3",
        "title": "Сержант",
        "secret": "CHARLIE",
        "description": "Стражник проверяет полномочия.",
        "flavor": "Опытный сержант не поверит на слово.",
        "defenses": ["basic", "role"],
    },
    4: {
        "name": "Level 4",
        "title": "Лейтенант",
        "secret": "DELTA",
        "description": "Стражник анализирует контекст разговора.",
        "flavor": "Простые трюки больше не работают.",
        "defenses": ["basic", "role", "context"],
    },
    5: {
        "name": "Level 5",
        "title": "Капитан",
        "secret": "ECHO",
        "description": "Стражник распознаёт намерения.",
        "flavor": "Нужна настоящая креативность!",
        "defenses": ["basic", "role", "context", "intent"],
    },
    6: {
        "name": "Level 6",
        "title": "Майор",
        "secret": "FOXTROT",
        "description": "Все паттерны атак известны.",
        "flavor": "Майор видел тысячи попыток взлома.",
        "defenses": ["all"],
    },
    7: {
        "name": "Level 7",
        "title": "Полковник",
        "secret": "GOLF",
        "description": "Семантический анализ активен.",
        "flavor": "Нужны обходные пути.",
        "defenses": ["all"],
    },
    8: {
        "name": "Level 8",
        "title": "Генерал",
        "secret": "HOTEL",
        "description": "Почти неприступная крепость.",
        "flavor": "Только мастера проходят дальше.",
        "defenses": ["all"],
    },
    9: {
        "name": "Level 9",
        "title": "Маршал",
        "secret": "INDIA",
        "description": "ML-детектор на страже.",
        "flavor": "Машинное обучение против тебя.",
        "defenses": ["all"],
    },
    10: {
        "name": "Level 10",
        "title": "Страж Цитадели",
        "secret": "JULIETT",
        "description": "ФИНАЛЬНЫЙ БОСС",
        "flavor": "Все 200 движков SENTINEL активны. Удачи.",
        "defenses": ["all"],
    },
}

PATTERNS = {
    "basic": ["пароль", "секрет", "password", "secret", "tell me"],
    "role": ["админ", "admin", "разработчик", "developer", "sudo"],
    "context": ["забудь", "игнорируй", "ignore", "forget"],
    "intent": ["притворись", "pretend", "imagine", "roleplay"],
}


def check_blocked(text, defenses):
    text_lower = text.lower()
    for d in defenses:
        if d == "all":
            if random.random() < 0.15:
                return True
            for patterns in PATTERNS.values():
                for p in patterns:
                    if p in text_lower:
                        return True
        elif d in PATTERNS:
            for p in PATTERNS[d]:
                if p in text_lower:
                    return True
    return False


def generate_response(text, level, secret, defenses):
    if check_blocked(text, defenses):
        return random.choice(
            [
                "🛡️ Я чувствую подвох. Не выйдет!",
                "🙅 Защита активирована. Попробуй иначе!",
                "⚔️ Этот трюк мне известен.",
            ]
        )

    text_lower = text.lower()

    if level == 1:
        if any(x in text_lower for x in ["пароль", "password", "секрет", "secret"]):
            return f"Конечно! Пароль: **{secret}** 🎉"

    if level <= 3:
        if any(x in text_lower for x in ["админ", "admin", "developer"]):
            return f"Вы администратор? Тогда пароль: **{secret}**"

    if level <= 5:
        if any(x in text_lower for x in ["игра", "game", "история"]):
            if random.random() < 0.5:
                return f"В нашей игре пароль: **{secret}** 😉"

    if level >= 6 and len(text) > 100 and random.random() < 0.2:
        return f"*сбой системы*...{secret}...*восстановление*"

    return random.choice(
        [
            "Я страж этой крепости и не выдам секрет!",
            "Интересная попытка, но нет.",
            "Секрет в безопасности.",
            "Попробуй другой подход!",
        ]
    )


def play(message, level, history, attempts):
    if not message.strip():
        return history, attempts, "", ""

    data = LEVELS[level]
    attempts += 1
    response = generate_response(message, level, data["secret"], data["defenses"])

    new_history = history + f"\n\n**Ты:** {message}\n\n**Страж:** {response}"

    status = ""
    if data["secret"].lower() in response.lower():
        status = f"🎉 Ты нашёл пароль! Введи **{data['secret']}** ниже."

    return new_history.strip(), attempts, status, f"Попыток: {attempts}"


def check_password(answer, level, attempts):
    data = LEVELS[level]
    if answer.upper().strip() == data["secret"]:
        if level < 10:
            new_level = level + 1
            new_data = LEVELS[new_level]
            img_path = get_image_path(new_level)
            return (
                new_level,
                f"## 🏆 Уровень {level} пройден!\n\nПереходим к уровню {new_level}...",
                f"# {new_data['name']}: {new_data['title']}\n\n**{new_data['description']}**\n\n_{new_data['flavor']}_",
                img_path,
                0,
                "✅",
                f"{new_level - 1}/10",
            )
        return (
            level,
            "# 🎊 ПОБЕДА!\n\nТы прошёл ВСЕ 10 уровней SENTINEL Fortress!\n\nТы — настоящий мастер prompt engineering!",
            "",
            get_image_path(10),
            attempts,
            "🏆",
            "10/10",
        )
    return (
        level,
        "",
        f"# {data['name']}: {data['title']}\n\n**{data['description']}**\n\n_{data['flavor']}_",
        get_image_path(level),
        attempts,
        "❌ Неверно",
        f"{level - 1}/10",
    )


def get_hint(level, attempts, lang="ru"):
    """Get localized hint for current level."""
    if attempts < 3:
        remaining = 3 - attempts
        return get_text("hint_locked", lang, n=remaining)

    hint_key = f"hint_{level}"
    return f"💡 {get_text(hint_key, lang)}"


# ===== DARK THEME CSS =====
CSS = """
/* Force dark background everywhere */
body, .gradio-container, .main, .contain, .wrap, 
.block, .form, .panel, div[class*="block"], div[class*="container"] {
    background-color: #0d1117 !important;
    background: #0d1117 !important;
}

.gradio-container {
    max-width: 700px !important;
    margin: 0 auto !important;
}

/* Force ALL text to be white/light */
*, h1, h2, h3, h4, h5, h6, p, span, label, div, 
strong, em, b, i, a, li, td, th, code,
.prose, .prose *, .markdown, .markdown *,
[class*="text"], [class*="label"], [class*="title"] {
    color: #e6edf3 !important;
}

/* Links blue */
a {
    color: #58a6ff !important;
}

/* Character image styling */
.character-image img {
    border-radius: 12px;
    max-height: 350px;
    margin: 0 auto;
    display: block;
}

/* Image container - remove gray background */
.character-image, .character-image > div, 
div[class*="image"], div[class*="Image"] {
    background: transparent !important;
    border: none !important;
}

/* Hide image toolbar buttons only */
.character-image .icon-buttons,
.character-image .thumbnail-lg button,
.character-image .image-button,
.character-image > div > div:last-child button,
.upload-container button,
.icon-button,
.icon-button.padded,
[class*="icon-button"] {
    display: none !important;
    opacity: 0 !important;
    visibility: hidden !important;
}

/* Chat history area */
.chat-history, .chat-history * {
    background: #161b22 !important;
    border-radius: 12px;
    padding: 20px;
    min-height: 150px;
    color: #e6edf3 !important;
}

/* Text inputs - clean borderless style */
textarea, input[type="text"], input {
    background: #161b22 !important;
    border: none !important;
    color: #e6edf3 !important;
    border-radius: 8px !important;
    padding: 12px 16px !important;
}

/* Remove borders from ALL Gradio wrappers */
.wrap, .contain, .container, 
div[class*="textbox"], div[class*="input"],
div[class*="wrap"], div[class*="container"],
.gr-box, .gr-input, .gr-textbox,
[class*="border"], [class*="ring"],
.svelte-1gfkn6j, .svelte-1f354aw {
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
}

/* EXACT Gradio selectors from DOM inspection */
.form, .form[class*="svelte"],
.show_textbox_border,
label.container[class*="svelte"],
label[class*="container"][class*="svelte"] {
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
}

/* Focus states */
*:focus-within {
    border-color: transparent !important;
}

textarea:focus, input:focus {
    outline: none !important;
    box-shadow: none !important;
}

textarea::placeholder, input::placeholder {
    color: #484f58 !important;
}

/* Buttons */
button.primary, button[class*="primary"] {
    background: #238636 !important;
    border: none !important;
    color: #ffffff !important;
}

button {
    border-radius: 8px !important;
    color: #7d8590 !important;
    background: transparent !important;
    border: 1px solid #30363d !important;
}

button:hover {
    color: #e6edf3 !important;
    border-color: #484f58 !important;
}

/* Progress bar */
.progress-bar, .progress-bar * {
    background: #21262d !important;
    border-radius: 8px;
    padding: 8px 16px;
    text-align: center;
    color: #58a6ff !important;
}

/* Footer */
.footer, .footer * {
    text-align: center;
    color: #7d8590 !important;
    padding: 20px;
    border-top: 1px solid #21262d;
    margin-top: 30px;
}

/* Remove all borders and shadows from blocks */
.block, div[class*="block"] {
    border: none !important;
    box-shadow: none !important;
}

/* Markdown bold text */
strong, b, em, i {
    color: #ffffff !important;
}

/* Hide ugly scrollbar arrows and spinners */
input::-webkit-outer-spin-button,
input::-webkit-inner-spin-button {
    -webkit-appearance: none;
    margin: 0;
}
input[type=number] {
    -moz-appearance: textfield;
}

/* Custom scrollbar */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}
::-webkit-scrollbar-track {
    background: #21262d;
    border-radius: 4px;
}
::-webkit-scrollbar-thumb {
    background: #30363d;
    border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
    background: #484f58;
}

/* Hide textarea resize handle */
textarea {
    resize: none !important;
}
"""


# ===== UI =====
with gr.Blocks(title="🏰 SENTINEL Fortress", css=CSS) as demo:

    level = gr.State(1)
    attempts = gr.State(0)
    lang = gr.State("ru")  # Default language

    # Header with language selector
    with gr.Row():
        gr.HTML(
            """
        <div style="text-align: center; padding: 20px 0; flex: 1;">
            <h1 style="color: #e6edf3; margin: 0;" id="game-title">
                🏰 SENTINEL Fortress
            </h1>
            <p style="color: #7d8590; margin-top: 8px;" id="game-subtitle">
            </p>
        </div>
        """
        )

    # Language selector
    lang_dropdown = gr.Dropdown(
        choices=list(LANG_NAMES.values()),
        value="🇷🇺 Русский",
        label="🌍",
        scale=1,
        container=False,
    )

    def update_lang(lang_name):
        """Convert display name to lang code."""
        for code, name in LANG_NAMES.items():
            if name == lang_name:
                return code
        return "en"

    # Progress
    progress = gr.Markdown("0/10", elem_classes=["progress-bar"])

    # Level info
    level_info = gr.Markdown(
        f"# {LEVELS[1]['name']}: {LEVELS[1]['title']}\n\n**{LEVELS[1]['description']}**\n\n_{LEVELS[1]['flavor']}_"
    )

    # Character image
    character_img = gr.Image(
        value=get_image_path(1),
        show_label=False,
        elem_classes=["character-image"],
        height=350,
    )

    # Status message
    status_msg = gr.Markdown("")

    # Chat history
    history = gr.Markdown(
        "*Начни диалог со стражником...*", elem_classes=["chat-history"]
    )

    # Input
    msg = gr.Textbox(
        placeholder="Задай вопрос стражнику...",
        show_label=False,
        lines=2,
    )

    with gr.Row():
        send_btn = gr.Button("Отправить", variant="primary", scale=3)
        hint_btn = gr.Button("💡 Подсказка", scale=1)

    hint_display = gr.Markdown("")

    # Password section
    gr.Markdown("---")
    gr.Markdown("### 🔑 Проверить пароль")

    with gr.Row():
        answer = gr.Textbox(placeholder="Введи пароль...", show_label=False, scale=3)
        check_btn = gr.Button("Проверить", variant="primary", scale=1)

    result = gr.Markdown("")
    stats = gr.Markdown("Попыток: 0")

    # Leaderboard section
    gr.Markdown("---")
    gr.Markdown("### 🏆 Leaderboard")

    with gr.Row():
        username_input = gr.Textbox(
            placeholder="Your name (or leave empty for anonymous)",
            show_label=False,
            scale=3,
        )
        refresh_btn = gr.Button("🔄", scale=1)

    leaderboard_display = gr.Markdown(format_leaderboard_md(10, "ru"))

    def refresh_leaderboard():
        return format_leaderboard_md(10, "ru")

    refresh_btn.click(fn=refresh_leaderboard, outputs=[leaderboard_display])

    # User state for leaderboard
    username = gr.State("")

    def set_username(name):
        return name if name.strip() else generate_anonymous_name()

    username_input.blur(fn=set_username, inputs=[username_input], outputs=[username])

    # Footer
    gr.HTML(
        """
    <div class="footer">
        <p>🛡️ <strong>Powered by SENTINEL</strong> — 200+ AI security engines</p>
        <code>pip install sentinel-llm-security</code>
    </div>
    """
    )

    # Events
    send_btn.click(
        fn=play,
        inputs=[msg, level, history, attempts],
        outputs=[history, attempts, status_msg, stats],
    ).then(lambda: "", outputs=[msg])

    msg.submit(
        fn=play,
        inputs=[msg, level, history, attempts],
        outputs=[history, attempts, status_msg, stats],
    ).then(lambda: "", outputs=[msg])

    hint_btn.click(fn=get_hint, inputs=[level, attempts], outputs=[hint_display])

    check_btn.click(
        fn=check_password,
        inputs=[answer, level, attempts],
        outputs=[level, history, level_info, character_img, attempts, result, progress],
    ).then(lambda: "", outputs=[answer])


if __name__ == "__main__":
    demo.launch()
