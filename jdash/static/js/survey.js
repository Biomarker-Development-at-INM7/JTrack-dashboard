console.log("Loaded survey.js version 2025-08-15");

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
    'Duration': '9'


}
///////////
///Survey details table
//////////////////
$(function() {
    initTable()

})
function initTable() {
    $('#survey_quest_table').bootstrapTable({
      detailViewAlign : 'right',
      paginationParts: ['pageInfoshort', 'pageSize', 'pageList']
    })

    $('#quest_table').bootstrapTable({
      detailViewAlign : 'right',
      exportTypes: ['json', 'csv'],
      exportDataType: 'all',
      onExportSaved: function (arg1) {  },
      exportOptions: {
        fileName: function () {
           return 'survey'
        }
     },
      paginationParts: ['pageInfoshort', 'pageSize', 'pageList']
    })

    $('#survey_table').bootstrapTable({
      detailViewAlign : 'right',
      paginationParts: ['pageInfoshort', 'pageSize', 'pageList']
    })
    $('#cat_table').bootstrapTable({
      detailViewAlign : 'right',
      paginationParts: ['pageInfoshort', 'pageSize', 'pageList']
    })
  }

window.operateEvents = {
    'click .edit': function (e, value, row, index) {
      $('#questionModalLabel').text("Edit Question Details" );
      $('#id_value').val(row[0] );
      $('#questionTitle').val(row[1] );
      $('#subText').val(row[2] );
      $('#questionType').val(question_types[row[3]] );
      $('#category').val(row[4] );
      $('#frequency').val(row[5]);
      $('#clockTime').val(row[6] );
      $('#nextDayToAnswer').val(row[7] );
      $('#url').val(row[9] );
      $('#imageURL').val(row[8] );
      $('#deactivateOnAnswer').val(row[11] );
      $('#deactivateOnDate').val(row[10] );
      if ($('#questionType').val() == 1 || $('#questionType').val() == 2  ){
        $("#answerChoices").css("display", "block");
        $('#answerText').val(row[13] );
      }
        else if ($('#questionType').val() == 3  ){
           $("#slidingAnswer").css("display", "block");
        $('#answerValue').val(row[14] );
        $('#defaultValue').val(row[15] );
        $('#stepSize').val(row[16] );
        $('#minValue').val(row[17] );
        $('#maxValue').val(row[18] );
        $('#minText').val(row[19] );
        $('#maxText').val(row[20] );
      }else{
        $("#otherTypeAnswer").css("display", "block");
        $('#answerText').val('');
        $('#answerSortId').val(row[22] );
        $('#answerSubText').val(row[21]);
        $('#answerValue').val(0.1 );
        $('#defaultValue').val(0.1 );
        $('#stepSize').val(0.1);
        $('#minValue').val(0.1);
        $('#maxValue').val(0.1);
        $('#minText').val('');
        $('#maxText').val('' );
      }

    },
    'click .delete': function (e, value, row, index) {
      $("#survey_quest_table").bootstrapTable('remove', {
        field: 'id',
        values: [row.id]
      })
      var questionTitle = row[1];
      // Update a hidden input field in the form with the quest ID
      var input = document.createElement('input');
      input.type = 'hidden';
      input.name = 'question_title';
      input.value = questionTitle;
      document.getElementById('removeQuestionForm').appendChild(input);
    }
  }


  window.createOperateEvents = {
    'click .edit': function (e, value, row, index) {
    },
    'click .delete': function (e, value, row, index) {
      $("#quest_table").bootstrapTable('remove', {
        field: 'id',
        values: [row.id]
      })
      var questionId = row[0];
      // Update a hidden input field in the form with the quest ID
      var input = document.createElement('input');
      input.type = 'hidden';
      input.name = 'question_id';
      input.value = questionId;
      document.getElementById('deleteQuestionForm').appendChild(input);
    }
  }


window.survey_operateEvents = {
    'click .delete': function (e, value, row, index) {
      $("#survey_table").bootstrapTable('remove', {
        field: 'survey_id',
        values: [row.survey_id]
      })
              // Retrieve the survey ID from the data-id attribute
              var surveyId = row.survey_id;
              // Update a hidden input field in the form with the survey ID
              var input = document.createElement('input');
              input.type = 'hidden';
              input.name = 'survey_id';
              input.value = surveyId;
              document.getElementById('deleteSurveyForm').appendChild(input);

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

    const selectedValue = questionType.value;
    const isChoice = selectedValue === '1' || selectedValue === '2';
    const isSliding = selectedValue === '3';
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
      element.style.display = (!isChoice && !isSliding) ? 'block' : 'none';
    });
  }
function initializeDefaultValueToggle() {
  const toggle = document.getElementById('flexSwitchCheckDefault');
  const advancedSection = document.getElementById('advanced-values-section');

  if (!toggle) return;

  function updateVisibility() {
    if (toggle.checked && advancedSection) {
      advancedSection.style.display = 'none';
    } else if (advancedSection) {
      advancedSection.style.display = '';
    }
  }

  if (window.current_sort_id === 1) {
    toggle.checked = true;
    toggle.disabled = true;
  }

  updateVisibility();
  toggle.addEventListener('change', () => {
    updateVisibility();
    set_default_values(toggle);
  });

  if (toggle.checked) {
    set_default_values(toggle);
  }
}
function set_default_values(default_switch){
  const isFirstQuestion = current_sort_id === 1;

  if (default_switch.checked) {
    if (isFirstQuestion) {
      // Apply static defaults for question 1
      $('#category').val(1);
      $('#nextDayToAnswer').val(1);
      $('#frequency').val(0);
      $('#clockTime').val(480);
      $('#deactivateOnDate').val(0);
    } else {
      // Apply values from previous question
      if (typeof previous_question_object !== 'undefined') {
        $('#category').val(previous_question_object.category || '');
        $('#nextDayToAnswer').val(previous_question_object.nextDayToAnswer || '');
        $('#frequency').val(previous_question_object.frequency || '');
        $('#clockTime').val(previous_question_object.clockTime || '');
        $('#deactivateOnDate').val(previous_question_object.deactivateOnDate || '');
      } else {
        console.warn("Previous question values are not available.");
      }
    }
  } else {
    // Clear values
    $('#category').val('');
    $('#nextDayToAnswer').val('');
    $('#frequency').val('');
    $('#clockTime').val('');
    $('#deactivateOnDate').val('');
  }
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
    $('#clockTime_start').val('[]')
    $('#clockTime_end').val('[]')
    $('#deactivateOnAnswer').val('')
    $('#deactivateOnDate').val(0)
    $('#activate_question').val('[]')
    $('#deactivate_question').val('[]')
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

function editQuestion(){
  const questionForm = document.getElementById("questionForm");
  var input = document.createElement('input');
  input.type = 'hidden';
  input.name = 'update_question';
  questionForm.appendChild(input);
  questionForm.submit();
}

function display_info(event){
    event.preventDefault();
  if (validateNecessaryFields() && validateClockTimes()) {
    $('#updateModal').modal('show');
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
    frequencyEl.setCustomValidity('Please enter a repetition interval or default values check the default switch');
    frequencyEl.reportValidity();
    return false;
  } else if (deactivateOnDateEl && String(deactivateOnDateEl.value).trim() === '') {
    deactivateOnDateEl.setCustomValidity('Please enter deactivate after days or default values check the default switch');
    deactivateOnDateEl.reportValidity();
    return false;
  } else if (nextDayToAnswerEl && String(nextDayToAnswerEl.value).trim() === '') {
    nextDayToAnswerEl.setCustomValidity('Please enter the first day to answer or default values check the default switch');
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

  quest_table = $('#quest_table')
  const questionForm = document.getElementById("questionForm");
  var x = $('#quest_table').bootstrapTable('getData').length;
  var rowCount = $('#quest_table tr').length;
  var row = document.createElement('tr');
  row.setAttribute('id',`tr-${rowCount -1}`)
  for (var c=0;c<= 7; c++){
  column = document.createElement('td');
  column.innerHTML = "<span>"+ questionForm.elements['title'].value+ "</span>"
  row.append(column)
  }
  quest_table.append(row)
  var input = document.createElement('input');
  input.type = 'hidden';
  input.name = 'add_question';
  questionForm.appendChild(input);
  $('#sort_id').val(x + 1 );
  questionForm.submit();

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

    alert("At least one category is required.");
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
}

function toggleActivateConditionsField(){
  const activate_questions_list = document.getElementById('activate_question')
  const activate_conditions = document.getElementById('activate_condition_div')
  try {
    // Parse the value in the textarea as JSON (an array)
    const questionArray = JSON.parse(activate_questions_list.value);

    // Check if it's a non-empty array
    if (Array.isArray(questionArray) && questionArray.length > 0) {
        activate_conditions.style.display = 'block'
      }else{
        activate_conditions.style.display = 'none'
      }
    } catch (e) {
      // If JSON parsing fails (invalid JSON), hide the div
      activate_conditions.style.display = 'none';
    }

}

function toggleDeactivateConditionsField(){
  const deactivate_questions_list = document.getElementById('deactivate_question')
  const deactivate_conditions = document.getElementById('deactivate_condition_div')

  try {
    // Parse the value in the textarea as JSON (an array)
    const questionArray = JSON.parse(deactivate_questions_list.value);

    // Check if it's a non-empty array
    if (Array.isArray(questionArray) && questionArray.length > 0) {
      deactivate_conditions.style.display = 'block'
      }else{
        deactivate_conditions.style.display = 'none'
      }
    } catch (e) {
      // If JSON parsing fails (invalid JSON), hide the div
      deactivate_conditions.style.display = 'none';
    }

}

function ensureChoiceFormCount(minCount) {
  let currentCount = document.querySelectorAll('.choice-formset').length;
  while (currentCount < minCount) {
    add_choices_form();
    currentCount = document.querySelectorAll('.choice-formset').length;
  }
}

function setChoiceTexts(values) {
  ensureChoiceFormCount(values.length);
  values.forEach((value, index) => {
    const input = document.querySelector(`[name="form-${index}-text"]`);
    if (input) {
      input.value = value;
    }
  });
}

function setSlidingDefaults(values) {
  const defaults = {
    value: 1,
    defaultValue: 3,
    stepSize: 1,
    minValue: 1,
    maxValue: 5,
    minText: 'Low',
    maxText: 'High',
  };
  const finalValues = { ...defaults, ...values };
  Object.entries(finalValues).forEach(([field, value]) => {
    const input = document.querySelector(`[name="form-0-${field}"]`);
    if (input) {
      input.value = value;
    }
  });
}

function applyQuestionTemplate(templateName) {
  const templates = {
    weekly_duration: {
      questionType: '9',
      frequency: 7,
      nextDayToAnswer: 1,
      deactivateOnDate: 0,
      choices: [],
    },
    daily_single_choice: {
      questionType: '1',
      frequency: 1,
      nextDayToAnswer: 1,
      deactivateOnDate: 0,
      choices: ['Yes', 'No'],
    },
    monthly_multiple_choice: {
      questionType: '2',
      frequency: 30,
      nextDayToAnswer: 1,
      deactivateOnDate: 0,
      choices: ['Option 1', 'Option 2', 'Option 3'],
    },
    weekly_sliding_choice: {
      questionType: '3',
      frequency: 7,
      nextDayToAnswer: 1,
      deactivateOnDate: 0,
      sliding: {
        value: 1,
        defaultValue: 3,
        stepSize: 1,
        minValue: 1,
        maxValue: 5,
        minText: 'Very low',
        maxText: 'Very high',
      },
      choices: [],
    },
    weekly_free_text: {
      questionType: '4',
      frequency: 7,
      nextDayToAnswer: 1,
      deactivateOnDate: 0,
      choices: [],
    }
  };

  const template = templates[templateName];
  if (!template) {
    return;
  }

  const defaultToggle = document.getElementById('flexSwitchCheckDefault');
  if (defaultToggle) {
    defaultToggle.checked = false;
  }

  $('#questionType').val(template.questionType);
  $('#frequency').val(template.frequency);
  $('#nextDayToAnswer').val(template.nextDayToAnswer);
  $('#deactivateOnDate').val(template.deactivateOnDate);

  show_answer_form();

  if (template.questionType === '1' || template.questionType === '2') {
    setChoiceTexts(template.choices);
  }
  if (template.questionType === '3' && template.sliding) {
    setSlidingDefaults(template.sliding);
  }
}
