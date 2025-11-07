
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
        field: 'id',
        values: [row.id]
      })
              // Retrieve the survey ID from the data-id attribute
              var surveyId = row["survey_id"];
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
    var selectedValue = document.getElementById('questionType').value;
    const totalChoiceForms = document.getElementById("id_form-TOTAL_FORMS")
      if (selectedValue == '1' || selectedValue == '2'){
        document.getElementById('answerForm_header').style.display = 'block';
        document.getElementById('add-choice').style.display = 'block';
        for (var i = 0; i < totalChoiceForms.value; i++) {
          document.getElementById('choice-form-'+ i ).style.display = 'block';
        } 
        document.getElementById('slidingAnswer-0').style.display = 'none';
        document.getElementById('slidingAnswer-1').style.display = 'none';
        document.getElementById('subTextDiv').style.display = 'none';
      }else if (selectedValue == 3){
        document.getElementById('answerForm_header').style.display = 'block';
        document.getElementById('slidingAnswer-0').style.display = 'block';
        document.getElementById('slidingAnswer-1').style.display = 'block';
        for (var i = 0; i < totalChoiceForms.value; i++) {
          document.getElementById('choice-form-'+ i ).style.display = 'none';
        }
        document.getElementById('subTextDiv').style.display = 'none';
      }else if (selectedValue == 4 || selectedValue == 5 || selectedValue == 6 
          || selectedValue == 7 || selectedValue == 8 || selectedValue == 9){
        document.getElementById('answerForm_header').style.display = 'block';
        document.getElementById('subTextDiv').style.display = 'block';
        document.getElementById('add-choice').style.display = 'none';
        for (var i = 0; i < totalChoiceForms.value; i++) {
          document.getElementById('choice-form-'+ i ).style.display = 'none';
        }
        
        document.getElementById('slidingAnswer-0').style.display = 'none';
        document.getElementById('slidingAnswer-1').style.display = 'none';
      }else{
        document.getElementById('answerForm_header').style.display = 'none';
        document.getElementById('add-choice').style.display = 'none';
        for (var i = 0; i < totalChoiceForms.value; i++) {
          document.getElementById('choice-form-'+ i ).style.display = 'none';
        }
        document.getElementById('slidingAnswer-0').style.display = 'none';
        document.getElementById('slidingAnswer-1').style.display = 'none';
        document.getElementById('subTextDiv').style.display = 'none';
      }
  }

function set_default_values(default_switch){
 if (default_switch.checked){
    $('#category').val(1)
    $('#nextDayToAnswer').val(1)
    $('#frequency').val(0)
    $('#clockTime').val(480)
    $('#deactivateOnDate').val(0)
  }else{
    $('#category').val('')
    $('#nextDayToAnswer').val('')
    $('#frequency').val('')
    $('#clockTime').val('')
    $('#deactivateOnDate').val('')
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
}




///////// Questions /////

function loadAnswerForm(){
  var selectedValue = document.getElementById('questionType').value;
    if (selectedValue == '1' || selectedValue == '2'){
      document.getElementById('add-choice').style.display = 'block';
    }

}

function editQuestion(){
  const questionForm = document.getElementById("editQuestionForm");
  var input = document.createElement('input');
  input.type = 'hidden';
  input.name = 'update_question';
  questionForm.appendChild(input);
  questionForm.submit();
}


function display_info(){
    // stop any native submit/validation
    if (validateNecessaryFields() && validateClockTimes()) {
      $('#updateModal').modal('show');
    }

}

function validateNecessaryFields() {
  const qTitleEl = document.getElementById('questionTitle');
  const qsubTextEl = document.getElementById('subText');
  const qTypeEl = document.getElementById('questionType');
  qTitleEl.setCustomValidity('');
  qsubTextEl.setCustomValidity('');
  qTypeEl.setCustomValidity('');

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

function addAnswer(){
  const answerForm = document.getElementById("answerForm");
  questionForm.append(document.getElementsByName('add_answer'))
  answerForm.submit(); 
}


///////// Categories /////


function add_category_form(){
  
  
  const main = document.getElementById("category_details_form")
  const totalCategoryForms = document.getElementById("id_form-TOTAL_FORMS")
 
  const currentCategoryForms = document.getElementsByClassName("category-formset mb-4")
  const currentFormCount = currentCategoryForms.length //+ 1

  //add new category form

  const categoryFormEl = document.getElementById('category-form-0').cloneNode(true)
  
  categoryFormEl.setAttribute('class','category-formset mb-4')
  categoryFormEl.setAttribute('id',`category-form-${currentFormCount}`)
  const regex = new RegExp('form-0-','g')
  categoryFormEl.innerHTML  = categoryFormEl.innerHTML.replace(regex,"form-"+currentFormCount+"-")
  categoryFormEl.innerHTML  = categoryFormEl.innerHTML.replace('id_0_remove_btn',"id_"+currentFormCount+"_remove_btn")
  totalCategoryForms.setAttribute('value', currentFormCount + 1)
  
  main.appendChild(categoryFormEl)
  const initialCategoryForms = document.getElementById("id_form-INITIAL_FORMS")
  if (initialCategoryForms.value != 0 ){
    document.getElementById("id_form-"+currentFormCount+"-categoryTitle").value = ""
    
  }
  if (currentFormCount> 0){
    document.getElementById("id_"+currentFormCount+"_remove_btn").disabled = false
  }
}

function remove_category_form(id){
  array = id.split("_")
  if(array[1] != 0){
  const main = document.getElementById("category_details_form")
  const categoryFormEl = document.getElementById("category-form-"+array[1])
  main.removeChild(categoryFormEl)
  }
}

function add_choices_form(){
  const main = document.getElementById("choice_details_form")
  const totalChoiceForms = document.getElementById("id_form-TOTAL_FORMS")
  const currentChoiceForms = document.getElementsByClassName("choice-formset mb-4")
  const currentFormCount = currentChoiceForms.length // +1
  

  //add new choice form

  const choiceFormEl = document.getElementById('choice-form-0').cloneNode(true)
  
  choiceFormEl.setAttribute('class','row choice-formset mb-4')
  choiceFormEl.setAttribute('id',`choice-form-${currentFormCount}`)
  const regex = new RegExp('form-0-','g')
  choiceFormEl.innerHTML  = choiceFormEl.innerHTML.replace(regex,"form-"+currentFormCount+"-")
  choiceFormEl.innerHTML  = choiceFormEl.innerHTML.replace('id_0_remove_btn',"id_"+currentFormCount+"_remove_btn")
  totalChoiceForms.setAttribute('value', currentFormCount + 1)
  
  main.appendChild(choiceFormEl)
  const initialChoiceForms = document.getElementById("id_form-INITIAL_FORMS")
    document.getElementById("id_form-"+currentFormCount+"-answerSortId").value = ""
    document.getElementById("id_form-"+currentFormCount+"-text").value = ""
  if (currentFormCount> 0){
    document.getElementById("id_"+currentFormCount+"_remove_btn").disabled = false
  }
}

function remove_choice_form(id){

  const idToRemove = document.getElementById("answer_id").value
  // Select all input elements with name "answer_id" and extract their values.
  const answerIdElements = document.querySelectorAll('input[name="answer_id"]');
  const answerIds = Array.from(answerIdElements, el => el.value);
  // Filter the array to remove the specified ID.
  var filteredAnswerIds = answerIds.filter(id => id !== idToRemove);

  filteredAnswerIds = document.querySelectorAll('input[name="answer_id"]');

  array = id.split("_")
  if(array[1] != 0){
  const main = document.getElementById("choice_details_form")
  const choiceFormEl = document.getElementById("choice-form-"+array[1])
  
  main.removeChild(choiceFormEl)
  }
}

function toggleActivateConditionsField(){
  const aqEl = document.getElementById('activate_question')
  const conaEl = document.getElementById('activate_condition_div')
    const conditionInput = conaEl.querySelector('input');
  const val = aqEl.value.trim();
  aqEl.setCustomValidity('');
  // Test for an integer (one or more digits only)
  const pattern = /^\d+(?:,\d+)*$/.test(val);
  if (val !== '' && !pattern){
    aqEl.setCustomValidity('Please enter a comma-separated list of question IDs.');
    aqEl.reportValidity();
  }
    if (val === '') {
    conaEl.value = '';
        if (conditionInput) {
      conditionInput.value = '';                        // Clear value
      conditionInput.removeAttribute('value');          // Prevent "cached" value on reload
      conditionInput.setAttribute('autocomplete', 'off'); // Prevent browser autocomplete
    }
  }
  // Show if integer, hide otherwise
  conaEl.style.display = val ? '' : 'none';
}

function toggleDeactivateConditionsField(){
  const dqEl = document.getElementById('deactivate_question')
  const condEl = document.getElementById('deactivate_condition_div')
    const conditionInput = condEl.querySelector('input');
  const val = dqEl.value.trim();
  dqEl.setCustomValidity('');
  // Test for an integer (one or more digits only)
  const pattern = /^\d+(?:,\d+)*$/.test(val);
  if (val !== '' && !pattern){
    dqEl.setCustomValidity('Please enter a comma-separated list of question IDs.');
    dqEl.reportValidity();
  }
  if (val === '') {
    conaEl.value = '';
    if (conditionInput) {
      conditionInput.value = '';                        // Clear value
      conditionInput.removeAttribute('value');          // Prevent "cached" value on reload
      conditionInput.setAttribute('autocomplete', 'off'); // Prevent browser autocomplete
    }
  }
  // Show if integer, hide otherwise
  condEl.style.display = val ? '' : 'none';

}
