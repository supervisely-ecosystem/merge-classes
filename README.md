<div align="center" markdown> 

<img src="https://i.imgur.com/CdTLI9w.png"/>

# Merge Classes
  
<p align="center">

  <a href="#Overview">Overview</a> •
  <a href="#How-To-Run">How To Run</a> •
  <a href="#Notes">Notes</a>
</p>

[![](https://img.shields.io/badge/slack-chat-green.svg?logo=slack)](https://supervise.ly/slack) 
![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/supervisely-ecosystem/merge-classes)
[![views](https://dev.supervise.ly/public/api/v3/ecosystem.counters?repo=supervisely-ecosystem/merge-classes&counter=views&label=views)](https://supervise.ly)
[![used by teams](https://dev.supervise.ly/public/api/v3/ecosystem.counters?repo=supervisely-ecosystem/merge-classes&counter=runs&label=used%20by%20teams)](https://supervise.ly)
[![runs](https://dev.supervise.ly/public/api/v3/ecosystem.counters?repo=supervisely-ecosystem/merge-classes&counter=downloads&label=runs&123)](https://supervise.ly)

</div>

## Overview 

Sometimes class management (combining, mapping, handling class imbalance) can be tricky and time-consuming. This App helps to merge classes with the same shapes. Let's consider several cases:

1. **Map one or several classes to the existing one**: all objects will be assigned to destination class and the source class will be removed from project. Follow steps from (<a href="#How-To-Run">How To Run</a> section) 
2. **Map one or several classes to a new one**: first, you have to create new class (on `Project`->`Classes` page) and then follow steps from (<a href="#How-To-Run">How To Run</a> section).

Notes:
- Result project name = original name + "(merged classes)" suffix
- Your data is safe: app creates new project with modified classes and objects. The original project remains unchanged


## How To Run

### Step 1: Run from context menu of project

Go to "Context Menu" (images project) -> "Run App" -> "Transform" -> "Merge Classes"

<img src="https://i.imgur.com/9fFK4KG.png" width="600"/>

### Step 2:  Waiting until the app is started
Once app is started, new task appear in workspace tasks. Wait message `Application is started ...` (1) and then press `Open` button (2).

<img src="https://i.imgur.com/uo1xJUJ.png"/>

### Step 3: Define mapping

App contains 3 sections: information about input project, information about output and the list of all classes from input project. In column `CONVERT TO` there are dropdown lists in front of each class (row of the table). You have to define transformations for classes of interest. 

Default `remain unchanged` option is selected and means that class and all its objects will be copied without modification to a new project. Dropdown lists only contain allowed shapes (see <a href="#Overview">Overview</a>), for example `Rectangle` can not be transformed to `Polyline` or `Point`. 

<img src="https://i.imgur.com/L9MSbLd.png"/>

### Step 4: Press RUN button and wait

Press `Run` button. The progress bas will appear in `Output` section. Also you can monitor progress from tasks list of the current workspace.

<img src="https://i.imgur.com/rCNNniF.png" width="450"/>

App creates new project and it will appear in `Output` section. Result project name = original name + "(merged classes)" suffix

<img src="https://i.imgur.com/rmAzI1G.png" width="450"/>

### Step 5: App shuts down automatically

Even if app is finished, you can always use it as a history: open it from tasks list in `Read Only` mode to view all information about a task: Input project, mapping settings and Output project. 
