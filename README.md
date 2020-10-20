<div align="center" markdown> 

<img src="https://hotpot.ai/designs/thumbnails/chrome-promotional-marquee/12.jpg"/>

# Merge Classes
  
<p align="center">

  <a href="#Overview">Overview</a> •
  <a href="#How-To-Run">How To Run</a> •
  <a href="#Explanation">Explanation</a>
</p>

[![](https://img.shields.io/badge/slack-chat-green.svg?logo=slack)](https://supervise.ly/slack) 
![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/supervisely-ecosystem/merge-classes)
[![views](https://dev.supervise.ly/public/api/v3/ecosystem.counters?repo=supervisely-ecosystem/merge-classes&counter=views&label=views)](https://supervise.ly)
[![used by teams](https://dev.supervise.ly/public/api/v3/ecosystem.counters?repo=supervisely-ecosystem/merge-classes&counter=runs&label=used%20by%20teams)](https://supervise.ly)
[![runs](https://dev.supervise.ly/public/api/v3/ecosystem.counters?repo=supervisely-ecosystem/merge-classes&counter=downloads&label=runs&123)](https://supervise.ly)

</div>

## Overview 

Sometimes class management (combining, mapping, handling class imbalance) can be tricky and time-consuming. App helps to merge classes with the same shapes.


## How To Run

### Step 1: Run from context menu of project / dataset

Go to "Context Menu" (images project or dataset) -> "Run App" -> "Transform" -> "Convert Class Shape"

<img src="https://i.imgur.com/9fFK4KG.png" width="600"/>

### Step 2:  Waiting until the app is started
Once app is started, new task appear in workspace tasks. Wait message `Application is started ...` (1) and then press `Open` button (2).

<img src="https://i.imgur.com/eeA4VMQ.png"/>

### Step 3: Define transformations

App contains 3 sections: information about input project, information about output and the list of all classes from input project. In column `CONVERT TO` there are dropdown lists in front of each class (row of the table). You have to define transformations for classes of interest. 

Default `remain unchanged` option is selected and means that class and all its objects will be copied without modification to a new project. Dropdown lists only contain allowed shapes (see <a href="#Overview">Overview</a>), for example `Rectangle` can not be transformed to `Polyline` or `Point`. 

<img src="https://i.imgur.com/mssxns3.png"/>

### Step 4: Press RUN button and wait

Press `Run` button. The progress bas will appear in `Output` section. Also you can monitor progress from tasks list of the current workspace.

<img src="https://i.imgur.com/rCNNniF.png" width="450"/>

App creates new project and it will appear in `Output` section. Result project name = original name + "(new shapes)" suffix.

<img src="https://i.imgur.com/79HnmH0.png" width="450"/>

### Step 5: App shuts down automatically

Even if app is finished, you can always use it as a history: open it from tasks list in `Read Only` mode to check Input project, list of applied transformations and Output project. 

## Explanation
    
- Result project name = original name + "(new shapes)" suffix

- Your data is safe: app creates new project with modified classes and objects. The original project remains unchanged

- Before converting `AnyShape` classes, you have to unpack it with another app - [Unpack Anyshape](https://github.com/supervisely-ecosystem/unpack-anyshape) 

- Colors of new classes will be generated randomly

- Note: transformation from raster (bitmap) to vector (polygon) will result in huge number of points. App performs approximation to reduce the number. That can lead to slight loss of accuracy at borders. Special settings to control approximation will be released in next version.
