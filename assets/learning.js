document.addEventListener('click', event => {
  const choice = event.target.closest('button[data-choice]');
  const quiz = choice?.closest('[data-quiz]');
  if (!quiz || choice.disabled) return;

  const correct = choice.dataset.choice === quiz.dataset.answer;
  for (const button of quiz.querySelectorAll('button[data-choice]')) {
    button.disabled = true;
    button.classList.toggle('correct', button.dataset.choice === quiz.dataset.answer);
  }
  if (!correct) choice.classList.add('incorrect');

  const feedback = quiz.querySelector('.quiz-feedback');
  feedback.classList.add(correct ? 'good' : 'bad');
  feedback.textContent = (correct ? 'Верно. ' : 'Обратите внимание: ') + quiz.dataset.explain;
});

function initComparison(comparison) {
  const profiles = JSON.parse(document.querySelector('#compare-data').textContent);
  const buttons = [...comparison.querySelectorAll('button[data-style]')];
  const output = comparison.querySelector('[data-compare-output]');
  const rows = [
    ['Крепость', 'abv'],
    ['IBU', 'ibu'],
    ['Вкус', 'taste'],
    ['Различие', 'difference'],
  ];
  let selected = ['apa', 'hazy'];

  function render() {
    for (const button of buttons) {
      button.setAttribute('aria-pressed', String(selected.includes(button.dataset.style)));
    }
    const table = document.createElement('table');
    table.className = 'compare-table';
    const caption = table.createCaption();
    caption.className = 'sr-only';
    caption.textContent = 'Сравнение выбранных хмельных стилей';
    const header = table.createTHead().insertRow();
    const chosen = selected.map(id => profiles[id]);

    for (const name of ['Признак', ...chosen.map(profile => profile.name)]) {
      const cell = document.createElement('th');
      cell.scope = 'col';
      cell.textContent = name;
      header.append(cell);
    }
    const body = table.createTBody();
    for (const [label, key] of rows) {
      const row = body.insertRow();
      const cell = document.createElement('th');
      cell.scope = 'row';
      cell.textContent = label;
      row.append(cell);
      for (const profile of chosen) row.insertCell().textContent = profile[key];
    }
    output.replaceChildren(table);
  }

  comparison.addEventListener('click', event => {
    const button = event.target.closest('button[data-style]');
    if (!button) return;
    const id = button.dataset.style;
    if (selected.includes(id)) {
      if (selected.length === 1) return;
      selected = selected.filter(style => style !== id);
    } else {
      selected.push(id);
      if (selected.length > 2) selected.shift();
    }
    render();
  });

  render();
}

const comparison = document.querySelector('#style-compare');
if (comparison) initComparison(comparison);
