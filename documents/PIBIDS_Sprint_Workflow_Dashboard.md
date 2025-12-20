
### **1. Product Overview**

The application serves as a sprint management middleware that sits between the **iTrack** ticketing system and the **PIBIDS team**. It allows Project Admins to convert raw ticket data into a structured 14-day Agile sprint plan, estimate team workload, and provide visibility to specific Lab Sections.

- **Sprint Cycle:** 14 Days (Starts Thursday, Ends Wednesday)1.
    
- **Primary Users:** Project Admins (Full Control)22.
    
- **Secondary Users:** Lab Sections (View-Only, filtered data)3.
    

---

### **2. Workflow Phase 1: Sprint Initialization (Import & Generate)**

_Occurs every 14 days on the morning of a new sprint._

Step 1: Data Import

The Project Admin uploads the latest iTrack_Extract.csv file into the dashboard.

Step 2: Automated Sprint Generation

The system automatically generates a draft for the "New Sprint" by processing data from three sources: the uploaded file, the previous sprint, and historical data.

- **Archiving:** The system takes the current sprint's data and appends it to the "Past Sprints" archive to maintain a permanent history4444.
    
- **Carryover Task Logic:** The system scans the previous sprint and identifies "Uncompleted Tasks."
    
    - _Definition:_ Any task where the status is **NOT** "Completed" and **NOT** "Canceled" is carried over to the new sprint55.
        
    - _Data Refresh:_ The system updates the status and priority of these carryover tasks using the fresh data from the imported `iTrack_Extract.csv`6.
        
    - _Effort Reset:_ The "Estimated Effort" field for carryover tasks is cleared (reset to blank) to require re-evaluation7.
        
- **New Task Identification:** The system identifies new tickets from the uploaded `iTrack_Extract.csv`.
    
    - _Definition:_ Tasks with a `Created On` date that is **after** the End Date of the previous sprint8888.
        
    - These tasks are appended to the new sprint draft.
        
- **Section Mapping:** The system automatically populates the "Section" field for every task by mapping it from the "Team" column in the iTrack export (e.g., "PIBIDS")9.
    

Step 3: Automated Priority Escalation (TAT)

The system analyzes the age of every task to highlight items at risk of missing their Turn Around Time (TAT). It automatically upgrades the CustomerPriority to 5 (High) if:

- **Incident (IR):** The task has been open for **0.8 days or more** (Approaching the 24-hour limit)10.
    
- **Service Request (SR):** The task has been open for **22 days or more** (Approaching the 2-sprint/28-day limit)11.
    
- **Project Request (PR):** No automatic escalation; managed manually by Admins12.
    

---

### **3. Workflow Phase 2: Sprint Planning (Annotate & Lock)**

_Occurs immediately after initialization._

The Admin Planning View

Project Admins are presented with an editable grid of the generated sprint draft.

Step 1: Effort Estimation

Admins manually enter the HoursEstimated for each task. This is a critical step as iTrack does not contain this data13131313.

Step 2: Capacity Validation (The 52-Hour Rule)

As Admins enter hours, the system calculates the total effort assigned to each team member (AssignedTo field).

- **Alert:** If a specific individual's total assigned effort exceeds **52 hours** (representing 65% capacity of a 2-week sprint), the system flags this as an overload to trigger resource leveling14141414.
    

Step 3: Plan Finalization

Admins review the automated priorities and capacity warnings. Once adjustments are made, they "Lock" the plan. This creates the official Current Sprint record15151515.

---

### **4. Workflow Phase 3: Monitoring (The Dashboard)**

_Continuous access during the sprint._

The application provides two distinct viewing experiences based on the user role:

**A. Project Admin View (Master Dashboard)**

- Admins see all tasks across all sections16.
    
- They can monitor "At Risk" items (those approaching TAT).
    
- They can track the "Days Open" metric against the target resolution times.
    
- They maintain the ability to update "Estimated Effort" if scope changes mid-sprint17.
    

**B. Lab Section View (Filtered Dashboard)**

- Users belonging to specific lab sections (e.g., Core Lab, Microbiology) see a read-only filtered view.
    
- **Logic:** A user from "Core Lab" will _only_ see rows where the `Section` column matches their department18181818.
    
- This reduces noise and allows teams to focus solely on their relevant tickets.
    

---

### **5. Workflow Phase 4: Sprint Closure**

_Occurs at the end of the 14-day cycle._

When the sprint period ends (Wednesday night), the cycle completes. The current state of the sprint (including which tasks were finished and which remain open) becomes the data source for the **next** Sprint Initialization phase, ensuring a continuous loop of history and planning19191919.