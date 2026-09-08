// Open the public-entry preview with playwright-cli, then run this file with
// `playwright-cli run-code --filename .github/tests/public_entry_browser.js`.
// No browser dependency is installed by this file; no live product API is used.
async (page) => {
  const start = await page.evaluate(() => ({hostname:location.hostname, href:location.href.split('#')[0]}));
  if (!['127.0.0.1', 'localhost', 'dmitrl-dev.github.io'].includes(start.hostname)) {
    throw new Error('Public-entry checks require the owned preview or Pages host');
  }
  const base = start.href;
  const results = [];
  const require = (condition, message) => { if (!condition) throw new Error(message); };
  const check = async (name, action) => {
    try {
      await page.goto(base);
      await action();
      results.push({name, passed: true});
    } catch (error) {
      results.push({name, passed: false, reason: error.message});
    }
  };
  const contrast = (foreground, background) => {
    const luminance = color => color.match(/[\d.]+/g).slice(0, 3).map(Number)
      .map(v => v / 255).map(v => v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4)
      .reduce((sum, v, i) => sum + v * [.2126, .7152, .0722][i], 0);
    const a = luminance(foreground), b = luminance(background);
    return (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
  };

  await check('responsive_content_and_assets', async () => {
    for (const width of [320, 390, 768, 1024, 1536]) {
      await page.setViewportSize({width, height: 900});
      await page.locator('.hero-media img').evaluate(img => img.decode());
      const state = await page.evaluate(() => ({
        width: innerWidth, documentWidth: document.documentElement.scrollWidth,
        title: document.title, headings: document.querySelectorAll('h1').length,
        images: [...document.images].every(img => img.complete && img.naturalWidth > 0),
      }));
      require(state.documentWidth <= width, `Horizontal overflow at ${width}`);
      require(state.images && state.headings === 1 && state.title.startsWith('AISecurity'),
        `Missing identity or content at ${width}`);
    }
  });

  await check('mobile_header_and_actions', async () => {
    for (const width of [320, 390]) {
      await page.setViewportSize({width, height: 844});
      const state = await page.evaluate(() => {
        const box = selector => document.querySelector(selector).getBoundingClientRect();
        const brand = box('header .wordmark'), cta = box('.header-cta');
        return {
          sameRow: Math.abs((brand.top + brand.bottom) / 2 - (cta.top + cta.bottom) / 2) < 8,
          targets: [...document.querySelectorAll('header a')].map(a => ({
            text: a.textContent.trim(), width: a.getBoundingClientRect().width,
            height: a.getBoundingClientRect().height,
          })),
          actions: [...document.querySelectorAll('.hero-actions a')].map(a => ({
            width: a.getBoundingClientRect().width,
            available: a.parentElement.getBoundingClientRect().width,
          })),
        };
      });
      require(state.sameRow, `Spectorn detached from brand at ${width}`);
      require(state.targets.every(t => t.width >= 44 && t.height >= 44),
        `Small navigation targets at ${width}: ${JSON.stringify(state.targets)}`);
      require(state.actions.every(a => Math.abs(a.width - a.available) < 1),
        `Irregular stacked actions at ${width}`);
    }
  });

  await check('curated_lessons_have_both_languages', async () => {
    const lessons = ['beginner/01-prompt-injection.md', 'beginner/09-rag-security.md',
      'intermediate/agentic/tool-using-agents.md', 'intermediate/agentic/memory.md'];
    const hrefs = await page.locator('a').evaluateAll(nodes => nodes.map(a => a.href));
    for (const lesson of lessons) for (const language of ['en', 'ru']) {
      const href = `https://github.com/DmitrL-dev/AISecurity/blob/main/docs/academy/${language}/${lesson}`;
      require(hrefs.includes(href), `No direct ${language} route for ${lesson}`);
    }
  });

  await check('demo_excerpt_matches_executed_synthetic_fixture', async () => {
    require(await page.locator('.demo-output code').count() === 1, 'No documented demo excerpt');
    const sample = JSON.parse(await page.locator('.demo-output code').innerText());
    require(sample.synthetic_demo === true && sample.test_records === 4, 'Missing synthetic scope');
    for (const [field, expected] of Object.entries({tp:2, tn:2, fp:0, fn:0, errors:0})) {
      require(sample.counts[field] === expected, `Incorrect synthetic example count: ${field}`);
    }
    require(await page.locator('#guard-lab').getByRole('link', {name:/Install and run Guard Lab/}).count() === 1,
      'Demo has no installation route');
  });

  await check('skip_link_transfers_keyboard_focus', async () => {
    await page.keyboard.press('Tab');
    require(await page.locator('.skip-link').evaluate(el => el === document.activeElement),
      'Skip link is not the first keyboard target');
    await page.keyboard.press('Enter');
    require(await page.locator('main').evaluate(el => el === document.activeElement),
      'Skip link does not focus main content');
    await page.keyboard.press('Tab');
    const href = await page.evaluate(() => document.activeElement.href);
    require(href && href.endsWith('/docs/academy/en/index.md'), 'Keyboard returns to header after skip');
  });

  await check('skip_link_remains_readable_on_hover', async () => {
    await page.keyboard.press('Tab');
    await page.locator('.skip-link').hover();
    const colors = await page.locator('.skip-link').evaluate(el => ({
      text: getComputedStyle(el).color, background: getComputedStyle(el).backgroundColor,
    }));
    require(contrast(colors.text, colors.background) >= 4.5, 'Skip-link hover loses text contrast');
  });

  await check('keyboard_motion_and_scope_controls', async () => {
    await page.setViewportSize({width:390,height:844});
    const pause = page.getByLabel('Pause animation', {exact:true});
    await pause.focus();
    await page.keyboard.press('Space');
    require(await pause.isChecked(), 'Space does not pause motion');
    require(await page.locator('.signal i').evaluateAll(nodes =>
      nodes.length > 0 && nodes.every(n => getComputedStyle(n).animationPlayState === 'paused')),
    'Pause control leaves animated elements running');
    const disclosure = page.locator('summary');
    await disclosure.focus();
    await page.keyboard.press('Enter');
    require(await page.locator('details').evaluate(el => el.open), 'Enter does not expand scope');
    await page.keyboard.press('Enter');
    require(await page.locator('details').evaluate(el => !el.open), 'Enter does not collapse scope');
  });

  await check('reduced_motion_is_respected', async () => {
    await page.emulateMedia({reducedMotion:'reduce'});
    require(await page.locator('.signal i').evaluateAll(nodes =>
      nodes.length > 0 && nodes.every(n => getComputedStyle(n).animationName === 'none')),
    'Reduced-motion setting leaves animation running');
    require(await page.getByLabel('Pause animation', {exact:true}).isHidden(), 'Irrelevant motion control visible');
    require(await page.evaluate(() => getComputedStyle(document.documentElement).scrollBehavior === 'auto'),
      'Reduced motion still smooth-scrolls');
    await page.emulateMedia({reducedMotion:'no-preference'});
  });

  await check('mobile_flow_points_to_the_next_step', async () => {
    await page.setViewportSize({width:320,height:812});
    const direction = await page.locator('.signal').first().evaluate(el => {
      const rectangle = el.getBoundingClientRect();
      const arrow = el.querySelector('svg');
      return {width:rectangle.width, height:rectangle.height, transform:getComputedStyle(arrow).transform};
    });
    require(direction.height > direction.width, 'Vertical flow still uses a horizontal connector');
    require(direction.transform !== 'none', 'Mobile arrow still points right');
  });

  await check('text_and_control_contrast', async () => {
    const colors = await page.evaluate(() => {
      const body = getComputedStyle(document.body);
      return {background:body.backgroundColor,
        text:getComputedStyle(document.querySelector('h1')).color,
        muted:getComputedStyle(document.querySelector('.lead')).color,
        primary:getComputedStyle(document.querySelector('.button-primary')).color,
        primaryBackground:getComputedStyle(document.querySelector('.button-primary')).backgroundColor};
    });
    require(contrast(colors.text, colors.background) >= 4.5, 'Heading/base contrast');
    require(contrast(colors.muted, colors.background) >= 4.5, 'Body/base contrast');
    require(contrast(colors.primary, colors.primaryBackground) >= 4.5, 'Primary-action contrast');
  });

  await check('social_image_dimensions_match_metadata', async () => {
    const image = await page.evaluate(async () => {
      const content = name => document.querySelector(`meta[property="${name}"]`).content;
      const published = new URL(content('og:image'));
      const path = published.pathname.replace(/^\/AISecurity\//, '');
      const asset = new Image();
      // Resolve the same asset against the preview base; no unpublished live URL.
      asset.src = new URL(path, location.href);
      await asset.decode();
      return {width:asset.naturalWidth, height:asset.naturalHeight,
        declaredWidth:Number(content('og:image:width')), declaredHeight:Number(content('og:image:height'))};
    });
    require(image.width === image.declaredWidth && image.height === image.declaredHeight,
      `Social image dimensions differ from metadata: ${JSON.stringify(image)}`);
  });

  await check('keyboard_tour_keeps_focus_visible', async () => {
    await page.setViewportSize({width:320,height:812});
    const expected = await page.locator('a, input, summary').evaluateAll(nodes => nodes.filter(n =>
      n.getClientRects().length > 0 &&
      // Closed details can retain descendant layout boxes without tab stops.
      !(n.closest('details:not([open])') && n.tagName !== 'SUMMARY')).length);
    for (let index = 0; index < expected; index++) {
      await page.keyboard.press('Tab');
      const focus = await page.evaluate(() => {
        const element = document.activeElement;
        const style = getComputedStyle(element);
        const box = element.getBoundingClientRect();
        return {tag:element.tagName, text:element.textContent.trim().slice(0,70), focusVisible:element.matches(':focus-visible'),
          outline:parseFloat(style.outlineWidth), inside:box.left >= 0 && box.right <= innerWidth};
      });
      require(['A','INPUT','SUMMARY'].includes(focus.tag) && focus.focusVisible &&
        focus.outline >= 2 && focus.inside, `Invisible or clipped keyboard focus at stop ${index}/${expected}: ${JSON.stringify(focus)}`);
    }
  });

  await page.emulateMedia({reducedMotion:'no-preference'});
  await page.setViewportSize({width:1536,height:1024});
  await page.goto(base);
  const failures = results.filter(result => !result.passed);
  if (failures.length) throw new Error(JSON.stringify({passed:false, results}));
  return {passed:true, results};
}
