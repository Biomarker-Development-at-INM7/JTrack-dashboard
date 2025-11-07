var sensorDefaults  = {
  ema : "ema",
  ac : "ac",
  at:  'at',

  gy:'gy',

  lo :'lo',

  ln:'ln',

  vo: 'vo',

  al :'al',

  au : 'au',

  ba :'ba',

  gs :'gs',
  ms: 'ms'
}
$(document).ready(function() {

  $('#index_table').removeClass('table-hover');

    $('#list').click(function(event){
    event.preventDefault();
    document.getElementById("index-list").style.display = "block";
    document.getElementById("index-grid").style.display = "none";
    $('#grid').removeClass('active');
       $('#list').addClass('active');
  });

  $('#grid').click(function(event){
    event.preventDefault();

    document.getElementById("index-list").style.display = "none";
    document.getElementById("index-grid").style.display = "block";
    $('#list').removeClass('active');
      $('#grid').addClass('active');

  });



});

function select_all_ids(){
  var options = document.getElementById('id-choices').options;
  for (let i = 0; i < options.length; i++) { 
    options[i].selected = select_all_ids ;
  }
}

function select_missing_ids(){
  var options = document.getElementById('id-choices').options;
  for (let i = 0; i < options.length; i++) { 
    missing = options[i].value.split(";")[1]
    if(missing == "True"){ options[i].selected = select_missing_ids ;}
      
  }
}

function change_active_sensors() {
  // Get selected options from the Passive Sensors dropdown
  let selectedOptions = Array.from(document.getElementById('id_sensor_list').selectedOptions);
  let selectedValues = selectedOptions.map(option => option.value);

  // Get the Active Sensors dropdown
  let sensorListLimited = document.getElementById('sensor_list_limited');

  // Get all options in Active Sensors dropdown
  let allActiveOptions = Array.from(sensorListLimited.options);

  // Add back any options that were previously deselected in Passive Sensors
  let allSensors = ["accelerometer", "activity", "application_usage", "barometer", "gravity_sensor", "gyroscope", "location", "magnetic_sensor", "rotation_vector", "linear_acceleration", "lockUnlock", "voice"];

  // Clear the Active Sensors dropdown
  //sensorListLimited.innerHTML = '';

  // Add back the unselected options from Passive Sensors
  allSensors.forEach(sensor => {
      if (!selectedValues.includes(sensor)) {
          let option = document.createElement('option');
          option.value = sensor;
          option.text = sensor.replace(/_/g, ' ');
          sensorListLimited.add(option);
            // At least one sensor is being added back to the list
      
      }
  });
   
}


function change_active_sensors() {
  // Get selected options from the Passive Sensors dropdown
  let selectedOptions = Array.from(document.getElementById('id_sensor_list').selectedOptions);
  let selectedValues = selectedOptions.map(option => option.value);

  // Get the Active Sensors dropdown
  let sensorListLimited = document.getElementById('sensor_list_limited');

  // Get all options in Active Sensors dropdown
  let allActiveOptions = Array.from(sensorListLimited.options);

  // Add back any options that were previously deselected in Passive Sensors
  let allSensors = ["accelerometer", "activity", "application_usage", "barometer", "gravity_sensor", "gyroscope", "location", "magnetic_sensor", "rotation_vector", "linear_acceleration", "lockUnlock", "voice"];

  // Clear the Active Sensors dropdown
  sensorListLimited.innerHTML = '';

  // Add back the unselected options from Passive Sensors
  allSensors.forEach(sensor => {
      if (!selectedValues.includes(sensor)) {
          let option = document.createElement('option');
          option.value = sensor;
          option.text = sensor.replace(/_/g, ' ');
          sensorListLimited.add(option);
            // At least one sensor is being added back to the list
      
      }
  });
   
}

function show_task_form(){

  // Get the task checkbox element
  let taskCheckbox = document.querySelector('input[name="task_checkbox"]');
  // Flag to determine if we need to check the task checkbox
  let addToLimited = false;
  // Check the task checkbox if any sensor is added to the limited list
  if (addToLimited && taskCheckbox) {
    taskCheckbox.checked = true;
    // Trigger the onclick function to show task details form
    show('task_details_form', taskCheckbox);
  }
}

function create_subject(){
  // Get the modal
  var modal = document.getElementById("createSubModal");  
  modal.style.display = "block";
  }

function remove_subject(){
const removeForm = document.forms.removeForm;
removeForm.submit(); 
}

function close_study(){
  const closeForm = document.forms.closeForm;
  closeForm.submit(); 
}



///question table

///////////
///Main details table
//////////////////
$(function() {
  initTable()
  
})

var filterDefaults = ['Completed', 'Instudy','Left study', 'Removed']



function dateformatter(value){
  if (value != 'none'){
  var date = new Date(value)
  return date.toString().substring(0,24);
  }
  else{
    return value;
  }
}

function detailFilter(index,row) {
  if (typeof(row["subject_id"]) != "undefined"){
  if (row["subject_id"].includes("user_sheet")) 
    return false; 
  else 
    return true;
  }
  else return false;
}

function buildchildtr(table,header,n_batches,last_time_received){
  var rowheader = document.createElement('tr');
  var columnvalue = document.createElement('td')
  columnvalue.innerHTML = "<strong>" + header + "</strong";
  rowheader.append(columnvalue)
  table.append(rowheader)
  var row2 = document.createElement('tr');
  row2.setAttribute('colspan','2')

  var column21 = document.createElement('td');
  
  column21.innerHTML = "<p>n_batches : <span>"+n_batches +"</p></span> "
  row2.append(column21)
  var column22 = document.createElement('td');
  
  column22.innerHTML = "<p>last_time_received : <span>"+dateformatter(last_time_received )+"</p></span> "
  row2.append(column22)
  table.append(row2)
}

function detailFormatter(index, row, element){ 
  
  
  var mainDiv = document.createElement("div");
  mainDiv.setAttribute('class',' hiddenRow');
      
    var table = document.createElement('table');
    table.setAttribute('class','ui very compact table');
    table.setAttribute('id','sub_table');


    var rowdetail = document.createElement('tr');
    //row.setAttribute('class','hiddenRow')

    var column = document.createElement('td');
    
    column.innerHTML = "<p>device_id : <span>"+row['device_id'] +"</p></span> "
    rowdetail.append(column)
    table.append(rowdetail)


    var row1 = document.createElement('tr');
    row1.setAttribute('colspan','2')
   
    var column11 = document.createElement('td');
    
    column11.innerHTML = "<p>date_registered : <span>"+dateformatter(row['date_registered'] )+"</p></span> "
    row1.append(column11)
    var column12 = document.createElement('td');
    
    column12.innerHTML = "<p>date_left_study : <span>"+dateformatter(row['date_left_study'] )+"</p></span> "
    row1.append(column12)
    table.append(row1)

    if (row["appName"] == "ema"){
      var nb = row['n_batches_ema'];
      var ltr = row['last_time_received_ema'];
      buildchildtr(table,"ema",nb,ltr)
    }

    else{
      if (row['sensor_list'].includes(",")){
        arr = row['sensor_list'].split(",")
        for (var i = 0, len = arr.length; i < len; i++)  {
          arr[i] = arr[i].replaceAll("&#39;","")
            if (i==0){
              arr[i] = arr[i].substring(1,arr[i].length)
            }
            else if (i == len - 1){
              arr[i] = arr[i].substring(0,arr[i].length -1 )
            }
            
            let nb = row['n_batches_'+arr[i].trim()];
            let ltr = row['last_time_received_'+arr[i].trim()];
            buildchildtr(table,arr[i],nb,ltr)
            
          }
      }
      else{
        var sensor = row['sensor_list']
        sensor = sensor.replaceAll("&#39;","")
        let nb = row['n_batches_'+sensor.substring(1,sensor.length -1)];
        let ltr = row['last_time_received_'+sensor.substring(1,sensor.length -1)];
        buildchildtr(table,sensor.substring(1,sensor.length -1),nb,ltr)
      }

        // logic to include active sensors
      if (row['sensor_list_limited'].includes(",")){
        s_arr = row['sensor_list_limited'].split(",")
        for (var i = 0, len = s_arr.length; i < len; i++)  {
          s_arr[i] = s_arr[i].replaceAll("&#39;","")
            if (i==0){
              s_arr[i] = s_arr[i].substring(1,s_arr[i].length)
            }
            else if (i == len - 1){
              s_arr[i] = s_arr[i].substring(0,s_arr[i].length -1 )
            }

            let s_nb = row['n_batches_'+s_arr[i].trim()];
            let s_ltr = row['last_time_received_'+s_arr[i].trim()];
            buildchildtr(table,s_arr[i],s_nb,s_ltr)

          }
      }
      else{
          if(row['sensor_list_limited'] != '[]'){
        var sensor_active = row['sensor_list_limited']
        sensor_active = sensor_active.replaceAll("&#39;","")
        let s_nb = row['n_batches_'+sensor_active.substring(1,sensor_active.length -1)];
        let s_ltr = row['last_time_received_'+sensor_active.substring(1,sensor_active.length -1)];
        buildchildtr(table,sensor_active.substring(1,sensor_active.length -1),s_nb,s_ltr)
          }
      }


    }

    mainDiv.append(table);
  return mainDiv;
};

function initTable() {
  $('#metadata_table').bootstrapTable({
    detailViewAlign : 'right',
    paginationParts: ['pageInfoshort', 'pageSize', 'pageList']
  })
  $('#index_table').bootstrapTable({
    detailViewAlign : 'right',
    paginationParts: ['pageInfoshort', 'pageSize', 'pageList']
  })
    $('#qc_table').bootstrapTable({
    detailViewAlign : 'right',
    paginationParts: ['pageInfoshort', 'pageSize', 'pageList']
  })
}




//create study related functions




function validatePassiveCheckbox(it, box){
  var selected_list = []

  var options = document.getElementById('id_sensor_list').options;
  for (let i = 0; i < options.length; i++) { 
    if (options[i].selected){
      selected_list.push(i)
    }
  }
  
  sensor_list_limited = document.getElementById('sensor_list_limited')
  for (let i=0;i < selected_list.length ; i++){
    sensor_list_limited.remove(selected_list[i]); 
  }

  var isPassive = document.getElementById("passive_form_checkbox").checked
  if (isPassive){
    show (it, box)
  }else{
    box.checked = false
    alert("Please choose sensors in Passive monitoring ")
  }
}

function show (it, box) {
  var vis = (box.checked) ? "block" : "none";
  document.getElementById(it).style.display = vis;
  if( it == "passive_monitoring_form"){
  if (!box.checked)
    document.getElementById("task_details_form").style.display = "none";

    document.getElementById("labelling_0").checked = true;
    

  }
}




function remove_task_form(id){
  array = id.split("_")
  if(array[1] != 0){
  const main = document.getElementById("task_details_form")
  const taskFormEl = document.getElementById("form-"+array[1])
  main.removeChild(taskFormEl)
  }
}

function add_task_form(){
  
  
  const main = document.getElementById("task_details_form")
  const totalTaskForms = document.getElementById("id_form-TOTAL_FORMS")
 
  const currentTaskForms = document.getElementsByClassName("task-formset mb-4")
  const currentFormCount = currentTaskForms.length //+ 1

  //add new task form

  const taskFormEl = document.getElementById('form-0').cloneNode(true)
  
  taskFormEl.setAttribute('class','task-formset mb-4')
  taskFormEl.setAttribute('id',`form-${currentFormCount}`)
  const regex = new RegExp('form-0-','g')
  taskFormEl.innerHTML  = taskFormEl.innerHTML.replace(regex,"form-"+currentFormCount+"-")
  taskFormEl.innerHTML  = taskFormEl.innerHTML.replace('id_0_remove_btn',"id_"+currentFormCount+"_remove_btn")
  totalTaskForms.setAttribute('value', currentFormCount + 1)
  
  main.appendChild(taskFormEl)
  const initialTaskForms = document.getElementById("id_form-INITIAL_FORMS")
  if (initialTaskForms.value != 0 ){
    document.getElementById("id_form-"+currentFormCount+"-task_name").value = ""
    document.getElementById("id_form-"+currentFormCount+"-task_preparation").value = ""
    document.getElementById("id_form-"+currentFormCount+"-task_duration").value = ""
    document.getElementById("id_form-"+currentFormCount+"-task_description").value = ""
    
  }
  if (currentFormCount> 0){
    document.getElementById("id_"+currentFormCount+"_remove_btn").disabled = false
  }
}

function show_task_form(){
  var radios = document.getElementsByName('active_labeling');
  
  for (var radio of radios)
  {
    
    if (radio.checked) {
      if(radio.value != 0){
        document.getElementById("task_details_form").style.display = "block";
        const addTaskBtn = document.getElementById("add-task")
        
        if (radio.value == 3){
          document.getElementById("labeling_sensor_list").style.display = "block";
        }
        
      }else if(radio.value == 0){
        
        const main = document.getElementById("task_details_form")
        const totalTaskForms = document.getElementById("id_form-TOTAL_FORMS")
        
        const currentTaskForms = document.getElementsByClassName("task-formset mb-4")
        
        if (currentTaskForms.length>1){
          for (count=1 ;count<=currentTaskForms.length;count++){
            const taskFormEl = document.getElementById("form-"+count)
            main.removeChild(taskFormEl)
            
          }
        }
        totalTaskForms.setAttribute('value',1);
        document.getElementById("labeling_sensor_list").style.display = "none";
        document.getElementById("task_details_form").style.display = "none";
      }
    }
  }
}



$(document).on('change', '.file-input', function() {


  var filesCount = $(this)[0].files.length;

  var textbox = $(this).prev();

  if (filesCount === 1) {
  var fileName = $(this).val().split('\\').pop();
  textbox.text(fileName);
  } else {
  textbox.text(filesCount + ' files selected');
  }
  });



// QC methods
// Toggle Select All Checkboxes
function toggleSelectAll(type, button) {
    // Get all checkboxes of the specified type
    const checkboxes = document.querySelectorAll(`.${type}-checkbox`);
    const shouldSelectAll = button.textContent === "Select All";
    checkboxes.forEach((checkbox) => {
        if (button.textContent == 'Select All'){
            checkbox.checked = true
        }else{
            checkbox.checked = false
        }
    });

    button.textContent = shouldSelectAll ? "Unselect All" : "Select All";
}

function sendCheckedFlagsToServer(study_name) {
    // Get all rows in the table
    const rows = document.querySelectorAll('tbody tr');

    // Collect data for checked flags
    const testCaseFlags = [];
    rows.forEach((row) => {
        // Get the test case ID
        const testCaseId = row.querySelector('#testcase_db_id').textContent.trim();
        // Check the state of admin and owner checkboxes
        const adminCheckbox = row.querySelector('.admin-checkbox');
        const ownerCheckbox = row.querySelector('.owner-checkbox');

        // Add the test case flag states to the array
        testCaseFlags.push({
            id: testCaseId,
            tested_by_admin: adminCheckbox.checked,
            tested_by_owner: ownerCheckbox.checked,
        });
    });
    // Convert test case flags to a JSON string
    const testCaseFlagsJSON = JSON.stringify(testCaseFlags);
    document.getElementById('testCaseFlagsInput').value = testCaseFlagsJSON;
    document.getElementById('testcaseForm').submit();
}


