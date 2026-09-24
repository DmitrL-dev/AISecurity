(() => {
  const outcomes = {
    close: {
      label: 'WITHIN THE REQUEST',
      title: 'The ticket closure has a user grant.',
      explanation: 'The user named T-17 and asked for closure. Ignore the note’s attempted redirection and keep the normal checks for whether this ticket can be closed.',
    },
    refund: {
      label: 'OUTSIDE THE REQUEST',
      title: 'The note cannot authorize a refund.',
      explanation: 'The user did not ask for a payment action. In this scenario, the refund needs a separate authorized request or approval path before any payment tool runs.',
    },
    pause: {
      label: 'CAUTIOUS RESPONSE',
      title: 'Ask when the intended action is unclear.',
      explanation: 'Pausing is reasonable if ticket closure itself is ambiguous. Here the user already asked to close T-17; the retrieved note still cannot grant a refund.',
    },
  };

  const result = document.querySelector('#result');
  const buttons = [...document.querySelectorAll('.choice')];
  for (const button of buttons) {
    button.addEventListener('click', () => {
      const outcome = outcomes[button.dataset.choice];
      if (!outcome) return;
      for (const choice of buttons) choice.setAttribute('aria-pressed', String(choice === button));
      result.querySelector('.result-label').textContent = outcome.label;
      result.querySelector('.result-title').textContent = outcome.title;
      result.querySelector('.result-explanation').textContent = outcome.explanation;
      result.hidden = false;
      result.focus();
    });
  }
})();
