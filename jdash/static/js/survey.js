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
    $('#survey_audit_table').bootstrapTable({
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
  if (!validateAnswerChoiceSeparators() || !validateConditionQuestionCategories()) {
    return;
  }
  const questionForm = document.getElementById("questionForm");
  var input = document.createElement('input');
  input.type = 'hidden';
  input.name = 'update_question';
  questionForm.appendChild(input);
  questionForm.submit();
}

function display_info(event){
    //event.preventDefault();
    if (validateNecessaryFields() && validateClockTimes() && validateAnswerChoiceSeparators() 
        && validateConditionQuestionCategories()) {
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
    const sNum = parseInt(s, 10);
    const eNum = parseInt(e, 10);
      // Check ordering
    if (eNum <= sNum) {
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


function delete_quest(){
  const deleteQuestionForm = document.getElementById("deleteQuestionForm");
  deleteQuestionForm.submit();
}

function remove_question(){
  const removeQuestionForm = document.getElementById("removeQuestionForm");
  removeQuestionForm.submit();
}

///////// Answers /////

function validateAnswerChoiceSeparators() {
  const answerInputs = Array.from(document.querySelectorAll('.choice-formset input[name$="-text"]'));
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
  const selectedValue = questionType ? String(questionType.value || '') : '';
  return selectedValue === '1' || selectedValue === '2';
}

function parseConditionSelectionValue(rawValue) {
  const value = String(rawValue ?? '').trim();
  if (!value) {
    return [];
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
