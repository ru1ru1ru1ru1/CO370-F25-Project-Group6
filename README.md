## 🚌 GO Transit Optimization Dataset

This repository contains data and code for our **GO Transit schedule optimization problem**, which aims to reduce system-wide passenger transfer waiting times through minor schedule adjustments.

---

### 📦 Data Sources

- **`GO-GTFS/`**: This folder contains the original [GTFS (General Transit Feed Specification)]data published by GO Transit.  
  You can find the latest version here:  
  [https://www.gotransit.com/en/partner-with-us/software-developers](https://www.gotransit.com/en/partner-with-us/software-developers)

  > 📌 We used the version published on **November 19**.

---

### 📊 Processed data

These files are derived from the GTFS data and serve as inputs or outputs of our optimization model:

- **`All-trips.csv`**  
  A selected list of trips relevant to our optimization scenarios.

- **`All-connections.csv`**  
  Structured list of feasible transfer connections (e.g., train-to-bus, bus-to-train), including passenger estimates and wait times.

- **`optimized_schedule_results.csv`**  
  The final output of our optimization model, listing the best schedules selected with Penalty = 60 when a connection is missed.

---

### 📁 Code and Analysis

- **`GO-optimizer.ipynb`**  
  Our optimization model that selects the best transfer connections and applies schedule shifts.

- **`analysis.ipynb`**  
  Scripts used to visualize and analyze optimization results (e.g., total waiting time saved, per-hub improvements).

- **`Diagrams/`**  
  Contains result visualizations used in our final report and presentation (e.g., histograms, bar charts, scatter plots).

- **`Input-output/`**  
  Intermediate files from our (human) data pipeline.

---

### 📜 Full Project Report

The full methodology, assumptions, results, and limitations are documented in our final report (see Learn Dropbox).
