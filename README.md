## GO Transit Optimization Dataset

This repository contains data used for the **GO Transit optimization problem**.

### Data Sources

- **`GO-GTFS/`**: This folder contains the original [GTFS (General Transit Feed Specification)]data published by GO Transit.  
  You can find the latest version here:  
  [https://www.gotransit.com/en/partner-with-us/software-developers](https://www.gotransit.com/en/partner-with-us/software-developers)

  > 📌 We used the version published on **November 19**.

### Processed Data

The following files contain filtered and structured data derived from the original GTFS feed:

- **`All-trips.csv`**: A selected list of trips relevant to our optimization scenarios.
- **`All-connections.csv`**: A selected list of viable transfer connections, extracted and processed for multi-leg trip planning.
- **`optimized_schedule_results.csv`**: The final output of our optimization model, listing the best schedules selected with Penalty = 60 when a connection is missed.

