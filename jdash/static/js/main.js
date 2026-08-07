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

let metadataTableScrollY = null;
let metadataTableScrollRestoreUntil = 0;

function captureMetadataTableScroll(event) {
  if (!event.target.closest('#metadata_table')) {
    return;
  }

  metadataTableScrollY = window.scrollY;
  metadataTableScrollRestoreUntil = Date.now() + 800;
}

function preserveMetadataTableScroll() {
  if (metadataTableScrollY === null) {
    return;
  }

  const scrollY = metadataTableScrollY;
  window.scrollTo(window.scrollX, scrollY);
  [0, 50, 150].forEach((delay) => {
    window.setTimeout(() => {
      window.scrollTo(window.scrollX, scrollY);
    }, delay);
  });
}

document.addEventListener('pointerdown', captureMetadataTableScroll, true);
document.addEventListener('mousedown', captureMetadataTableScroll, true);
document.addEventListener('touchstart', captureMetadataTableScroll, true);
document.addEventListener('click', function(event) {
  const metadataTable = event.target.closest('#metadata_table');
  if (!metadataTable) {
    return;
  }

  const link = event.target.closest('a');
  if (event.target.closest('.detail-icon') || (link && link.getAttribute('href') === '#')) {
    event.preventDefault();
  }
}, true);

window.addEventListener('scroll', function() {
  if (
    metadataTableScrollY !== null &&
    metadataTableScrollY > 0 &&
    Date.now() < metadataTableScrollRestoreUntil &&
    window.scrollY === 0
  ) {
    preserveMetadataTableScroll();
  }
}, true);

$(document).on(
  'expand-row.bs.table collapse-row.bs.table post-body.bs.table reset-view.bs.table',
  '#metadata_table',
  preserveMetadataTableScroll
);


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

function datetimeformatter(value) {
  if (!value || value === 'none') return value;

  const date = new Date(value);
  if (isNaN(date)) return value;

  const day = date.toLocaleDateString(undefined, { weekday: 'short' });  // "Fri"
  const month = date.toLocaleDateString(undefined, { month: 'short' });  // "Apr"
  const dayNum = date.getDate();  // 22
  const year = date.getFullYear();  // 2022

  const hours = String(date.getHours()).padStart(2, '0');  // 16
  const minutes = String(date.getMinutes()).padStart(2, '0');  // 54

  return `${day} ${month} ${dayNum} ${year} ${hours}:${minutes}`;
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

function formatBatchCount(value) {
  if (value === null || typeof value === 'undefined' || value === '' || value === 'none') {
    return 0;
  }

  const numericValue = Number(value);
  if (Number.isNaN(numericValue)) {
    return 0;
  }

  return Math.ceil(numericValue);
}

function buildchildtr(table,header,n_batches,last_time_received,row){
  const sensorCard = document.createElement('div');
  const freshness = getSensorFreshnessMeta(header, last_time_received, row);
  sensorCard.className = `study-subject-sensor-card ${freshness.cardClass}`;

  const sensorHeader = document.createElement('div');
  sensorHeader.className = 'study-subject-sensor-header';

  const sensorTitle = document.createElement('div');
  sensorTitle.className = 'study-subject-sensor-title';
  sensorTitle.textContent = getDashboardSensorDisplayLabel(header);

  const sensorBadgeGroup = document.createElement('div');
  sensorBadgeGroup.className = 'study-subject-sensor-badges';

  const batchesBadge = document.createElement('span');
  batchesBadge.className = 'study-subject-sensor-badge study-subject-sensor-badge--count';
  batchesBadge.textContent = `${formatBatchCount(n_batches)} batches`;

  sensorBadgeGroup.appendChild(batchesBadge);
  sensorHeader.appendChild(sensorTitle);
  sensorHeader.appendChild(sensorBadgeGroup);

  const sensorMeta = document.createElement('div');
  sensorMeta.className = 'study-subject-sensor-meta';
  sensorMeta.innerHTML = `
    <span class="study-subject-sensor-meta-label">last_time_received</span>
    <span class="study-subject-sensor-meta-value">${datetimeformatter(last_time_received)}</span>
  `;

  sensorCard.appendChild(sensorHeader);
  sensorCard.appendChild(sensorMeta);
  table.appendChild(sensorCard);
}

function parseStudyDaysValue(value) {
  if (value === null || typeof value === 'undefined') {
    return NaN;
  }

  const match = String(value).match(/-?\d+/);
  return match ? Number(match[0]) : NaN;
}

function parseSensorActivityMap(rawValue) {
  if (!rawValue) {
    return {};
  }

  const decoder = document.createElement('textarea');
  decoder.innerHTML = String(rawValue);
  const normalized = decoder.value.trim();
  if (!normalized) {
    return {};
  }

  try {
    const parsed = JSON.parse(normalized);
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch (error) {
    return {};
  }
}

function getSensorFreshnessMeta(sensorName, last_time_received, row) {
  const sensorActivityMap = parseSensorActivityMap(row && row.sensor_activity_map);
  const sensorState = sensorActivityMap[sensorName];
  const statusCode = sensorState ? sensorState.status_code : null;

  if (statusCode === 0) {
    return {
      label: 'No data',
      cardClass: 'study-subject-sensor-card--missing',
      badgeClass: 'study-subject-sensor-badge--missing',
    };
  }

  if (statusCode === 1) {
    return {
      label: 'Left study',
      cardClass: 'study-subject-sensor-card--left',
      badgeClass: 'study-subject-sensor-badge--left',
    };
  }

  if (statusCode === 2) {
    return {
      label: 'Active',
      cardClass: 'study-subject-sensor-card--active',
      badgeClass: 'study-subject-sensor-badge--active',
    };
  }

  if (statusCode === 3) {
    return {
      label: 'Completed',
      cardClass: 'study-subject-sensor-card--completed',
      badgeClass: 'study-subject-sensor-badge--completed',
    };
  }
    if (row && row.date_left_study && row.date_left_study !== 'none') {
    return {
      label: 'Left study',
      cardClass: 'study-subject-sensor-card--completed',
      badgeClass: 'study-subject-sensor-badge--completed',
    };
  }

  if (!last_time_received || last_time_received === 'none') {
    return {
        label: 'Stale',
      cardClass: 'study-subject-sensor-card--stale',
      badgeClass: 'study-subject-sensor-badge--stale',
    };
  }

  const parsed = new Date(last_time_received);
  if (isNaN(parsed)) {
    return {
      label: 'Received',
      cardClass: 'study-subject-sensor-card--unknown',
      badgeClass: 'study-subject-sensor-badge--unknown',
    };
  }

  const now = new Date();
  const daysSince = Math.floor((now - parsed) / (1000 * 60 * 60 * 24));
  if (daysSince >= 2) {
    return {
      label: 'Stale',
      cardClass: 'study-subject-sensor-card--stale',
      badgeClass: 'study-subject-sensor-badge--stale',
    };
  }

  return {
    label: 'Active',
    cardClass: 'study-subject-sensor-card--active',
    badgeClass: 'study-subject-sensor-badge--active',
  };
}


function formatDetailLabel(value) {
  if (!value) {
    return '';
  }

  return String(value).trim().toLowerCase();
}

function getDashboardSensorDisplayLabel(sensorName) {
  if (!sensorName) {
    return '';
  }

  const displayMap = window.wearableSensorDisplayMap || {};
  const wearableLabel = displayMap[String(sensorName).trim().toLowerCase()];
  if (wearableLabel) {
    return wearableLabel;
  }

  return formatDetailLabel(sensorName);
}

function parseDashboardSensorList(rawValue) {
  if (!rawValue) {
    return [];
  }

  if (Array.isArray(rawValue)) {
    return rawValue.map((item) => String(item).trim()).filter((item) => item !== '');
  }

  let normalized = String(rawValue).replaceAll("&#39;", "'");
  normalized = normalized.trim();
  if (!normalized || normalized === '[]') {
    return [];
  }

  try {
    const parsed = JSON.parse(normalized.replaceAll("'", '"'));
    if (Array.isArray(parsed)) {
      return parsed.map((item) => String(item).trim()).filter((item) => item !== '');
    }
  } catch (error) {
    // Fall back to legacy bracket/comma parsing below.
  }

  if (normalized.startsWith('[') && normalized.endsWith(']')) {
    normalized = normalized.substring(1, normalized.length - 1);
  }

  return normalized
    .split(',')
    .map((item) => item.replaceAll("'", "").trim())
    .filter((item) => item !== '');
}

function getDevicePlatformMeta(deviceId) {
  const normalizedDeviceId = String(deviceId || '').trim();
  const isAndroid = /[a-z]/.test(normalizedDeviceId);
  return {
    label: isAndroid ? 'Android' : 'iOS',
    iconClass: isAndroid ? 'fab fa-android' : 'fab fa-apple',
  };
}

function detailFormatter(index, row, element){ 
  
  
  var mainDiv = document.createElement("div");
  mainDiv.setAttribute('class','hiddenRow study-subject-detail-panel');

    var metaGrid = document.createElement('div');
    metaGrid.setAttribute('class','study-subject-meta-grid');
    const metaBits = [];
    if (row['device_id'] && row['device_id'] !== 'none') {
      const devicePlatform = getDevicePlatformMeta(row['device_id']);
      metaBits.push(`
        <span class="study-subject-device-platform" title="${devicePlatform.label}">
          <i class="${devicePlatform.iconClass}" aria-label="${devicePlatform.label}" role="img"></i>
        </span>
      `);
    }
    if (row['date_registered'] && row['date_registered'] !== 'none') {
      metaBits.push(`
        <span class="study-subject-meta-pill">
          <span class="study-subject-meta-label">date_registered</span>
          <span class="study-subject-meta-value">${datetimeformatter(row['date_registered'])}</span>
        </span>
      `);
    }
    if (row['date_left_study'] && row['date_left_study'] !== 'none') {
      metaBits.push(`
        <span class="study-subject-meta-pill study-subject-meta-pill--right">
          <span class="study-subject-meta-label">date_left_study</span>
          <span class="study-subject-meta-value">${datetimeformatter(row['date_left_study'])}</span>
        </span>
      `);
    }
    metaGrid.innerHTML = metaBits.join('');

    var sensorSection = document.createElement('div');
    sensorSection.setAttribute('class','study-subject-sensor-grid');

    if (row["appName"] == "ema"){
      var nb = row['n_batches_ema'];
      var ltr = row['last_time_received_ema'];
      buildchildtr(sensorSection,"ema",nb,ltr,row)
    }

    else{
      const dashboardSensors = parseDashboardSensorList(row['dashboard_sensor_list']);
      for (var i = 0, len = dashboardSensors.length; i < len; i++)  {
        const sensorName = dashboardSensors[i];
        let nb = row['n_batches_'+sensorName];
        let ltr = row['last_time_received_'+sensorName];
        buildchildtr(sensorSection, sensorName, nb, ltr, row)
      }
    }

    if (metaBits.length > 0) {
      mainDiv.append(metaGrid);
    }
    mainDiv.append(sensorSection);
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
    $('#study_audit_table').bootstrapTable({
    paginationParts: ['pageInfoshort', 'pageSize', 'pageList']
  })
}


window.operateEvents = {
}

function isMissingLastTimeValue(value) {
  return value === null || typeof value === 'undefined' || String(value).trim().toLowerCase() === 'none' || String(value).trim() === '';
}

function hideNoDataSensorButtons() {
  const $metadataTable = $('#metadata_table');
  if ($metadataTable.length === 0) {
    return;
  }

  const rows = $metadataTable.bootstrapTable('getData') || [];
  $metadataTable.find('tbody tr[data-index]').each(function() {
    const rowIndex = Number(this.getAttribute('data-index'));
    const row = rows[rowIndex];
    if (!row) {
      return;
    }

    const sensorButtons = this.querySelectorAll('td[data-field="sensor_info"] button[data-sensor-name]');
    sensorButtons.forEach((button) => {
      const sensorName = String(button.getAttribute('data-sensor-name') || '').trim();
      if (!sensorName) {
        return;
      }

      const lastTimeKey = sensorName === 'ema' ? 'last_time_received_ema' : `last_time_received_${sensorName}`;
      if (isMissingLastTimeValue(row[lastTimeKey])) {
        button.remove();
      }
    });
  });
}

$(document).on('post-body.bs.table', '#metadata_table', function() {
  hideNoDataSensorButtons();
});

document.addEventListener('DOMContentLoaded', function() {
  hideNoDataSensorButtons();
});

function extractSensorInfoTokens(cellValue) {
  if (!cellValue) {
    return [];
  }

  const temp = document.createElement('div');
  temp.innerHTML = String(cellValue);

  const buttonTexts = Array.from(temp.querySelectorAll('button'))
    .map((button) => (button.textContent || '').trim().toLowerCase())
    .filter((value) => value !== '');

  if (buttonTexts.length > 0) {
    return buttonTexts;
  }

  return (temp.textContent || '')
    .split(/[\s,;|/]+/)
    .map((value) => value.trim().toLowerCase())
    .filter((value) => value !== '');
}

window.sensorInfoFilterSearch = function(filterValue, cellValue) {
  if (!filterValue) {
    return true;
  }

  const target = String(filterValue).trim().toLowerCase();
  const tokens = extractSensorInfoTokens(cellValue);
  return tokens.includes(target);
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

function remove_wbdevice_form(id){
  array = id.split("_")
  if(array[1] != 0){
  const main = document.getElementById("wbdevice_details_form")
  const wbdeviceFormEl = document.getElementById("wbdevice_form-"+array[1])
  main.removeChild(wbdeviceFormEl)
  }
}
function add_wbdevice_form(){
  
  
  const main = document.getElementById("wbdevice_details_form")
  const totalWbDeviceForms = document.getElementById("id_form-TOTAL_FORMS")
 
  const currentWbDeviceForms = document.getElementsByClassName("wbdevice-formset mb-4")
  const currentFormCount = currentWbDeviceForms.length //+ 1

  //add new wbdevice form

  const wbdeviceFormEl = document.getElementById('wbdevice_form-0').cloneNode(true)
  
  wbdeviceFormEl.setAttribute('class','wbdevice-formset mb-4')
  wbdeviceFormEl.setAttribute('id',`wbdevice_form-${currentFormCount}`)
  const regex = new RegExp('form-0-','g')
  wbdeviceFormEl.innerHTML  = wbdeviceFormEl.innerHTML.replace(regex,"form-"+currentFormCount+"-")
  totalWbDeviceForms.setAttribute('value', currentFormCount + 1)
  
  main.appendChild(wbdeviceFormEl)
  const initialWbDeviceForms = document.getElementById("id_form-INITIAL_FORMS")
  if (initialWbDeviceForms.value != 0 ){
    document.getElementById("id_form-"+currentFormCount+"-device").value = ""
    
  }
}

function add_task_form(){
  
  
  const main = document.getElementById("task_details_form")
  const totalTaskForms = document.getElementById("id_form-TOTAL_FORMS")
 
  const currentTaskForms = document.getElementsByClassName("task-formset")
  const currentFormCount = currentTaskForms.length //+ 1
  //add new task form
  const templateTaskForm = currentTaskForms[0]
  if (!templateTaskForm) {
    return
  }

  const sourceFormId = templateTaskForm.id || "form-0"
  const sourceFormIndexMatch = sourceFormId.match(/form-(\d+)/)
  const sourceFormIndex = sourceFormIndexMatch ? sourceFormIndexMatch[1] : "0"
  const taskFormEl = templateTaskForm.cloneNode(true)
  
  taskFormEl.setAttribute('class','task-formset  border rounded p-3 mb-3')
  taskFormEl.setAttribute('id',`form-${currentFormCount}`)
  const regex = new RegExp('form-'+sourceFormIndex+'-','g')
  taskFormEl.innerHTML  = taskFormEl.innerHTML.replace(regex,"form-"+currentFormCount+"-")
  taskFormEl.innerHTML  = taskFormEl.innerHTML.replace("id_"+sourceFormIndex+"_remove_btn","id_"+currentFormCount+"_remove_btn")
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
      const removeBtn = document.getElementById("id_"+currentFormCount+"_remove_btn")
    if (removeBtn) {
      removeBtn.disabled = false
      removeBtn.style.display = ""
    }
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
        const testCaseId = row.querySelector('.testcase-db-id').value.trim();
        // Check the state of admin and owner checkboxes
        const adminCheckbox = row.querySelector('.admin-checkbox');
        const ownerCheckbox = row.querySelector('.owner-checkbox');
        const notesInput = row.querySelector('.qc-notes-data');

        // Add the test case flag states to the array
        testCaseFlags.push({
            id: testCaseId,
            tested_by_admin: adminCheckbox.checked,
            tested_by_owner: ownerCheckbox.checked,
            notes: notesInput ? JSON.parse(notesInput.value || "[]") : [],
        });
    });
    // Convert test case flags to a JSON string
    const testCaseFlagsJSON = JSON.stringify(testCaseFlags);
    document.getElementById('testCaseFlagsInput').value = testCaseFlagsJSON;
    document.getElementById('testcaseForm').submit();
}


let activeQcNotesRow = null;

function getQcNotesFromRow(row) {
    const notesInput = row ? row.querySelector('.qc-notes-data') : null;
    const rawValue = notesInput ? (notesInput.value || notesInput.textContent || '') : '';
    if (!rawValue) {
        return [];
    }

    try {
        const parsed = JSON.parse(rawValue);
        return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
        console.error('Unable to parse QC notes JSON', error);
        return [];
    }
}

function setQcNotesForRow(row, notes) {
    const notesInput = row ? row.querySelector('.qc-notes-data') : null;
    const serialized = JSON.stringify(notes);
    if (notesInput) {
        notesInput.value = serialized;
        notesInput.textContent = serialized;
    }

    const container = row ? row.querySelector('.qc-note-list') : null;
    renderQcNotesList(container, notes.slice(-3), {
        totalCount: notes.length,
        showSummary: notes.length > 3,
    });
}

function getCsrfToken() {
    const cookieValue = `; ${document.cookie}`;
    const parts = cookieValue.split('; csrftoken=');
    if (parts.length === 2) {
        return parts.pop().split(';').shift();
    }
    return '';
}

function notifyQcComment(testCaseId, commentText, timestamp) {
    const modal = document.getElementById('qcNotesModal');
    const notifyUrl = modal ? modal.dataset.notifyUrl : '';
    if (!notifyUrl) {
        return Promise.resolve();
    }

    return fetch(notifyUrl, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify({
            id: testCaseId,
            comment: commentText,
            timestamp: timestamp,
        }),
    }).then((response) => {
        if (!response.ok) {
            throw new Error(`QC comment notify failed: ${response.status}`);
        }
        return response.json();
    });
}

function renderQcNotesList(container, notes, options = {}) {
    if (!container) return;

    container.innerHTML = '';
    const totalCount = options.totalCount ?? notes.length;
    const showSummary = options.showSummary ?? false;

    if (!notes || notes.length === 0) {
        const emptyState = document.createElement('p');
        emptyState.className = 'qc-note-empty';
        emptyState.textContent = 'No notes yet.';
        container.appendChild(emptyState);
        return;
    }

    notes.forEach((note) => {
        const item = document.createElement('div');
        item.className = 'qc-note-item';

        const text = document.createElement('p');
        text.textContent = note.text || '';
        item.appendChild(text);

        if (note.user || note.timestamp) {
            const meta = document.createElement('small');
            meta.className = 'qc-note-meta';
            meta.textContent = [note.user || '', note.timestamp || ''].filter(Boolean).join(' · ');
            item.appendChild(meta);
        }

        container.appendChild(item);
    });

    if (showSummary && totalCount > notes.length) {
        const summary = document.createElement('p');
        summary.className = 'qc-note-empty';
        summary.textContent = 'Showing last 3 notes.';
        container.appendChild(summary);
    }
}

function openQcNotesModal(button) {
    activeQcNotesRow = button.closest('tr');
    if (!activeQcNotesRow) return;

    const modal = document.getElementById('qcNotesModal');
    const listContainer = modal.querySelector('.qc-modal-list');
    const input = document.getElementById('qcNoteInput');
    const notes = getQcNotesFromRow(activeQcNotesRow);
    renderQcNotesList(listContainer, notes, { totalCount: notes.length, showSummary: false });
    input.value = '';
    modal.classList.add('is-open');
    input.focus();
}

function closeQcNotesModal() {
    const modal = document.getElementById('qcNotesModal');
    if (modal) {
        modal.classList.remove('is-open');
    }
    activeQcNotesRow = null;
}

function appendQcNote() {
    if (!activeQcNotesRow) return;

    const modal = document.getElementById('qcNotesModal');
    const input = document.getElementById('qcNoteInput');
    const username = modal ? (modal.dataset.currentUser || '') : '';
    const text = (input.value || '').trim();

    if (!text) {
        return;
    }

    const now = new Date();
    const noteEntry = {
        text: text,
        user: username,
        timestamp: now.toLocaleString(),
    };
    const testCaseId = activeQcNotesRow.querySelector('.testcase-db-id')?.value?.trim();

    const notes = getQcNotesFromRow(activeQcNotesRow);
    notes.push(noteEntry);
    setQcNotesForRow(activeQcNotesRow, notes);

    const modalList = modal ? modal.querySelector('.qc-modal-list') : null;
    renderQcNotesList(modalList, notes, { totalCount: notes.length, showSummary: false });
    input.value = '';
    input.focus();

    if (testCaseId) {
        notifyQcComment(testCaseId, noteEntry.text, noteEntry.timestamp).catch((error) => {
            console.error(error);
        });
    }
}

document.addEventListener('click', (event) => {
    const modal = document.getElementById('qcNotesModal');
    if (modal && event.target === modal) {
        closeQcNotesModal();
    }
});

document.addEventListener('keydown', (event) => {
    const modal = document.getElementById('qcNotesModal');
    if (!modal || !modal.classList.contains('is-open')) {
        return;
    }

    if (event.key === 'Escape') {
        closeQcNotesModal();
    }

    if (event.key === 'Enter' && event.target && event.target.id === 'qcNoteInput') {
        event.preventDefault();
        appendQcNote();
    }
});



/***********************
 *  STUDY DEVICE + SENSOR CONFIG JS (NEW SCHEMA)
 *
 *  Uses:
 *   - devices formset (prefix="devices")
 *   - per-device sensor formsets (prefix="sensors-{i}")
 *
 *  Reads JSON from template:
 *   - {{ device_sensors_json|json_script:"device-sensors-json" }}
 *   - {{ resolution_json|json_script:"resolution-json" }}
 *   - {{ sampling_json|json_script:"sampling-json" }}
 *   - {{ unit_json|json_script:"unit-json" }}
 *
 *  IMPORTANT:
 *   - Multi-select shows available sensors for selected device using DeviceSensor mapping rows.
 *   - Each table row posts:
 *       sensors-{i}-{row}-device_sensor   (DeviceSensor.id)
 *       sensors-{i}-{row}-resolution      (ResolutionCatalog.id) [override; can be blank if you allow]
 *       sensors-{i}-{row}-sampling_rate   (SamplingRateCatalog.id)
 *       sensors-{i}-{row}-unit            (UnitCatalog.id)
 ***********************/

let deviceSensorsAll = [];
let catalogs = {  samplings: [], units: [] };

function readJsonScript(id) {
  const el = document.getElementById(id);
  if (!el) {
    console.error(`Missing JSON script tag: #${id}`);
    return null;
  }
  try {
    return JSON.parse(el.textContent);
  } catch (e) {
    console.error(`Invalid JSON in #${id}`, e, el.textContent);
    return null;
  }
}

/** Build <select> for catalog tables */
function buildSelect(name, options, selectedValue, className = "form-control") {
  const sel = document.createElement("select");
  sel.name = name;
  sel.className = className;

  options.forEach(o => {
    const opt = document.createElement("option");
    opt.value = String(o.id);
    opt.textContent = o.label ?? o.value ?? String(o.id);
    sel.appendChild(opt);
  });

  if (selectedValue != null && selectedValue !== "") sel.value = String(selectedValue);
  return sel;
}

function buildReadOnlyInput(name, value, displayValue, className = "form-control") {
  const wrapper = document.createDocumentFragment();

  const visibleInput = document.createElement("input");
  visibleInput.type = "text";
  visibleInput.className = className;
  visibleInput.value = displayValue ?? "";
  visibleInput.disabled = true;

  const hiddenInput = document.createElement("input");
  hiddenInput.type = "hidden";
  hiddenInput.name = name;
  hiddenInput.value = value != null ? String(value) : "";

  wrapper.appendChild(visibleInput);
  wrapper.appendChild(hiddenInput);
  return wrapper;
}

function formatWearableSensorDisplayLabel(value) {
  if (!value) {
    return "";
  }

  return String(value).trim().toLowerCase();
}
/** Map device_id -> DeviceSensor[] */
function deviceSensorsByDeviceMap(deviceSensors) {
  const map = new Map();
  deviceSensors.forEach(ds => {
    const key = String(ds.device_id);
    if (!map.has(key)) map.set(key, []);
    map.get(key).push(ds);
  });
  return map;
}

/** Fill the multi-select with DeviceSensor rows (value=DeviceSensor.id, label=sensor__label) */
function fillSensorMulti(multiEl, deviceSensorsForDevice) {
  multiEl.innerHTML = "";

  deviceSensorsForDevice.forEach(ds => {
    const opt = document.createElement("option");
    opt.value = String(ds.id); // DeviceSensor.id
    opt.textContent = formatWearableSensorDisplayLabel(ds.sensor__label) || `sensor ${ds.sensor_id}`;
    multiEl.appendChild(opt);
  });
}

function selectedDeviceSensorsInBlock(block) {
  return new Set(
    Array.from(
      block.querySelectorAll('.sensor-tbody [name$="-device_sensor"]')
    )
      .filter((input) => {
        const row = input.closest("tr");
        if (!row || row.style.display === "none") {
          return false;
        }
        const deleteInput = row.querySelector('input[type="checkbox"][name$="-DELETE"]');
        return !(deleteInput && deleteInput.checked);
      })
      .map((input) => String(input.value || ""))
      .filter((value) => value !== "")
  );
}

function syncSensorMultiAvailability(block) {
  const multi = block.querySelector("select.sensor-multi");
  if (!multi) return;

  const selectedIds = selectedDeviceSensorsInBlock(block);
  Array.from(multi.options).forEach((opt) => {
    const blocked = selectedIds.has(String(opt.value || ""));
    opt.hidden = blocked;
    opt.disabled = blocked;
    if (blocked) {
      opt.selected = false;
    }
  });
}

function makeExistingUnitReadOnly(block) {
  block.querySelectorAll('.sensor-tbody select[name$="-unit"]').forEach((selectEl) => {
    if (selectEl.dataset.readonlyApplied === "true") {
      return;
    }

    const selectedOption = selectEl.options[selectEl.selectedIndex];
    const hiddenInput = document.createElement("input");
    hiddenInput.type = "hidden";
    hiddenInput.name = selectEl.name;
    hiddenInput.value = selectEl.value;

    selectEl.removeAttribute("name");
    selectEl.disabled = true;
    selectEl.dataset.readonlyApplied = "true";

    if (selectedOption) {
      selectEl.title = selectedOption.textContent;
    }

    selectEl.insertAdjacentElement("afterend", hiddenInput);
  });
}

function filterCatalogBySensor(options, sensorId) {
  return (options || []).filter(o => String(o.sensor_id) === String(sensorId));
}

function filterCatalogById(options, selectedId) {
  if (selectedId == null || selectedId === "") return [];
  return (options || []).filter(o => String(o.id) === String(selectedId));
}

/**
 * Add selected DeviceSensor(s) as rows in the table.
 * Each row posts device_sensor (mapping id) + resolution/sampling/unit (override ids).
 * Defaults are pulled from mapping: default_resolution_id, default_sampling_rate_id, default_unit_id
 */
function addSelectedSensorsToTable(block) {
  const prefix = block.dataset.sensorPrefix; // e.g. "sensors-0"
  const totalEl = document.getElementById(`id_${prefix}-TOTAL_FORMS`);
  const tbody = block.querySelector(".sensor-tbody");
  const multi = block.querySelector("select.sensor-multi");
  const deviceSel = block.querySelector("select.device-select");

  if (!prefix || !totalEl || !tbody || !multi || !deviceSel) {
    console.error("Missing required elements in device block", { prefix, totalEl, tbody, multi, deviceSel });
    return;
  }

  // Must have device selected
  const deviceId = deviceSel.value;
  if (!deviceId) return;

  if (!Array.isArray(deviceSensorsAll)) {
    console.error("deviceSensorsAll is not an array. Check device-sensors-json reading.", deviceSensorsAll);
    return;
  }

  const dsById = new Map(deviceSensorsAll.map(ds => [String(ds.id), ds]));

  const selectedDeviceSensorIds = Array.from(multi.selectedOptions).map(o => String(o.value));
  if (selectedDeviceSensorIds.length === 0) return;

  // Prevent duplicates already added
  const existing = new Set(
    Array.from(tbody.querySelectorAll(`input[type="hidden"][name^="${prefix}-"][name$="-device_sensor"]`))
      .map(inp => String(inp.value))
  );

  let idx = parseInt(totalEl.value, 10);
  if (Number.isNaN(idx)) idx = 0;

  selectedDeviceSensorIds.forEach(deviceSensorId => {
    if (existing.has(deviceSensorId)) return;
  
    const dsRow = dsById.get(deviceSensorId);
    if (!dsRow) return;
  
    const sensorLabel = formatWearableSensorDisplayLabel(dsRow.sensor__label) || `sensor ${dsRow.sensor_id}`;
    const sensorId = dsRow.sensor_id;
  
    const sensorInput = document.createElement("input");
    sensorInput.type = "text";
    sensorInput.className = "form-control";
    sensorInput.value = sensorLabel;
    sensorInput.readOnly = true;
  
    const deviceSensorHidden = document.createElement("input");
    deviceSensorHidden.type = "hidden";
    deviceSensorHidden.name = `${prefix}-${idx}-device_sensor`;
    deviceSensorHidden.value = deviceSensorId;
  
    // const resolutionOptions = filterCatalogBySensor(catalogs.resolutions, sensorId);
    const samplingOptions = filterCatalogBySensor(catalogs.samplings, sensorId);
    const mappedUnitOptions = filterCatalogById(catalogs.units, dsRow.default_unit_id);
    const unitOptions = mappedUnitOptions.length
      ? mappedUnitOptions
      : filterCatalogBySensor(catalogs.units, sensorId);
  
    // const resSelect = buildSelect(
    //   `${prefix}-${idx}-resolution`,
    //   resolutionOptions,
    //   dsRow.default_resolution_id ?? null
    // );
  
    const srSelect = buildSelect(
      `${prefix}-${idx}-sampling_rate`,
      samplingOptions,
      dsRow.default_sampling_rate_id ?? null
    );
  
    const selectedUnit = unitOptions.find(
      option => String(option.id) === String(dsRow.default_unit_id ?? "")
    ) || unitOptions[0] || null;
  
    const idHidden = document.createElement("input");
    idHidden.type = "hidden";
    idHidden.name = `${prefix}-${idx}-id`;
  
    const del = document.createElement("input");
    del.type = "checkbox";
    del.name = `${prefix}-${idx}-DELETE`;
    del.style.display = "none";
  
    const tr = document.createElement("tr");
    tr.className = "sensor-row";
  
    const tdSensor = document.createElement("td");
    tdSensor.appendChild(idHidden);
    tdSensor.appendChild(sensorInput);
    tdSensor.appendChild(deviceSensorHidden);
  
    // const tdRes = document.createElement("td");
    // tdRes.appendChild(resSelect);
  
    const tdSR = document.createElement("td");
    tdSR.appendChild(srSelect);
  
    const tdUnit = document.createElement("td");
    tdUnit.appendChild(
      buildReadOnlyInput(
        `${prefix}-${idx}-unit`,
        selectedUnit ? selectedUnit.id : dsRow.default_unit_id ?? "",
        selectedUnit ? (selectedUnit.label ?? selectedUnit.value ?? String(selectedUnit.id)) : ""
      )
    );
  
    const tdActions = document.createElement("td");
    tdActions.appendChild(del);
  
    const deleteLink = document.createElement("a");
    deleteLink.href = "javascript:void(0)";
    deleteLink.className = "delete-row-btn me-2 mt-2";
    deleteLink.innerHTML = '<i class="fa fa-times-circle fa-lg text-danger" aria-hidden="true"></i>';
    tdActions.appendChild(deleteLink);
  
    tr.appendChild(tdSensor);
    //tr.appendChild(tdRes);
    tr.appendChild(tdSR);
    tr.appendChild(tdUnit);
    tr.appendChild(tdActions);
  
    tbody.appendChild(tr);
  
    existing.add(deviceSensorId);
    idx += 1;
  });

  totalEl.value = String(idx);
     syncSensorMultiAvailability(block);
}

/**
 * Refilter all device selects so each select hides devices selected in OTHER (visible) blocks.
 */
function refilterAllDeviceSelects() {
  const blocks = Array.from(document.querySelectorAll("#device-blocks .device-block"))
    .filter(b => b.style.display !== "none");

  const selects = blocks
    .map(b => b.querySelector("select.device-select"))
    .filter(Boolean);

  selects.forEach(sel => {
    const myValue = String(sel.value || "");
    const othersSelected = new Set(
      selects
        .filter(s => s !== sel)
        .map(s => String(s.value || ""))
        .filter(v => v !== "")
    );

    Array.from(sel.options).forEach(opt => {
      const v = String(opt.value || "");
      if (!v) {
        opt.hidden = false;
        opt.disabled = false;
        return;
      }
      const blocked = othersSelected.has(v) && v !== myValue;
      opt.hidden = blocked;
      opt.disabled = blocked;
    });
  });
}

/**
 * Add device block (dynamic)
 * - clones options from existing .device-select
 * - ensures nested sensors management inputs exist for sensors-{index}
 */
function addDeviceBlock() {
  const blocks = document.getElementById("device-blocks");
  const totalDevicesEl = document.getElementById("id_devices-TOTAL_FORMS");

  if (!blocks || !totalDevicesEl) {
    console.error("Missing #device-blocks or #id_devices-TOTAL_FORMS");
    return;
  }

  let deviceIndex = parseInt(totalDevicesEl.value, 10);
  if (Number.isNaN(deviceIndex)) deviceIndex = 0;

  const sensorPrefix = `sensors-${deviceIndex}`;

  const masterSelect = document.querySelector("#device-blocks .device-block select.device-select");
  if (!masterSelect) {
    console.error("No existing .device-select found to copy options from. Render at least one initial device form.");
    return;
  }

  // Collect selected devices in visible blocks
  const selectedIds = new Set(
    Array.from(document.querySelectorAll("#device-blocks .device-block"))
      .filter(b => b.style.display !== "none")
      .map(b => b.querySelector("select.device-select"))
      .filter(Boolean)
      .map(sel => String(sel.value || ""))
      .filter(v => v !== "")
  );

  // Build select
  const deviceSelect = document.createElement("select");
  deviceSelect.name = `devices-${deviceIndex}-device`;
  deviceSelect.id = `id_devices-${deviceIndex}-device`;
  deviceSelect.className = masterSelect.className; // "form-control device-select"
  deviceSelect.innerHTML = masterSelect.innerHTML;

  // Label
  const label = document.createElement("label");
  label.className = "text-primary";
  label.setAttribute("for", deviceSelect.id);
  label.textContent = "Device name";

  // Filter devices not already chosen
  Array.from(deviceSelect.options).forEach(opt => {
    const v = String(opt.value || "");
    if (!v) return;
    const blocked = selectedIds.has(v);
    opt.hidden = blocked;
    opt.disabled = blocked;
  });

  deviceSelect.value = "";

  // Create new block markup (same structure you already use)
  const block = document.createElement("div");
  block.className = "device-block card p-3 mb-3";
  block.dataset.devicePrefix = "devices";
  block.dataset.sensorPrefix = sensorPrefix;

  block.innerHTML = ` <div class="row g-3 ">
    <div class="d-flex align-items-center gap-3">
      <div class="device-select form-group flex-grow-1  mb-4" "></div>
      <div>
        <a type="button" class="btn btn-outline-danger btn-sm remove-device-bt">
          <i class="fa fa-trash fa-lg"></i>
        </a>
      </div>
    </div>

    <input type="hidden" name="${sensorPrefix}-TOTAL_FORMS" value="0" id="id_${sensorPrefix}-TOTAL_FORMS">
    <input type="hidden" name="${sensorPrefix}-INITIAL_FORMS" value="0" id="id_${sensorPrefix}-INITIAL_FORMS">
    <input type="hidden" name="${sensorPrefix}-MIN_NUM_FORMS" value="0" id="id_${sensorPrefix}-MIN_NUM_FORMS">
    <input type="hidden" name="${sensorPrefix}-MAX_NUM_FORMS" value="1000" id="id_${sensorPrefix}-MAX_NUM_FORMS">

    <div class="col-12 col-lg-5">
      <div class="form-group">
        <select class="form-control sensor-multi" multiple size="6"></select>
        <label class="text-primary">Wearable sensors for this device</label>
        <small class="text-muted">Select one or more sensors, then click Add</small>
      </div>
    </div>
    <div class="col-12 col-lg-2 d-flex align-items-start pt-lg-4">
      <button type="button" class="btn btn-success add-selected-sensors-btn" >
        Add
      </button></div>
    
        <div class="col-12 col-lg-5">
      <div class="table-responsive">
        <table class="table table-striped sensor-table mb-0">
          <thead>
            <tr>
              <th>Sensor</th>
              <th>Sampling rate</th>
              <th>Unit</th>
              <th style="width:140px;"></th>
            </tr>
          </thead>
          <tbody class="sensor-tbody"></tbody>
        </table>
      </div>
    </div>
    </div>
  `;

  block.querySelector(".device-select").appendChild(deviceSelect);
  block.querySelector(".device-select").appendChild(label);

  blocks.appendChild(block);
  totalDevicesEl.value = String(deviceIndex + 1);

  refilterAllDeviceSelects();
}

/** DOM Ready: read JSON + wire events */
document.addEventListener("DOMContentLoaded", () => {

  deviceSensorsAll = readJsonScript("device-sensors-json") || [];
  catalogs = {
    //resolutions: readJsonScript("resolution-json") || [],
    samplings: readJsonScript("sampling-json") || [],
    units: readJsonScript("unit-json") || [],
  };

  const byDevice = deviceSensorsByDeviceMap(deviceSensorsAll);

  // When device changes -> populate multi-select from mapping rows
  document.addEventListener("change", (e) => {
    if (!e.target.classList.contains("device-select")) return;

    const deviceId = e.target.value;
    const block = e.target.closest(".device-block");
    if (!block) return;

    const multi = block.querySelector("select.sensor-multi");
    if (!multi) {
      console.error("Missing .sensor-multi inside device-block");
      return;
    }

    const options = byDevice.get(String(deviceId)) || [];
    fillSensorMulti(multi, options);
  });

  // Populate for already-selected devices on load
  document.querySelectorAll(".device-block").forEach(block => {
    const dev = block.querySelector("select.device-select");
    const multi = block.querySelector("select.sensor-multi");
    if (!dev || !multi) return;
    if (!dev.value) return;
    fillSensorMulti(multi, byDevice.get(String(dev.value)) || []);
       syncSensorMultiAvailability(block);
    makeExistingUnitReadOnly(block);

  });
    refilterAllDeviceSelects();

  const deviceBlocks = document.querySelectorAll("#device-blocks .device-block");
  deviceBlocks.forEach((block, index) => {
    const removeBtn = block.querySelector(".remove-device-bt");
    if (!removeBtn) return;
    removeBtn.style.display = index === 0 ? "none" : "";
  });
});

/** Add selected sensors rows */
document.addEventListener("click", (e) => {
  const btn = e.target.closest(".add-selected-sensors-btn");
  if (!btn) return;

  const block = btn.closest(".device-block");
  if (!block) return;

  addSelectedSensorsToTable(block);
});

/** Delete row (mark DELETE and hide) */
document.addEventListener("click", (e) => {
  const delBtn = e.target.closest(".delete-row-btn");
  if (!delBtn) return;

  const tr = delBtn.closest("tr");
  if (!tr) return;

  const del = tr.querySelector('input[type="checkbox"][name$="-DELETE"]');
  if (del) {
    del.checked = true;
    tr.style.display = "none";
  } else {
    tr.remove();
  }
    const block = tr.closest(".device-block");
  if (block) {
    syncSensorMultiAvailability(block);
  }
});

/** Add device block button */
document.addEventListener("click", (e) => {
  const btn = e.target.closest("#add-device-btn");
  if (!btn) return;
  addDeviceBlock();
});

/** Remove device block safely (hide + disable + optional DELETE) */
document.addEventListener("click", (e) => {
  const rm = e.target.closest(".remove-device-bt");
  if (!rm) return;

  const block = rm.closest(".device-block");
  if (!block) return;

  const deviceSelect = block.querySelector("select.device-select");
  const m = deviceSelect?.name?.match(/^devices-(\d+)-device$/);
  const deviceIndex = m ? parseInt(m[1], 10) : null;

  // Create/mark DELETE for devices formset row (if can_delete=True)
  if (deviceIndex !== null) {
    let del = block.querySelector(`input[name="devices-${deviceIndex}-DELETE"]`);
    if (!del) {
      del = document.createElement("input");
      del.type = "checkbox";
      del.name = `devices-${deviceIndex}-DELETE`;
      del.style.display = "none";
      block.appendChild(del);
    }
    del.checked = true;
  }

  // Disable all inputs so Django ignores them
  block.querySelectorAll("input, select, textarea").forEach(el => {
    el.disabled = true;
  });

  // Hide instead of removing (keeps formset indices consistent)
  block.style.display = "none";

  refilterAllDeviceSelects();
});

/** Keep device uniqueness enforced */
document.addEventListener("change", (e) => {
  if (e.target && e.target.matches("#device-blocks select.device-select")) {
    refilterAllDeviceSelects();
  }
});

