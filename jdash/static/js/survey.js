console.log("Loaded survey.js version 2026-09-10");

var question_types = {
  'Instruction for questions' : '0',
    'Single Choice' : '1',
    'Multiple Choice' : '2',
    'Sliding' : '3',
    'Free Text': '4',
    'Free Number' : '5',
    'Time':  '6',
    'Date':'7',
    'Time and Date': '8',
    'Duration': '9',
    'Location': '10',
    'Consent': '11'


}

var choiceQuestionTypes = ['1', '2'];
var slidingQuestionType = '3';

function initializeSurveyCommitLoadingForms() {
  document.querySelectorAll('form[data-survey-commit-form]').forEach(function (form) {
    form.addEventListener('submit', function (event) {
      if (form.dataset.submitting === 'true') {
        event.preventDefault();
        return;
      }

      form.dataset.submitting = 'true';
      if (typeof showJdashLoading === 'function') {
        showJdashLoading(
          form.getAttribute('data-loading-message') || 'Committing survey...'
        );
      }

      const submitter = event.submitter;
      window.setTimeout(function () {
        if (submitter) submitter.disabled = true;
      }, 0);
    });
  });
}

document.addEventListener('DOMContentLoaded', initializeSurveyCommitLoadingForms);

function initializeSurveyCommitChangeDetails() {
  const modal = document.getElementById('publishSurveyModal');
  if (!modal) return;

  const options = Array.from(modal.querySelectorAll('.publish-study-option'));

  function renderItems(container, items) {
    container.replaceChildren();
    const list = document.createElement('ul');
    list.className = 'mb-0 ps-3';
    items.forEach(function (item) {
      const listItem = document.createElement('li');
      listItem.textContent = item;
      list.appendChild(listItem);
    });
    container.appendChild(list);
  }

  async function loadChanges(option) {
    if (option.dataset.changesLoaded === 'true' || option.dataset.changesLoading === 'true') {
      return;
    }
    option.dataset.changesLoading = 'true';
    const container = option.querySelector('.publish-change-details');
    try {
      const response = await fetch(option.dataset.changeUrl, {
        headers: {'X-Requested-With': 'XMLHttpRequest'},
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.error || 'Unable to load pending changes.');
      }
      renderItems(container, payload.items || []);
      option.dataset.changesLoaded = 'true';
    } catch (error) {
      container.replaceChildren();
      const message = document.createElement('span');
      message.className = 'text-danger';
      message.textContent = error.message;
      container.appendChild(message);
      if (typeof window.showJdashMessage === 'function') {
        window.showJdashMessage(error.message, 'error');
      }
    } finally {
      option.dataset.changesLoading = 'false';
    }
  }

  options.forEach(function (option) {
    const toggle = option.querySelector('.publish-change-toggle');
    const details = option.querySelector('.publish-change-details');
    if (!toggle || !details) return;
    toggle.addEventListener('click', function () {
      const willOpen = details.classList.contains('d-none');
      details.classList.toggle('d-none', !willOpen);
      toggle.setAttribute('aria-expanded', String(willOpen));
      toggle.textContent = willOpen ? toggle.dataset.hideLabel : toggle.dataset.showLabel;
      if (willOpen) loadChanges(option);
    });
  });

  modal.addEventListener('shown.bs.modal', function () {
    options.forEach(loadChanges);
  });
}

document.addEventListener('DOMContentLoaded', initializeSurveyCommitChangeDetails);

function normalizeQuestionTypeValue(value) {
  return String(value === null || value === undefined ? '' : value);
}

function isChoiceQuestionType(value) {
  return choiceQuestionTypes.indexOf(normalizeQuestionTypeValue(value)) !== -1;
}

function isSlidingQuestionType(value) {
  return normalizeQuestionTypeValue(value) === slidingQuestionType;
}

///////////
///Survey details table
//////////////////
$(function() {
    initTable()

})
function initTable() {
    initializeQuestionDataTable()
    initializeSurveyListDataTable()

    if (typeof $.fn.bootstrapTable === 'function') {
      $('#survey_table').bootstrapTable({
        detailViewAlign : 'right',
        paginationParts: ['pageInfoshort', 'pageSize', 'pageList']
      })
      $('#cat_table').bootstrapTable({
        detailViewAlign : 'right',
        paginationParts: ['pageInfoshort', 'pageSize', 'pageList']
      })
      $('#survey_audit_table').bootstrapTable({
        paginationParts: ['pageInfoshort', 'pageSize', 'pageList']
      })
    }
  }

function getQuestionTableColumnIndex(tableElement, className) {
  return Array.from(tableElement.querySelectorAll('thead th')).findIndex(function (header) {
    return header.classList.contains(className);
  });
}

function initializeSurveyListDataTable() {
  var tableElement = document.getElementById('survey_table');
  if (!tableElement || !window.DataTable || tableElement.dataset.dataTableInitialized === 'true') {
    return;
  }

  var categoryColumn = getQuestionTableColumnIndex(tableElement, 'survey-category-column');
  var studyColumn = getQuestionTableColumnIndex(tableElement, 'survey-study-column');
  var createdColumn = getQuestionTableColumnIndex(tableElement, 'survey-created-column');
  var dataTable = new window.DataTable(tableElement, {
    autoWidth: false,
    columnDefs: [
      { targets: '.no-sort', orderable: false }
    ],
    layout: {
      topStart: null,
      topEnd: null,
      bottomStart: ['pageLength', 'info'],
      bottomEnd: 'paging'
    },
    order: createdColumn >= 0 ? [[createdColumn, 'desc']] : [],
    pageLength: 10,
    lengthMenu: [10, 30, 50, 100, { label: 'All', value: -1 }]
  });
  tableElement.dataset.dataTableInitialized = 'true';
  window.surveyListDataTable = dataTable;

  var searchInput = document.getElementById('survey-filter-search');
  var categorySelect = document.getElementById('survey-filter-category');
  var studySelect = document.getElementById('survey-filter-study');
  var clearButton = document.getElementById('survey-filter-clear');
  var countBadge = document.getElementById('survey-visible-count');

  function updateSurveyVisibleCount() {
    if (!countBadge) {
      return;
    }
    var info = dataTable.page.info();
    var total = Number(countBadge.dataset.total || info.recordsTotal);
    countBadge.textContent = info.recordsDisplay === total
      ? total + ' ' + (total === 1 ? 'survey' : 'surveys')
      : info.recordsDisplay + ' of ' + total + ' surveys';
  }

  dataTable.on('draw', updateSurveyVisibleCount);

  addQuestionFilterOptions(dataTable, categoryColumn, categorySelect);
  addQuestionFilterOptions(dataTable, studyColumn, studySelect);

  if (searchInput) {
    searchInput.addEventListener('input', function () {
      dataTable.search(searchInput.value).draw();
    });
  }

  function applyExactFilter(columnIndex, value) {
    if (columnIndex < 0) {
      return;
    }
    var pattern = value ? '^' + escapeQuestionFilterValue(value) + '$' : '';
    dataTable.column(columnIndex).search(pattern, true, false).draw();
  }

  if (categorySelect) {
    categorySelect.addEventListener('change', function () {
      applyExactFilter(categoryColumn, categorySelect.value);
    });
  }
  if (studySelect) {
    studySelect.addEventListener('change', function () {
      applyExactFilter(studyColumn, studySelect.value);
    });
  }
  if (clearButton) {
    clearButton.addEventListener('click', function () {
      if (searchInput) searchInput.value = '';
      if (categorySelect) categorySelect.value = '';
      if (studySelect) studySelect.value = '';
      dataTable.search('').columns().search('').draw();
    });
  }
  updateSurveyVisibleCount();
}

function addQuestionFilterOptions(dataTable, columnIndex, selectElement) {
  if (columnIndex < 0 || !selectElement) {
    return;
  }

  var values = [];
  dataTable.column(columnIndex).data().each(function (value) {
    var text = String(value === null || value === undefined ? '' : value).trim();
    if (text && values.indexOf(text) === -1) {
      values.push(text);
    }
  });

  values.sort(function (left, right) {
    return left.localeCompare(right, undefined, { sensitivity: 'base' });
  });
  values.forEach(function (value) {
    var option = document.createElement('option');
    option.value = value;
    option.textContent = value;
    selectElement.appendChild(option);
  });
}

function escapeQuestionFilterValue(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function initializeQuestionDataTable() {
  var tableElement = document.getElementById('quest_table') || document.getElementById('survey_quest_table');
  if (!tableElement || !window.DataTable || tableElement.dataset.dataTableInitialized === 'true') {
    return;
  }

  var typeColumn = getQuestionTableColumnIndex(tableElement, 'question-type-column');
  var categoryColumn = getQuestionTableColumnIndex(tableElement, 'question-category-column');
  var conditionColumn = getQuestionTableColumnIndex(tableElement, 'condition-column');
  var columnDefinitions = [
    { targets: '.dt-hidden', visible: false, searchable: false },
    { targets: '.no-sort', orderable: false },
    {
      targets: '.schedule-interval-column',
      render: function (data, type) {
        return type === 'display' ? scheduleIntervalFormatter(data) : data;
      }
    },
    {
      targets: '.schedule-window-column',
      render: function (data, type) {
        return type === 'display' ? scheduleTimeWindowsFormatter(data) : data;
      }
    },
    {
      targets: '.condition-column',
      render: function (data, type) {
        return type === 'display' ? conditionQuestionFormatter(data) : data;
      }
    },
    {
      targets: '.legacy-question-id-column',
      render: function (data, type, row, meta) {
        return type === 'display' ? legacyQuestionSortFormatter(data, row, meta.row) : data;
      }
    }
  ];

  var dataTable = new window.DataTable(tableElement, {
    autoWidth: false,
    columnDefs: columnDefinitions,
    layout: {
      topStart: null,
      topEnd: null,
      bottomStart: ['pageLength', 'info'],
      bottomEnd: 'paging'
    },
    order: [],
    pageLength: 10,
    lengthMenu: [10, 30, 50, 100, { label: 'All', value: -1 }]
  });
  tableElement.dataset.dataTableInitialized = 'true';
  if (tableElement.id === 'survey_quest_table') {
    window.editSurveyQuestionTable = dataTable;
  } else {
    window.createSurveyQuestionTable = dataTable;
  }

  if (tableElement.id === 'survey_quest_table') {
    tableElement.addEventListener('click', function (event) {
      var action = event.target.closest('.edit, .view');
      if (!action) {
        return;
      }

      var rowData = dataTable.row(action.closest('tr')).data();
      var legacyRow = {};
      Array.from(tableElement.querySelectorAll('thead th')).forEach(function (header, index) {
        var fieldName = header.dataset.field;
        if (fieldName) {
          legacyRow[fieldName] = rowData[index];
        }
      });
      window.operateEvents['click .edit'](event, null, legacyRow, null);
    });
  }

  var searchInput = document.getElementById('question-filter-search');
  var typeSelect = document.getElementById('question-filter-type');
  var categorySelect = document.getElementById('question-filter-category');
  var conditionSelect = document.getElementById('question-filter-condition');
  var clearButton = document.getElementById('question-filter-clear');
  var questionCountBadge = document.getElementById('question-visible-count');
  var conditionalCountBadge = document.getElementById('question-visible-conditional-count');
  var categoryCountBadge = document.getElementById('question-visible-category-count');

  function setQuestionSummaryBadge(element, count) {
    if (!element) {
      return;
    }
    var total = Number.parseInt(element.dataset.total, 10);
    if (Number.isNaN(total)) {
      total = count;
    }
    var label = total === 1 ? element.dataset.singular : element.dataset.plural;
    element.textContent = count + ' of ' + total + ' ' + label;
  }

  function plainQuestionCellValue(value) {
    var container = document.createElement('div');
    container.innerHTML = String(value === null || value === undefined ? '' : value);
    return container.textContent.trim();
  }

  function questionHasCondition(value) {
    return String(value === null || value === undefined ? '' : value)
      .split('||')
      .some(function (part) {
        var normalized = part.trim().toLowerCase();
        return normalized && normalized !== 'none' && normalized !== 'null' && normalized !== '[]';
      });
  }

  function updateQuestionFilterSummary() {
    var visibleRows = [];
    dataTable.rows({ search: 'applied' }).data().each(function (row) {
      visibleRows.push(row);
    });

    var visibleCategories = new Set();
    var visibleConditionalQuestions = 0;
    visibleRows.forEach(function (row) {
      if (categoryColumn >= 0) {
        var category = plainQuestionCellValue(row[categoryColumn]);
        if (category) {
          visibleCategories.add(category);
        }
      }
      if (conditionColumn >= 0 && questionHasCondition(row[conditionColumn])) {
        visibleConditionalQuestions += 1;
      }
    });

    setQuestionSummaryBadge(questionCountBadge, visibleRows.length);
    setQuestionSummaryBadge(conditionalCountBadge, visibleConditionalQuestions);
    setQuestionSummaryBadge(categoryCountBadge, visibleCategories.size);
  }

  dataTable.on('draw', updateQuestionFilterSummary);
  updateQuestionFilterSummary();

  addQuestionFilterOptions(dataTable, typeColumn, typeSelect);
  addQuestionFilterOptions(dataTable, categoryColumn, categorySelect);

  if (searchInput) {
    searchInput.addEventListener('input', function () {
      dataTable.search(searchInput.value).draw();
    });
  }

  function applyExactColumnFilter(columnIndex, value) {
    if (columnIndex < 0) {
      return;
    }
    var pattern = value ? '^' + escapeQuestionFilterValue(value) + '$' : '';
    dataTable.column(columnIndex).search(pattern, true, false).draw();
  }

  if (typeSelect) {
    typeSelect.addEventListener('change', function () {
      applyExactColumnFilter(typeColumn, typeSelect.value);
    });
  }
  if (categorySelect) {
    categorySelect.addEventListener('change', function () {
      applyExactColumnFilter(categoryColumn, categorySelect.value);
    });
  }
  if (conditionSelect && conditionColumn >= 0) {
    conditionSelect.addEventListener('change', function () {
      var pattern = '';
      if (conditionSelect.value === 'with') {
        pattern = '.+';
      } else if (conditionSelect.value === 'without') {
        pattern = '^$';
      }
      dataTable.column(conditionColumn).search(pattern, true, false).draw();
    });
  }
  if (clearButton) {
    clearButton.addEventListener('click', function () {
      if (searchInput) searchInput.value = '';
      if (typeSelect) typeSelect.value = '';
      if (categorySelect) categorySelect.value = '';
      if (conditionSelect) conditionSelect.value = '';
      dataTable.search('').columns().search('').draw();
    });
  }
}

function parseScheduleInteger(value) {
  if (value === null || value === undefined) {
    return null;
  }

  var parsed = Number.parseInt(String(value).trim(), 10);
  return Number.isNaN(parsed) ? null : parsed;
}

function parseScheduleTimeList(value) {
  if (value === null || value === undefined) {
    return [];
  }

  var raw = String(value).trim();
  if (!raw || raw === '[]' || raw.toLowerCase() === 'none' || raw.toLowerCase() === 'null') {
    return [];
  }

  try {
    var parsed = JSON.parse(raw.replace(/'/g, '"'));
    if (Array.isArray(parsed)) {
      return parsed.map(function (item) { return String(item).trim(); }).filter(Boolean);
    }
  } catch (error) {
    // Fall back to simple comma/semicolon parsing below.
  }

  return raw
    .replace(/^\[/, '')
    .replace(/\]$/, '')
    .split(/[;,]/)
    .map(function (item) { return item.replace(/["']/g, '').trim(); })
    .filter(Boolean);
}

function formatScheduleTime(value) {
  var trimmed = String(value || '').trim();
  if (!trimmed) {
    return '';
  }
  if (trimmed.indexOf(':') !== -1) {
    return trimmed;
  }

  var minutes = Number.parseInt(trimmed, 10);
  if (Number.isNaN(minutes)) {
    return trimmed;
  }

  minutes = ((minutes % 1440) + 1440) % 1440;
  var hours = Math.floor(minutes / 60);
  var mins = minutes % 60;
  return String(hours).padStart(2, '0') + ':' + String(mins).padStart(2, '0');
}

function formatScheduleFrequency(frequency) {
  var interval = parseScheduleInteger(frequency);
  if (interval === 1) {
    return 'Daily';
  }
  if (interval && interval > 1) {
    return 'Every ' + interval + ' days';
  }
  return 'Anytime';
}

function formatScheduleWindows(starts, ends) {
  if (starts.length === 0) {
    return '';
  }

  return starts.map(function (start, index) {
    var formattedStart = formatScheduleTime(start);
    var formattedEnd = formatScheduleTime(ends[index]);
    if (formattedEnd && formattedEnd !== formattedStart) {
      return formattedStart + '–' + formattedEnd;
    }
    return formattedStart;
  }).filter(Boolean).join(', ');
}

function formatNextDayScheduleLabel(nextDayToAnswer) {
  var nextDay = parseScheduleInteger(nextDayToAnswer);
  if (nextDay === null) {
    return '';
  }
  if (nextDay === 0) {
    return 'day of enrollment';
  }
  if (nextDay === 1) {
    return 'next day of enrollment';
  }
  return nextDay + ' days after enrollment';
}

function scheduleIntervalFormatter(value, row, index) {
  var parts = String(value || '').split('||');
  var scheduleParts = [
    formatNextDayScheduleLabel(parts[1] || ''),
    formatScheduleFrequency(parts[0] || '')
  ].filter(Boolean);

  return scheduleParts.length > 0 ? scheduleParts.join(' · ') : 'No schedule';
}

function scheduleTimeWindowsFormatter(value, row, index) {
  var parts = String(value || '').split('||');
  var starts = parseScheduleTimeList(parts[0] || '');
  var ends = parseScheduleTimeList(parts[1] || '');
  var windows = formatScheduleWindows(starts, ends);

  return windows || 'No time window';
}

function scheduleFormatter(value, row, index) {
  var parts = String(value || '').split('||');
  var frequency = parts[0] || '';
  var starts = parseScheduleTimeList(parts[1] || '');
  var ends = parseScheduleTimeList(parts[2] || '');
  var nextDayToAnswer = parts[3] || '';
  var scheduleParts = [
    formatScheduleFrequency(frequency),
    formatScheduleWindows(starts, ends),
    formatNextDayScheduleLabel(nextDayToAnswer)
  ].filter(Boolean);

  return scheduleParts.length > 0 ? scheduleParts.join(' · ') : 'No schedule';
}

function escapeHtml(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function parseConditionQuestionIds(value) {
  if (value === null || value === undefined) {
    return [];
  }

  var raw = String(value).trim();
  if (!raw || raw === '[]' || raw.toLowerCase() === 'none') {
    return [];
  }

  try {
    var parsed = JSON.parse(raw.replace(/'/g, '"'));
    if (Array.isArray(parsed)) {
      return parsed.map(function (item) { return String(item).trim(); }).filter(Boolean);
    }
  } catch (error) {
    // Fall back to simple comma/semicolon parsing below.
  }

  return raw
    .replace(/^\[/, '')
    .replace(/\]$/, '')
    .split(/[;,]/)
    .map(function (item) { return item.replace(/["']/g, '').trim(); })
    .filter(Boolean);
}

function formatConditionQuestionBadge(type, questionIds, answers) {
  if (questionIds.length === 0) {
    return '';
  }

  var label = type === 'activate' ? 'Activate' : 'Deactivate';
  var answerText = String(answers || '').trim();
  var title = answerText ? 'Answers: ' + answerText : 'No answer condition set';

  return '<span class="condition-question-badge ' + type + '" title="' + escapeHtml(title) + '">' +
    escapeHtml(label + ' Q(' + questionIds.join(', ') + ')') +
    '</span>';
}

function conditionQuestionFormatter(value, row, index) {
  var parts = String(value || '').split('||');
  var activateQuestionIds = parseConditionQuestionIds(parts[0] || '');
  var activationAnswers = parts[1] || '';
  var deactivateQuestionIds = parseConditionQuestionIds(parts[2] || '');
  var deactivationAnswers = parts[3] || '';
  var badges = [
    formatConditionQuestionBadge('activate', activateQuestionIds, activationAnswers),
    formatConditionQuestionBadge('deactivate', deactivateQuestionIds, deactivationAnswers)
  ].filter(Boolean);

  if (badges.length === 0) {
    return '';
  }

  return '<span class="condition-question-badges">' + badges.join('') + '</span>';
}

/*
 * edit_survey.html legacy question ordering.
 * Renders the arrow icon beside the file-based question id and wires the
 * shared sort modal with the current/new sequence values.
 */
function legacyQuestionSortFormatter(value, row, index) {
  var questionId = String(value || '').trim();
  var maxSortId = Number.parseInt(window.legacyQuestionCount || 0, 10);
  var currentSortId = Number.parseInt(questionId, 10);

  if (!window.legacyQuestionCanSort || !questionId) {
    return escapeHtml(questionId);
  }

  var iconClass = 'fas fa-arrows-alt-v';
  if (currentSortId === 1) {
    iconClass = 'fas fa-long-arrow-alt-down';
  } else if (currentSortId === maxSortId) {
    iconClass = 'fas fa-long-arrow-alt-up';
  }

  return '<div class="question-sort-cell">' +
    '<span>' + escapeHtml(questionId) + '</span>' +
    '<button class="btn btn-link btn-sm p-0" type="button" title="Change order" ' +
      'data-bs-toggle="modal" data-bs-target="#sortIdModal" ' +
      'data-question-id="' + escapeHtml(questionId) + '" ' +
      'data-current-sort-id="' + escapeHtml(questionId) + '" ' +
      'data-max-sort-id="' + escapeHtml(maxSortId) + '">' +
      '<i class="' + iconClass + '"></i>' +
    '</button>' +
  '</div>';
}

document.addEventListener('DOMContentLoaded', function () {
  var sortModal = document.getElementById('sortIdModal');
  if (!sortModal || sortModal.dataset.initialized === 'true') {
    return;
  }

  sortModal.dataset.initialized = 'true';
  sortModal.addEventListener('show.bs.modal', function (event) {
    var trigger = event.relatedTarget;
    if (!trigger) {
      return;
    }

    var questionId = trigger.getAttribute('data-question-id');
    var currentSortId = trigger.getAttribute('data-current-sort-id');
    var maxSortId = trigger.getAttribute('data-max-sort-id');

    var questionInput = document.getElementById('sort-question-id');
    var oldSortInput = document.getElementById('sort-old-id');
    var newSortInput = document.getElementById('sort-new-id');

    if (questionInput) {
      questionInput.value = questionId;
    }
    if (oldSortInput) {
      oldSortInput.value = currentSortId;
    }
    if (newSortInput) {
      newSortInput.value = currentSortId;
      newSortInput.max = maxSortId;
    }
  });

  sortModal.addEventListener('shown.bs.modal', function () {
    var newSortInput = document.getElementById('sort-new-id');
    if (newSortInput) {
      newSortInput.focus();
      newSortInput.select();
    }
  });
});

/*
 * edit_survey.html legacy question modal.
 * Bootstrap Table passes row values from #survey_quest_table; these helpers
 * normalize that row data into the simple two-column edit modal fields.
 */
function setLegacyModalField(selector, value) {
  var element = document.querySelector(selector);
  if (element) {
    element.value = value === null || value === undefined ? '' : value;
  }
}

function setLegacyModalCheckbox(selector, value, defaultValue) {
  var element = document.querySelector(selector);
  if (!element) {
    return;
  }

  var normalized = String(value === null || value === undefined ? '' : value).trim().toLowerCase();
  if (normalized === '') {
    element.checked = Boolean(defaultValue);
    return;
  }
  element.checked = ['1', 'true', 'yes', 'on'].indexOf(normalized) !== -1;
}

function getLegacyRowValue(row, fieldName, fallbackIndex) {
  if (row && !Array.isArray(row) && Object.prototype.hasOwnProperty.call(row, fieldName)) {
    return row[fieldName];
  }
  if (Array.isArray(row) && row.length > fallbackIndex) {
    return row[fallbackIndex];
  }
  return '';
}

window.operateEvents = {
    'click .edit': function (e, value, row, index) {
      var questionId = getLegacyRowValue(row, 'id', 0);
      var questionType = getLegacyRowValue(row, 'questionType', 3);
      $('#questionModalLabel').text("Edit Question Details" );
      $('#id_value').val(questionId);
      $('#sortId').val(questionId);
      $('#legacy-sortid-badge').text(questionId);
      $('#questionTitle').val(getLegacyRowValue(row, 'title', 1));
      $('#subText').val(getLegacyRowValue(row, 'subText', 2));
      $('#questionType').val(question_types[questionType] || questionType);
      $('#category').val(getLegacyRowValue(row, 'categoryValue', 5) || getLegacyRowValue(row, 'category', 4));
      $('#frequency').val(getLegacyRowValue(row, 'frequency', 8));
      $('#clockTime').val(getLegacyRowValue(row, 'clockTime', 9));
      $('#nextDayToAnswer').val(getLegacyRowValue(row, 'nextDayToAnswer', 10));
      $('#url').val(getLegacyRowValue(row, 'url', 12));
      $('#imageURL').val(getLegacyRowValue(row, 'imageURL', 11));
      $('#deactivateOnAnswer').val(getLegacyRowValue(row, 'deactivateOnAnswer', 14));
      $('#deactivateOnDate').val(getLegacyRowValue(row, 'deactivateOnDate', 13));
      setLegacyModalCheckbox('#active', getLegacyRowValue(row, 'active', 15), true);
      setLegacyModalCheckbox('#mandatory', getLegacyRowValue(row, 'mandatory', 16), false);
      setLegacyModalField(
        '#clockTime_start',
        parseScheduleTimeList(getLegacyRowValue(row, 'clockTimeStart', 17) || getLegacyRowValue(row, 'clockTime', 9)).join(', ')
      );
      setLegacyModalField('#clockTime_end', parseScheduleTimeList(getLegacyRowValue(row, 'clockTimeEnd', 18)).join(', '));
      setLegacyModalField('#activate_question', parseConditionQuestionIds(getLegacyRowValue(row, 'activateQuestion', 19)).join(', '));
      setLegacyModalField('#deactivate_question', parseConditionQuestionIds(getLegacyRowValue(row, 'deactivateQuestion', 20)).join(', '));
      setLegacyModalField('#activation_condition', getLegacyRowValue(row, 'activationCondition', 21));
      setLegacyModalField('#deactivation_condition', getLegacyRowValue(row, 'deactivationCondition', 22));
      $("#answerChoices").css("display", "none");
      $("#slidingAnswer").css("display", "none");
      $("#otherTypeAnswer").css("display", "none");
      $('#answerText').val('');
      $('#answerValue').val(getLegacyRowValue(row, 'answerValue', 26) || 0.1);
      $('#defaultValue').val(getLegacyRowValue(row, 'answerDefaultValue', 27) || 0.1);
      $('#stepSize').val(getLegacyRowValue(row, 'answerStepSize', 28) || 0.1);
      $('#minValue').val(getLegacyRowValue(row, 'answerMinValue', 29) || 0.1);
      $('#maxValue').val(getLegacyRowValue(row, 'answerMaxValue', 30) || 0.1);
      $('#minText').val(getLegacyRowValue(row, 'answerMinText', 31) || '');
      $('#maxText').val(getLegacyRowValue(row, 'answerMaxText', 32) || '');
      $('#answerSubText').val(getLegacyRowValue(row, 'answerSubText', 33) || '');
      $('#answerSortId').val(getLegacyRowValue(row, 'answerSortId', 34) || 1);
      if (isChoiceQuestionType($('#questionType').val())){
        $("#answerChoices").css("display", "block");
        $('#answerText').val(getLegacyRowValue(row, 'answerText', 25));
      }
        else if (isSlidingQuestionType($('#questionType').val())){
           $("#slidingAnswer").css("display", "block");
      }else{
        $("#otherTypeAnswer").css("display", "block");
        $('#answerText').css('display', 'none');
      }
      $('#activate_condition_div').css('display', 'block');
      $('#deactivate_condition_div').css('display', 'block');
      $('#activation_condition').css('display', '');
      $('#deactivation_condition').css('display', '');

    },
    'click .delete': function (e, value, row, index) {
      e.preventDefault();
      var questionId = getLegacyRowValue(row, 'id', 0);
      setDeleteQuestionIds([questionId]);
    }
  }


/*
 * edit_survey.html question deletion.
 * The selectors include #survey_quest_table for legacy file-backed surveys
 * and #quest_table for DB-backed surveys, so bulk delete can share one modal.
 */
var selectedQuestionIds = new Set();
var deleteQuestionSubmitting = false;

function ensureDeleteQuestionSubmitValue(form) {
  var existingInput = form.querySelector('input[type="hidden"][name="delete_question"]');

  if (existingInput) {
    existingInput.value = '1';
    return;
  }

  var input = document.createElement('input');
  input.type = 'hidden';
  input.name = 'delete_question';
  input.value = '1';
  form.appendChild(input);
}

function normalizeQuestionIds(questionIds) {
  return Array.from(new Set(
    questionIds
      .map(function (questionId) { return String(questionId || '').trim(); })
      .filter(function (questionId) { return questionId.length > 0; })
  ));
}

function setDeleteQuestionIds(questionIds) {
  var idsContainer = document.getElementById('delete-question-ids');
  var summary = document.getElementById('delete-question-summary');

  if (!idsContainer) {
    return;
  }

  idsContainer.innerHTML = '';
  var normalizedIds = normalizeQuestionIds(questionIds);

  normalizedIds.forEach(function (questionId) {
    var input = document.createElement('input');
    input.type = 'hidden';
    input.name = 'question_id';
    input.value = questionId;
    idsContainer.appendChild(input);
  });

  if (summary) {
    if (normalizedIds.length === 1) {
      summary.textContent = '1 question selected.';
    } else if (normalizedIds.length > 1) {
      summary.textContent = normalizedIds.length + ' questions selected.';
    } else {
      summary.textContent = '';
    }
  }
}

function getVisibleQuestionCheckboxes() {
  return Array.from(document.querySelectorAll('#quest_table .question-select, #survey_quest_table .question-select'));
}

function updateBulkQuestionDeleteControls() {
  var deleteButton = document.getElementById('bulk-delete-questions');
  var countLabel = document.getElementById('bulk-question-selected-count');
  var selectAll = document.getElementById('select-all-questions');
  var selectedCount = selectedQuestionIds.size;
  var visibleCheckboxes = getVisibleQuestionCheckboxes();

  if (deleteButton) {
    deleteButton.disabled = selectedCount === 0;
  }

  if (countLabel) {
    countLabel.textContent = selectedCount > 0 ? selectedCount + ' selected' : '';
  }

  if (selectAll) {
    var visibleCount = visibleCheckboxes.length;
    var selectedVisibleCount = visibleCheckboxes.filter(function (checkbox) {
      return selectedQuestionIds.has(checkbox.value);
    }).length;

    selectAll.checked = visibleCount > 0 && selectedVisibleCount === visibleCount;
    selectAll.indeterminate = selectedVisibleCount > 0 && selectedVisibleCount < visibleCount;
  }
}

function applySelectedQuestionState() {
  getVisibleQuestionCheckboxes().forEach(function (checkbox) {
    checkbox.checked = selectedQuestionIds.has(checkbox.value);
  });
  updateBulkQuestionDeleteControls();
}

function initializeQuestionBulkDelete() {
  var table = document.getElementById('quest_table') || document.getElementById('survey_quest_table');
  if (!table) {
    return;
  }

  table.addEventListener('change', function (event) {
    if (!event.target.classList.contains('question-select')) {
      return;
    }

    if (event.target.checked) {
      selectedQuestionIds.add(event.target.value);
    } else {
      selectedQuestionIds.delete(event.target.value);
    }
    updateBulkQuestionDeleteControls();
  });

  var selectAll = document.getElementById('select-all-questions');
  if (selectAll) {
    selectAll.addEventListener('change', function (event) {
      getVisibleQuestionCheckboxes().forEach(function (checkbox) {
        checkbox.checked = event.target.checked;
        if (event.target.checked) {
          selectedQuestionIds.add(checkbox.value);
        } else {
          selectedQuestionIds.delete(checkbox.value);
        }
      });
      updateBulkQuestionDeleteControls();
    });
  }

  var bulkDeleteButton = document.getElementById('bulk-delete-questions');
  if (bulkDeleteButton) {
    bulkDeleteButton.addEventListener('click', function (event) {
      if (selectedQuestionIds.size === 0) {
        event.preventDefault();
        return;
      }
      setDeleteQuestionIds(Array.from(selectedQuestionIds));
    });
  }

  $('#survey_quest_table, #quest_table').on('draw.dt', applySelectedQuestionState);
  applySelectedQuestionState();
}

function initializeQuestionDeleteLoading() {
  var deleteQuestionForm = document.getElementById('deleteQuestionForm');
  if (!deleteQuestionForm) {
    return;
  }

  deleteQuestionForm.addEventListener('submit', function (event) {
    if (deleteQuestionSubmitting) {
      return;
    }

    event.preventDefault();
    deleteQuestionSubmitting = true;
    ensureDeleteQuestionSubmitValue(deleteQuestionForm);
    if (typeof showJdashLoading === 'function') {
      showJdashLoading(
        deleteQuestionForm.getAttribute('data-loading-message') ||
        'Deleting selected questions and updating order...'
      );
    }

    window.setTimeout(function () {
      deleteQuestionForm.submit();
    }, 80);
  });
}

$(function() {
  initializeQuestionBulkDelete();
  initializeQuestionDeleteLoading();
});

  window.createOperateEvents = {
    'click .edit': function (e, value, row, index) {
    },
    'click .delete': function (e, value, row, index) {
      e.preventDefault();
      var questionId = e.currentTarget.getAttribute('data-question-id') || row[0];
      setDeleteQuestionIds([questionId]);
    }
  }


function prepareSurveyDeleteForm(trigger, row) {
  const deleteSurveyForm = document.getElementById('deleteSurveyForm');
  if (!deleteSurveyForm || !trigger) {
    return;
  }

  const defaultAction = deleteSurveyForm.getAttribute('data-default-action') || deleteSurveyForm.action;
  deleteSurveyForm.action = trigger.getAttribute('data-delete-url') || defaultAction;
  deleteSurveyForm.querySelectorAll('input[name="survey_id"]').forEach(function (input) {
    input.remove();
  });

  const surveyId = trigger.getAttribute('data-survey-id') || (row && row.survey_id);
  if (surveyId && surveyId !== 'file') {
    const input = document.createElement('input');
    input.type = 'hidden';
    input.name = 'survey_id';
    input.value = surveyId;
    deleteSurveyForm.appendChild(input);
  }
}

document.addEventListener('click', function (event) {
  const trigger = event.target.closest('#survey_table .delete');
  if (trigger) {
    prepareSurveyDeleteForm(trigger);
  }
});

window.survey_operateEvents = {
    'click .delete': function (e, value, row, index) {
      e.preventDefault();
      prepareSurveyDeleteForm(e.currentTarget, row);
    }
  }

function remove_survey(){
    const myModal = document.getElementById('deleteModal')
    const deleteSurveyForm = document.getElementById("deleteSurveyForm");
    deleteSurveyForm.submit();
}



function show_answer_form(){
    const questionType = document.getElementById('questionType');
    if (!questionType) {
      return;
    }

    const selectedValue = normalizeQuestionTypeValue(questionType.value);
    const isChoice = isChoiceQuestionType(selectedValue);
    const isSliding = isSlidingQuestionType(selectedValue);
    const answerForms = Array.from(document.querySelectorAll('.choice-formset'));
    const slidingRows = Array.from(document.querySelectorAll('[id^="slidingAnswer-"]'));
    const subTextRows = Array.from(document.querySelectorAll('[id="subTextDiv"]'));

    if (!isChoice && answerForms.length > 1) {
      for (let index = answerForms.length - 1; index >= 1; index--) {
        answerForms[index].remove();
        if (slidingRows[index]) {
          slidingRows[index].remove();
        }
        if (subTextRows[index]) {
          subTextRows[index].remove();
        }

        const answerIdInputs = document.querySelectorAll('input[name="answer_id"]');
        if (answerIdInputs[index]) {
          answerIdInputs[index].remove();
        }
      }

      const totalFormsInput = document.getElementById('id_form-TOTAL_FORMS');
      if (totalFormsInput) {
        totalFormsInput.value = '1';
      }
      renumberChoices();
    }

    const addChoiceButton = document.getElementById('add-choice');
    if (addChoiceButton) {
      addChoiceButton.style.display = isChoice ? 'block' : 'none';
    }

    document.querySelectorAll('.choice-formset').forEach((element) => {
      element.style.display = isChoice ? 'flex' : 'none';
    });

    document.querySelectorAll('[id^="slidingAnswer-"]').forEach((element) => {
      element.style.display = isSliding ? 'flex' : 'none';
    });

    document.querySelectorAll('#subTextDiv').forEach((element) => {
      element.style.display = 'none';
    });
  }
function initializeDefaultValueToggle() {
  const toggle = document.getElementById('flexSwitchCheckDefault');

  if (!toggle) return;

  const sortIdInput = document.querySelector('input[name="sortId"]');
  const currentSortId = Number.parseInt(sortIdInput?.value || '', 10);
  window.current_sort_id = Number.isNaN(currentSortId) ? 1 : currentSortId;

  const previousQuestionScript = document.getElementById('prev-question-data');
  if (previousQuestionScript) {
    try {
      window.previous_question_object = JSON.parse(previousQuestionScript.textContent || '{}');
    } catch (error) {
      console.warn('Unable to parse previous question data.', error);
      window.previous_question_object = {};
    }
  } else {
    window.previous_question_object = {};
  }

  if (window.current_sort_id === 1) {
    toggle.checked = true;
    toggle.disabled = true;
  }

  toggle.addEventListener('change', () => {
    //updateVisibility();
    set_default_values(toggle);
  });

  if (toggle.checked) {
    set_default_values(toggle);
  }
}

function serializeQuestionValue(value) {
  if (Array.isArray(value)) {
    return value.join(',');
  }
  if (value === null || value === undefined) {
    return '';
  }
  return value;
}

function set_default_values(default_switch){
  const isFirstQuestion = window.current_sort_id === 1;

  if (!default_switch.checked) {
    return;
  }

    // Apply values from previous question
    const previousQuestion = window.previous_question_object || {};
    if (Object.keys(previousQuestion).length > 0) {
      $('#activate_question').val(serializeQuestionValue(previousQuestion.activate_question));
      $('#deactivate_question').val(serializeQuestionValue(previousQuestion.deactivate_question));
      $('#activation_condition').val(previousQuestion.activation_condition ?? '');
      $('#deactivation_condition').val(previousQuestion.deactivation_condition ?? '');
      $('#imageURL').val(previousQuestion.imageURL ?? '');
      $('#url').val(previousQuestion.url ?? '');
    } else {
      console.warn("Previous question values are not available.");
    }

  toggleActivateConditionsField();
  toggleDeactivateConditionsField();
}

function makeAllEmptyValues(){
    $('#sortId').val('')
    $('#questionTitle').val('')
    $('#subText').val('')
    $('#questionType').val('')
    $('#flexSwitchCheckDefault').prop("checked", true);
    $('#category').val(1);
    $('#imageURL').val('' );
    $('#url').val('' );
    $('#nextDayToAnswer').val(1)
    $('#frequency').val(0)
    $('#clockTime_start').val('')
    $('#clockTime_end').val('')
    $('#deactivateOnAnswer').val('')
    $('#deactivateOnDate').val(0)
    $('#activate_question').val('')
    $('#deactivate_question').val('')
    $('#activation_condition').val('')
    $('#deactivation_condition').val('')
    $("#slidingAnswer").css("display", "none");
    $("#answerChoices").css("display", "none");
    $('#answerText').val('');
    $('#answerText').val('');
    $('#answerValue').val(0.1);
    $('#defaultValue').val(0.1 );
    $('#stepSize').val(0.1);
    $('#minValue').val(0.1);
    $('#maxValue').val(0.1);
    $('#minText').val('');
    $('#maxText').val('' );
    document.getElementsByName('add_question')[0].disabled = false;
    document.getElementsByName('update_question')[0].disabled = true;
}




///////// Questions /////

function addQuestionSubmitFlag(questionForm, name) {
  questionForm
    .querySelectorAll(`input[type="hidden"][data-submit-flag="${name}"]`)
    .forEach((input) => input.remove());

  var input = document.createElement('input');
  input.type = 'hidden';
  input.name = name;
  input.value = '1';
  input.dataset.submitFlag = name;
  questionForm.appendChild(input);
}

function submitQuestionFormOnce(questionForm, name) {
  if (!questionForm || questionForm.dataset.submitting === 'true') {
    return false;
  }

  questionForm.dataset.submitting = 'true';
  questionForm.setAttribute('aria-busy', 'true');
  addQuestionSubmitFlag(questionForm, name);

  document
    .querySelectorAll('#updateModal button, #questionForm button, #questionForm input[type="submit"]')
    .forEach((element) => {
      element.disabled = true;
    });

  return true;
}

function editQuestion(){
  if (!validateAnswerChoiceSeparators() || !validateConditionQuestionCategories()) {
    return;
  }

  const questionForm = document.getElementById("questionForm");
  if (!submitQuestionFormOnce(questionForm, 'update_question')) {
    return;
  }
  questionForm.submit();
}

function display_info(event){
  if (event && typeof event.preventDefault === 'function') {
    event.preventDefault();
  }
  if (validateNecessaryFields() && validateClockTimes() && validateAnswerChoiceSeparators() && validateConditionQuestionCategories()) {
    const updateModal = document.getElementById('updateModal');
    if (updateModal && window.bootstrap && window.bootstrap.Modal) {
      window.bootstrap.Modal.getOrCreateInstance(updateModal).show();
    }
  }

}

function validateNecessaryFields() {
  const qTitleEl = document.getElementById('questionTitle');
  const qsubTextEl = document.getElementById('subText');
  const qTypeEl = document.getElementById('questionType');
  const frequencyEl = document.getElementById('frequency');
  const deactivateOnDateEl = document.getElementById('deactivateOnDate');
  const nextDayToAnswerEl = document.getElementById('nextDayToAnswer');
  qTitleEl.setCustomValidity('');
  qsubTextEl.setCustomValidity('');
  qTypeEl.setCustomValidity('');
  if (frequencyEl) frequencyEl.setCustomValidity('');
  if (deactivateOnDateEl) deactivateOnDateEl.setCustomValidity('');
  if (nextDayToAnswerEl) nextDayToAnswerEl.setCustomValidity('');

   // 1) Require at least one of title or subtext
   if (qTitleEl.value.trim() === '' && qsubTextEl.value.trim() === '') {
    const msg = 'Please enter a title or a subtext.';
    qTitleEl.setCustomValidity(msg);
    qsubTextEl.setCustomValidity(msg);
    qTitleEl.reportValidity();
    return false;
  }

  // 2) Require a question type selection (assuming empty string is the default)
    else if (qTypeEl.value === '') {
    qTypeEl.setCustomValidity('Please select a question type.');
    qTypeEl.reportValidity();
    return false;
  } else if (frequencyEl && String(frequencyEl.value).trim() === '') {
    frequencyEl.setCustomValidity('Please enter a repetition interval');
    frequencyEl.reportValidity();
    return false;
  } else if (nextDayToAnswerEl && String(nextDayToAnswerEl.value).trim() === '') {
    nextDayToAnswerEl.setCustomValidity('Please enter the first day to answer ');
    nextDayToAnswerEl.reportValidity();
    return false;
  }else{

  // all good!
  return true;
  }
}

function validateClockTimes() {
  // 1) Get **elements**, not just their .value
  const startEl = document.getElementById('clockTime_start');
  const endEl   = document.getElementById('clockTime_end');
  startEl.setCustomValidity('');
  endEl.setCustomValidity('');
    const starts_raw = startEl.value.replace(/"/g, "");
    const end_raw = endEl.value.replace(/"/g, "");
  const starts = starts_raw.split(",");
  const ends   = end_raw.split(",");
  // 3) Check the arrays
  if (starts.length == 0) {
  //  startEl.setCustomValidity(`Please enter at least one start time.`);
  //  startEl.reportValidity();
    return true;
  }
  else if (starts.length > 1) {
    // 3a) Must have the same number of entries
    if (starts.length !== ends.length ) {
      endEl.setCustomValidity(
        `You have ${starts.length} start(s) but ${ends.length} end(s).`
      );
      endEl.reportValidity();
      return false;
    }

    // 3b) Each must be an integer, and end > start
    for (let i = 0; i < starts.length; i++) {
        const s = starts[i];
        const e = ends[i];
      // Check they really are integers
      if (!Number.isInteger(parseInt(s, 10))) {
        startEl.setCustomValidity(`Entry #${i+1} (“${s}”) is not an integer.`);
        startEl.reportValidity();
        return false;
      }
      if (!Number.isInteger(parseInt(e, 10))) {
        endEl.setCustomValidity(`Entry #${i+1} (“${e}”) is not an integer.`);
        endEl.reportValidity();
        return false;
      }

      // Check ordering
      if (e <= s) {
        endEl.setCustomValidity(
          `Entry #${i+1}: end time (${e}) must be greater than start time (${s}).`
        );
        endEl.reportValidity();
        return false;
      }
    }
  }else{
    // All good!  Let the form submit.
  return true;

  }

  return true;
}


function addQuestion(){
  if (!validateConditionQuestionCategories()) {
    return;
  }

  const questionForm = document.getElementById("questionForm");
  if (!submitQuestionFormOnce(questionForm, 'add_question')) {
    return;
  }

  const quest_table = $('#quest_table');
  var x = parseInt($('#sort_id').val(), 10) || 0;

  if (quest_table.length && typeof quest_table.bootstrapTable === 'function') {
    const tableData = quest_table.bootstrapTable('getData') || [];
    x = tableData.length;
    var rowCount = $('#quest_table tr').length;
    var row = document.createElement('tr');
    row.setAttribute('id',`tr-${rowCount -1}`);
    for (var c=0;c<= 7; c++){
      var column = document.createElement('td');
      column.innerHTML = "<span>"+ questionForm.elements['title'].value+ "</span>";
      row.append(column);
    }
    quest_table.append(row);
    $('#sort_id').val(x + 1);
  }

  questionForm.submit();

}

function getQuestionCategoryMap() {
  const script = document.getElementById('question-category-map');
  if (!script) {
    return {};
  }

  try {
    return JSON.parse(script.textContent || '{}');
  } catch (error) {
    console.warn('Unable to parse question category map.', error);
    return {};
  }
}

function getCurrentQuestionCategory() {
  const categoryField = document.getElementById('category');
  return String(categoryField ? categoryField.value : '').trim();
}

function getConditionQuestionValidationErrors(fieldId, label, questionCategoryMap, currentCategory) {
  const field = document.getElementById(fieldId);
  if (!field) {
    return { field: null, errors: [] };
  }

  field.setCustomValidity('');
  const errors = parseQuestionListValue(field.value).reduce((fieldErrors, questionNumber) => {
    const normalizedQuestionNumber = String(questionNumber).trim();
    const referencedCategory = questionCategoryMap[normalizedQuestionNumber];
    if (!referencedCategory) {
      fieldErrors.push(`${label}: question ${normalizedQuestionNumber} was not found.`);
    } else if (String(referencedCategory).trim() !== currentCategory) {
      fieldErrors.push(`${label}: question ${normalizedQuestionNumber} belongs to another category.`);
    }
    return fieldErrors;
  }, []);
  return { field, errors };
}

function validateConditionQuestionCategories() {
  const currentCategory = getCurrentQuestionCategory();
  if (!currentCategory) {
    return true;
  }

  const questionCategoryMap = getQuestionCategoryMap();
  const validationResults = [
    getConditionQuestionValidationErrors(
      'activate_question',
      'Activate question',
      questionCategoryMap,
      currentCategory
    ),
    getConditionQuestionValidationErrors(
      'deactivate_question',
      'Deactivate question',
      questionCategoryMap,
      currentCategory
    ),
  ];
  const invalidResult = validationResults.find((result) => result.errors.length > 0);

  if (!invalidResult) {
    return true;
  }

  invalidResult.field.setCustomValidity(
    `Activation/deactivation questions must belong to the selected category.\n\n${invalidResult.errors.join('\n')}`
  );
  invalidResult.field.reportValidity();
  return false;
}

function validateAnswerChoiceSeparators() {
  const answerInputs = Array.from(document.querySelectorAll('.choice-formset input[name$="-text"]'));
  const questionType = document.getElementById('questionType');
  if (!isChoiceQuestionType(questionType ? questionType.value : '')) {
    answerInputs.forEach((input) => input.setCustomValidity(''));
    return true;
  }

  const invalidInput = answerInputs.find((input) => /[,;]/.test(input.value || ''));

  answerInputs.forEach((input) => input.setCustomValidity(''));

  if (!invalidInput) {
    return true;
  }

  invalidInput.setCustomValidity('Answer choices cannot contain commas or semicolons.');
  invalidInput.reportValidity();
  return false;
}

function clearAnswerChoiceSeparatorValidity(input) {
  if (!input) {
    return;
  }
  input.setCustomValidity(/[,;]/.test(input.value || '')
    ? 'Answer choices cannot contain commas or semicolons.'
    : '');
}


function delete_quest(){
  const deleteQuestionForm = document.getElementById("deleteQuestionForm");
  deleteQuestionForm.submit();
}

function remove_question(){
  const removeQuestionForm = document.getElementById("removeQuestionForm");
  removeQuestionForm.submit();
}

///////// Answers /////

function addAnswer() {
  const answerForm = document.getElementById("answerForm");
  const addInput = document.getElementsByName('add_answer')[0];

  if (addInput && answerForm) {
    // Add the input to the form (if it’s not already in it)
    if (!answerForm.contains(addInput)) {
      answerForm.appendChild(addInput);
    }
    answerForm.submit();
  }
}

function renumberChoices() {
  const forms = document.querySelectorAll('.choice-formset');
  forms.forEach((formEl, index) => {
    // Update row ID
    formEl.id = `choice-form-${index}`;

    // Update form field names/ids inside this row
    formEl.querySelectorAll('input, textarea, select, label').forEach(el => {
      if (el.name) {
        el.name = el.name.replace(/form-\d+-/, `form-${index}-`);
      }
      if (el.id) {
        el.id = el.id.replace(/form-\d+-/, `form-${index}-`);
      }
      if (el.htmlFor) {
        el.htmlFor = el.htmlFor.replace(/form-\d+-/, `form-${index}-`);
      }
    });

    // Update remove button ID
    const removeBtn = formEl.querySelector('[id^="id_"][id$="_remove_btn"]');
    if (removeBtn) {
      removeBtn.id = `id_${index}_remove_btn`;
    }

    // Update visible order label (if used)
    const orderLabel = formEl.querySelector('.form-control-plaintext');
    if (orderLabel) {
      orderLabel.textContent = index + 1;
    }

    // Update hidden sort ID
    const sortInput = formEl.querySelector(`input[name$="-answerSortId"]`);
    if (sortInput) {
      sortInput.value = index + 1;
    }
  });
  refreshConditionOptionGroups();
}


///////// Categories /////

function renumber_category_forms() {
  const forms = document.querySelectorAll(".category-formset.mb-4");
  const totalForms = document.getElementById("id_form-TOTAL_FORMS");

  forms.forEach((formEl, index) => {
    formEl.id = `category-form-${index}`;

    formEl.querySelectorAll("input, textarea, select, label, span, a").forEach((el) => {
      if (el.name) {
        el.name = el.name.replace(/form-\d+-/g, `form-${index}-`);
      }
      if (el.id) {
        el.id = el.id.replace(/form-\d+-/g, `form-${index}-`);
      }
      if (el.htmlFor) {
        el.htmlFor = el.htmlFor.replace(/form-\d+-/g, `form-${index}-`);
      }
    });

    const titleField = formEl.querySelector(`[name="form-${index}-categoryTitle"]`);
    if (titleField) {
      titleField.id = `id_form-${index}-categoryTitle`;
    }

    const valueField = formEl.querySelector(`[name="form-${index}-categoryValue"]`);
    if (valueField) {
      valueField.id = `id_form-${index}-categoryValue`;
      valueField.value = index + 1;
      valueField.type = "hidden";
    }

    const displayValue = formEl.querySelector('[id^="display-value-"]');
    if (displayValue) {
      displayValue.id = `display-value-${index}`;
    }

    const removeBtn = formEl.querySelector('[id^="id_"][id$="_remove_btn"]');
    if (removeBtn) {
      removeBtn.id = `id_${index}_remove_btn`;
    }
  });

  if (totalForms) {
    totalForms.value = forms.length;
  }
}

function update_remove_buttons() {
  const forms = document.querySelectorAll(".category-formset.mb-4");
  forms.forEach((formEl, index) => {
    const removeBtn = formEl.querySelector('[id^="id_"][id$="_remove_btn"]');
    if (removeBtn) {
      removeBtn.disabled = forms.length <= 1;
      removeBtn.id = `id_${index}_remove_btn`;
    }
  });
}


function add_category_form() {
  const main = document.getElementById("category_details_form");
  const totalCategoryForms = document.getElementById("id_form-TOTAL_FORMS");

  const currentCategoryForms = document.getElementsByClassName("category-formset mb-4");
  const currentFormCount = currentCategoryForms.length;

  const categoryFormEl = document.getElementById('category-form-0').cloneNode(true);

  // Update formset metadata
  categoryFormEl.setAttribute('class', 'category-formset mb-4');
  categoryFormEl.setAttribute('id', `category-form-${currentFormCount}`);
  const regex = new RegExp('form-0-', 'g');
  categoryFormEl.innerHTML = categoryFormEl.innerHTML.replace(regex, `form-${currentFormCount}-`);
  categoryFormEl.innerHTML = categoryFormEl.innerHTML.replace('id_0_remove_btn', `id_${currentFormCount}_remove_btn`);

  totalCategoryForms.setAttribute('value', currentFormCount + 1);
  main.appendChild(categoryFormEl);

  // Clean up cloned input values
  document.getElementById(`id_form-${currentFormCount}-categoryTitle`).value = "";

  // ✅ HIDE and set `categoryValue` automatically
  const valueField = document.getElementById(`id_form-${currentFormCount}-categoryValue`);
  valueField.value = currentFormCount + 1;
  valueField.type = "hidden"; // Hide it from the user

  // ✅ Remove duplicated 'didSubjectAsk' (leave only the original one at top)
  const didSubjectAskField = document.getElementById(`id_form-${currentFormCount}-didSubjectAsk`);
  if (didSubjectAskField) {
    didSubjectAskField.closest('.form-check').remove(); // or .parentElement.remove() if needed
  }

  // Enable the remove button
  const removeBtn = document.getElementById(`id_${currentFormCount}_remove_btn`);
  if (removeBtn) {
    removeBtn.disabled = false;
  }

  renumber_category_forms();
  update_remove_buttons();
}

function remove_category_form(id) {
  const index = id.split("_")[1];
  const allForms = document.getElementsByClassName("category-formset mb-4");

  if (allForms.length <= 1) {
    // Only one form left — don't remove it, just clear its fields
    const titleField = document.getElementById(`id_form-${index}-categoryTitle`);
    const valueField = document.getElementById(`id_form-${index}-categoryValue`);
    const checkbox = document.getElementById(`id_form-${index}-didSubjectAsk`);

    if (titleField) titleField.value = "";
    if (valueField) valueField.value = "1";
    if (checkbox) checkbox.checked = false;

    if (typeof window.showJdashMessage === 'function') {
      window.showJdashMessage('At least one category is required.', 'warning');
    }
    return;
  }

  // Otherwise, safe to remove
  const main = document.getElementById("category_details_form");
  const categoryFormEl = document.getElementById("category-form-" + index);
  if (categoryFormEl) {
    main.removeChild(categoryFormEl);

    renumber_category_forms();
    update_remove_buttons();
  }
}

function add_choices_form() {
  // Get the container that holds all choice forms
  const container = document.getElementById("sortable-answer-list");
  const totalFormsInput = document.getElementById("id_form-TOTAL_FORMS");

  // Count current choice forms to determine the next index
  const currentFormCount = document.getElementsByClassName("choice-formset").length;

  // Use the first available form as a template
  const template = document.querySelector('.choice-formset');
  if (!template) {
    console.error("No template form found");
    return;
  }

  // Clone the template node deeply
  const newForm = template.cloneNode(true);
  newForm.setAttribute('id', `choice-form-${currentFormCount}`);

  // Replace all form index references (e.g., form-0- → form-3-)
  const regex = new RegExp(`form-(\\d+)-`, 'g');
  newForm.innerHTML = newForm.innerHTML.replace(regex, `form-${currentFormCount}-`);

  // Update the remove button ID as well
  newForm.innerHTML = newForm.innerHTML.replace(/id_\d+_remove_btn/, `id_${currentFormCount}_remove_btn`);

  // Append the new form to the container
  container.appendChild(newForm);

  // Update Django's management TOTAL_FORMS count
  totalFormsInput.value = currentFormCount + 1;

  // Reset specific fields inside the new form
  setTimeout(() => {
    const sortInput = newForm.querySelector(`[name="form-${currentFormCount}-answerSortId"]`);
    const textInput = newForm.querySelector(`[name="form-${currentFormCount}-text"]`);
    if (sortInput) sortInput.value = currentFormCount + 1;
    if (textInput) textInput.value = "";
  }, 0);

  // Enable the remove button on the new form
  setTimeout(() => {
    const removeBtn = newForm.querySelector(`#id_${currentFormCount}_remove_btn`);
    if (removeBtn) removeBtn.disabled = false;
  }, 0);

  // Re-index all choice forms (sort IDs, visible numbers, etc.)
  renumberChoices();
  refreshConditionOptionGroups();
}

function remove_choice_form(btnId) {
  // Extract form index from button ID (e.g., "id_2_remove_btn" → 2)
  const idx = parseInt(btnId.split('_')[1], 10);
  const row = document.getElementById(`choice-form-${idx}`);
  if (!row) return;

  // Remove the form row
  row.remove();

  // Remove the associated hidden input (answer_id)
  const allAnswerInputs = document.querySelectorAll('input[name="answer_id"]');
  if (allAnswerInputs.length > idx) {
    allAnswerInputs[idx].remove();
  }

  // Update TOTAL_FORMS
  const totalFormsInput = document.getElementById("id_form-TOTAL_FORMS");
  const newCount = document.querySelectorAll('.choice-formset').length;
  totalFormsInput.value = newCount;

  // Reindex all forms so Django can parse them
  renumberChoices();
  refreshConditionOptionGroups();
}

function parseQuestionListValue(rawValue) {
  const value = String(rawValue ?? '').trim();
  if (!value) {
    return [];
  }

  try {
    const parsed = JSON.parse(value);
    if (Array.isArray(parsed)) {
      return parsed.filter((item) => String(item).trim() !== '');
    }
  } catch (error) {
    // Fall back to comma/semicolon separated input.
  }

  return value
    .split(/[;,]/)
    .map((item) => item.trim())
    .filter((item) => item !== '');
}

function toggleActivateConditionsField(){
  const activate_questions_list = document.getElementById('activate_question');
  const activate_conditions = document.getElementById('activate_condition_div');
  if (!activate_questions_list || !activate_conditions) {
    return;
  }

  const questionArray = parseQuestionListValue(activate_questions_list.value);
  activate_conditions.style.display = questionArray.length > 0 ? 'block' : 'none';
  rebuildConditionOptions('activation_condition', 'activation_condition_options');
}

function toggleDeactivateConditionsField(){
  const deactivate_questions_list = document.getElementById('deactivate_question');
  const deactivate_conditions = document.getElementById('deactivate_condition_div');
  if (!deactivate_questions_list || !deactivate_conditions) {
    return;
  }

  const questionArray = parseQuestionListValue(deactivate_questions_list.value);
  deactivate_conditions.style.display = questionArray.length > 0 ? 'block' : 'none';
  rebuildConditionOptions('deactivation_condition', 'deactivation_condition_options');
}

function getAnswerChoiceTexts() {
  const inputs = Array.from(document.querySelectorAll('.choice-formset input[name$="-text"]'));
  return inputs
    .map((input) => String(input.value || '').trim())
    .filter((value, index, values) => value !== '' && values.indexOf(value) === index);
}

function shouldUseConditionRadioOptions() {
  const questionType = document.getElementById('questionType');
  return isChoiceQuestionType(questionType ? questionType.value : '');
}

function parseConditionSelectionValue(rawValue) {
  const value = String(rawValue ?? '').trim();
  if (!value) {
    return [];
  }

  try {
    const parsed = JSON.parse(value);
    if (Array.isArray(parsed)) {
      return parsed
        .map((item) => String(item).trim())
        .filter((item, index, values) => item !== '' && values.indexOf(item) === index);
    }
  } catch (error) {
    // Fall back to legacy comma/semicolon separated values.
  }

  return value
    .split(/[;,]/)
    .map((item) => item.trim())
    .filter((item, index, values) => item !== '' && values.indexOf(item) === index);
}

function updateConditionDropdownSummary(summaryElement, selectedValues) {
  if (!summaryElement) {
    return;
  }

  summaryElement.textContent = selectedValues.length > 0
    ? selectedValues.join(', ')
    : 'Select condition';
}

function normalizeConditionChoice(value) {
  return String(value || '').replace(/\s+/g, ' ').trim().toLowerCase();
}

function rebuildConditionOptions(fieldId, containerId) {
  const hiddenInput = document.getElementById(fieldId);
  const container = document.getElementById(containerId);
  const inputWrap = document.getElementById(`${fieldId}_input_wrap`);
  if (!hiddenInput || !container) {
    return;
  }

  const useRadioOptions = shouldUseConditionRadioOptions();
  if (inputWrap) {
    inputWrap.style.display = useRadioOptions ? 'none' : 'block';
  }
  hiddenInput.style.display = useRadioOptions ? 'none' : '';

  container.style.display = useRadioOptions ? 'block' : 'none';
  container.classList.toggle('condition-choice-multiselect', useRadioOptions);
  if (!useRadioOptions) {
    container.classList.remove('condition-choice-multiselect');
    hiddenInput.style.display = '';
    container.innerHTML = '';
    return;
  }

  const selectedValues = parseConditionSelectionValue(hiddenInput.value);
  const choiceTexts = getAnswerChoiceTexts();
  const selectedValueMap = new Map(
    selectedValues.map((value) => [normalizeConditionChoice(value), value])
  );

  selectedValues.forEach((value) => {
    const hasMatchingChoice = choiceTexts.some(
      (choiceText) => normalizeConditionChoice(choiceText) === normalizeConditionChoice(value)
    );
    if (value && !hasMatchingChoice) {
      choiceTexts.unshift(value);
    }
  });

  container.innerHTML = '';
  const options = choiceTexts.map((text) => ({ value: text, label: text }));
  const matchedSelectedValues = options
    .filter((option) => selectedValueMap.has(normalizeConditionChoice(option.value)))
    .map((option) => option.value);

  const dropdown = document.createElement('div');
  dropdown.className = 'condition-choice-dropdown';

  const toggle = document.createElement('button');
  toggle.type = 'button';
  toggle.className = 'form-control condition-choice-toggle';
  toggle.setAttribute('aria-haspopup', 'listbox');
  toggle.setAttribute('aria-expanded', 'false');

  const summary = document.createElement('span');
  summary.className = 'condition-choice-summary';
  updateConditionDropdownSummary(summary, matchedSelectedValues);

  const caret = document.createElement('span');
  caret.className = 'condition-choice-caret';
  caret.setAttribute('aria-hidden', 'true');
  caret.textContent = '▾';

  toggle.appendChild(summary);
  toggle.appendChild(caret);
  toggle.addEventListener('click', (event) => {
    event.stopPropagation();
    const isOpen = dropdown.classList.toggle('is-open');
    toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
  });

  const menu = document.createElement('div');
  menu.className = 'condition-choice-menu';
  menu.setAttribute('role', 'listbox');
  menu.setAttribute('aria-multiselectable', 'true');

  options.forEach((option, index) => {
    const wrapper = document.createElement('label');
    wrapper.className = 'condition-choice-option';
    wrapper.setAttribute('for', `${fieldId}_choice_${index}`);

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.className = 'form-check-input';
    checkbox.name = `${fieldId}_choice`;
    checkbox.id = `${fieldId}_choice_${index}`;
    checkbox.value = option.value;
    checkbox.checked = selectedValueMap.has(normalizeConditionChoice(option.value));

    const labelText = document.createElement('span');
    labelText.textContent = option.label;

    checkbox.addEventListener('change', () => {
      const selected = Array.from(
        menu.querySelectorAll(`input[name="${fieldId}_choice"]:checked`)
      ).map((input) => input.value.trim()).filter((value) => value !== '');
      hiddenInput.value = selected.join(', ');
      updateConditionDropdownSummary(summary, selected);
    });

    wrapper.appendChild(checkbox);
    wrapper.appendChild(labelText);
    menu.appendChild(wrapper);
  });

  dropdown.appendChild(toggle);
  dropdown.appendChild(menu);
  container.appendChild(dropdown);

  if (choiceTexts.length === 0) {
    const helper = document.createElement('small');
    helper.className = 'text-muted d-block mt-1';
    helper.textContent = 'Add answer choices to select a condition.';
    menu.appendChild(helper);
  }
}

document.addEventListener('click', (event) => {
  document.querySelectorAll('.condition-choice-dropdown.is-open').forEach((dropdown) => {
    if (!dropdown.contains(event.target)) {
      dropdown.classList.remove('is-open');
      const toggle = dropdown.querySelector('.condition-choice-toggle');
      if (toggle) {
        toggle.setAttribute('aria-expanded', 'false');
      }
    }
  });
});

function refreshConditionOptionGroups() {
  rebuildConditionOptions('activation_condition', 'activation_condition_options');
  rebuildConditionOptions('deactivation_condition', 'deactivation_condition_options');
}

function updateConditionSelectionForChoiceRename(fieldId, oldValue, newValue) {
  const field = document.getElementById(fieldId);
  const oldText = String(oldValue || '').trim();
  const newText = String(newValue || '').trim();
  if (!field || oldText === '' || oldText === newText) {
    return;
  }

  const selectedValues = parseConditionSelectionValue(field.value);
  let changed = false;
  const updatedValues = selectedValues.map((value) => {
    if (normalizeConditionChoice(value) === normalizeConditionChoice(oldText)) {
      changed = true;
      return newText;
    }
    return value;
  }).filter((value, index, values) => value !== '' && values.indexOf(value) === index);

  if (changed) {
    field.value = updatedValues.join(', ');
  }
}

function syncConditionSelectionsForChoiceRename(input) {
  const oldValue = input.dataset.previousChoiceText || '';
  const newValue = input.value || '';
  updateConditionSelectionForChoiceRename('activation_condition', oldValue, newValue);
  updateConditionSelectionForChoiceRename('deactivation_condition', oldValue, newValue);
  input.dataset.previousChoiceText = newValue;
}


document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.choice-formset input[name$="-text"]').forEach((input) => {
    input.dataset.previousChoiceText = input.value || '';
  });
  refreshConditionOptionGroups();
  document.addEventListener('input', (event) => {
    if (event.target && event.target.matches('.choice-formset input[name$="-text"]')) {
      clearAnswerChoiceSeparatorValidity(event.target);
      if (!event.target.checkValidity()) {
        return;
      }
      syncConditionSelectionsForChoiceRename(event.target);
      refreshConditionOptionGroups();
    }
  });
});


   document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('categoryModal');
    if (!modal) return;

    const form = modal.querySelector('form');
    if (!form) return;

    const originalFormHTML = form.innerHTML; // Store original HTML when DOM is loaded

    modal.addEventListener('hidden.bs.modal', function () {
      form.innerHTML = originalFormHTML; // Reset form content
    });
  });
    let initialCategoryCount = 0;

document.addEventListener("DOMContentLoaded", function () {
  const modal = document.getElementById("categoryModal");

  if (!modal) return;

  // On modal open: record the number of existing category forms
  modal.addEventListener("show.bs.modal", () => {
    const forms = document.getElementsByClassName("category-formset mb-4");
    initialCategoryCount = forms.length;
  });

  // On modal close: remove any added forms beyond the original count
  modal.addEventListener("hidden.bs.modal", () => {
    const allForms = document.getElementsByClassName("category-formset mb-4");
    const totalForms = document.getElementById("id_form-TOTAL_FORMS");

    for (let i = allForms.length - 1; i >= initialCategoryCount; i--) {
      allForms[i].remove();
    }

    // Reset form fields in the initial form(s)
    for (let i = 0; i < initialCategoryCount; i++) {
      const titleField = document.getElementById(`id_form-${i}-categoryTitle`);
      const valueField = document.getElementById(`id_form-${i}-categoryValue`);
      const checkbox = document.getElementById(`id_form-${i}-didSubjectAsk`);

      if (titleField) titleField.value = titleField.defaultValue || "";
      if (valueField) valueField.value = valueField.defaultValue || Math.max(i + 1, 1);
      if (checkbox) checkbox.checked = checkbox.defaultChecked;
    }

    if (totalForms) {
      totalForms.value = initialCategoryCount;
    }

    update_remove_buttons();
  });
});
// function ensureChoiceFormCount(minCount) {
//   let currentCount = document.querySelectorAll('.choice-formset').length;
//   while (currentCount < minCount) {
//     add_choices_form();
//     currentCount = document.querySelectorAll('.choice-formset').length;
//   }
// }

// function setChoiceTexts(values) {
//   ensureChoiceFormCount(values.length);
//   values.forEach((value, index) => {
//     const input = document.querySelector(`[name="form-${index}-text"]`);
//     if (input) {
//       input.value = value;
//     }
//   });
// }

// function setSlidingDefaults(values) {
//   const defaults = {
//     value: 1,
//     defaultValue: 3,
//     stepSize: 1,
//     minValue: 1,
//     maxValue: 5,
//     minText: 'Low',
//     maxText: 'High',
//   };
//   const finalValues = { ...defaults, ...values };
//   Object.entries(finalValues).forEach(([field, value]) => {
//     const input = document.querySelector(`[name="form-0-${field}"]`);
//     if (input) {
//       input.value = value;
//     }
//   });
// }

// function applyQuestionTemplate(templateName) {
//   const templates = {
//     weekly_duration: {
//       questionType: '9',
//       frequency: 7,
//       nextDayToAnswer: 1,
//       deactivateOnDate: 0,
//       choices: [],
//     },
//     daily_single_choice: {
//       questionType: '1',
//       frequency: 1,
//       nextDayToAnswer: 1,
//       deactivateOnDate: 0,
//       choices: ['Yes', 'No'],
//     },
//     monthly_multiple_choice: {
//       questionType: '2',
//       frequency: 30,
//       nextDayToAnswer: 1,
//       deactivateOnDate: 0,
//       choices: ['Option 1', 'Option 2', 'Option 3'],
//     },
//     weekly_sliding_choice: {
//       questionType: '3',
//       frequency: 7,
//       nextDayToAnswer: 1,
//       deactivateOnDate: 0,
//       sliding: {
//         value: 1,
//         defaultValue: 3,
//         stepSize: 1,
//         minValue: 1,
//         maxValue: 5,
//         minText: 'Very low',
//         maxText: 'Very high',
//       },
//       choices: [],
//     },
//     weekly_free_text: {
//       questionType: '4',
//       frequency: 7,
//       nextDayToAnswer: 1,
//       deactivateOnDate: 0,
//       choices: [],
//     }
//   };

//   const template = templates[templateName];
//   if (!template) {
//     return;
//   }

//   const defaultToggle = document.getElementById('flexSwitchCheckDefault');
//   if (defaultToggle) {
//     defaultToggle.checked = false;
//   }

//   $('#questionType').val(template.questionType);
//   $('#frequency').val(template.frequency);
//   $('#nextDayToAnswer').val(template.nextDayToAnswer);
//   $('#deactivateOnDate').val(template.deactivateOnDate);

//   show_answer_form();

//   if (template.questionType === '1' || template.questionType === '2') {
//     setChoiceTexts(template.choices);
//   }
//   if (template.questionType === '3' && template.sliding) {
//     setSlidingDefaults(template.sliding);
//   }
// }
