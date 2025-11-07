# 🧭 JDash System Overview  
**By Biomarker Development Group, INM-7**

## 1. Introduction  

JDash is a Django-based web platform developed by the **Biomarker Development Group, INM-7**, for managing digital health studies conducted through **JTrack** mobile applications. It provides a unified interface to design, monitor, and manage behavioral and sensor-based research studies.

The system connects mobile app data with researcher-controlled dashboards. Its main goal is to simplify the lifecycle of digital studies — from **study setup and survey design** to **subject enrollment, progress monitoring, and data validation**.

## 2. System Architecture  

JDash follows a **modular Django MVC structure** integrated with a clean Bootstrap-based frontend and optional Plotly-Dash analytics components.

**Core Components:**
- **Backend:** Django framework managing user authentication, database models, and view rendering.  
- **Frontend:** HTML templates with Bootstrap, BootstrapTables, and AJAX for dynamic UI.  
- **Data Layer:** Centralized database storing study metadata, subjects, sensor configurations, and EMA survey definitions.  
- **Analytics Integration:** Optional Dash/Plotly apps embedded using Django templates for visualization.  
- **Mobile Link:** JTrack and JTrack-EMA mobile apps connect to JDash for study configuration and data upload.  

## 3. Main Modules  

### 3.1 Login Module  
Provides authentication for registered users such as investigators and administrators.  
- Users log in with a username and password.  
- A default demo user (`demouser`) is available for testing.  
- Footer links connect to Biomarker Development information, App Store badges, and collaboration contact details.  
- Once authenticated, users access the **Studies** interface as the entry point.

### 3.2 Studies Module  
Central hub for study management, showing all studies the user can access or create.  

**Interface Elements:**
- **Add Study Button:** Opens a form for creating a new study.  
- **Grid/List Toggle:** Allows switching between study card and list layouts.  
- **Search Bar:** Filters displayed studies.  

Each study card shows the title, description, and quick actions:
- **View:** Open study details.  
- **Edit:** Modify configuration or metadata.  
- **QC:** Access quality control section.

#### 3.2.1 Create New Study  
Accessible from **Add Study**.

**Form Sections:**
- **Study Metadata:** Name, duration, subject count, recording frequency, description.  
- **Sensors Configuration:**  
  - *Passive sensors* (e.g., accelerometer, application usage, barometer, gravity, gyroscope, location).  
  - *Active sensors* for specific triggered data capture.  
- **EMA (Ecological Momentary Assessment):**  
  - Checkbox to enable EMA surveys.  
  - Dropdown to select existing survey.  
  - JSON/ZIP upload options for EMA question and image definitions.  
- **Task Management:** Add or remove study tasks with preparation and duration times.  

#### 3.2.2 Study Details and Subjects View  
Displays overview panel and subject table.

**Left Panel – Study Information:**
- Duration, selected sensors, and associated EMA surveys.  
- Button for viewing **Survey details**.  

**Subjects Section:**
- Displays total and enrolled subject counts.  
- “Number of Subjects” dropdown defines how many new subject IDs to generate.  
- “Create” button adds new participant identifiers linked to the study.  
- “Remove” button deregisters specific subjects from the study.

**Right Panel – Subject Table:**
- Lists all study participants and related applications (main, EMA).  
- Columns include Subject ID, App Type, Duration, Sensor Information, and Status (e.g., *Instudy*, *Left study*).  
- Color-coded labels (red for inactive, yellow for active) provide a quick overview of status.

#### 3.2.3 Notifications and Study Closure  
**Notification Section:**
- Fields for message title and text.  
- Target selection (All IDs or Missing IDs).  
- “Send notification” button dispatches push notifications to participants’ devices via JTrack-EMA.

**Close Study Section:**
- “Close Study” button deactivates data collection and marks the study as completed.

### 3.3 Survey Module  
Manages EMA (Ecological Momentary Assessment) questionnaires linked to studies.

**Components:**
- **Survey List Page:** Displays existing surveys with title, study association, creation date, and actions (edit, clone, delete).  
- **Upload Section:** Allows importing survey definitions via JSON files.  
- **New Survey Button:** Creates a blank survey structure for manual question entry.

#### 3.3.1 Survey Details View  
Displays internal structure of an EMA survey.  
Each survey question is listed with metadata such as id, title, subText, questionType, category, frequency, and activation times.

Users can edit or delete questions using icons in the “actions” column.

#### 3.3.2 Edit Question Form  
Provides a complete definition for each question:

- **Sequence ID:** Ordering number in the survey.  
- **Type:** Expected answer type.  
- **Title and Description:** Main question and English translation.  
- **Category and Frequency:** Group and timing parameters.  
- **DeactivateOnAnswer / DeactivateOnDate:** Conditions to stop showing the question.  
- **Activate/Deactivate Question Lists:** Define dependencies between questions.  
- **ClockTime Settings:** Define when push notifications are triggered.  
- **Image URL / Link URL:** Optional visual or external reference content.

### 3.4 Analytics Module  
The Analytics tab  integrates visual dashboards through **django-plotly-dash**. It allows analysis of data collected from mobile apps, such as:

- Sensor activity over time  
- EMA response   
- Participant-level metrics  


**Workflow Summary:**
1. User logs in to JDash.  
2. Creates or opens a study.  
3. Defines study metadata and sensor/EMA configuration.  
4. Enrolls subjects.  
5. Associates or uploads surveys.  
6. Monitors progress and sends notifications.  
7. Optionally analyzes data through Analytics tab.

**End of JDash System Overview**  
