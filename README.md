# Retail Demand Forecasting & Inventory Replenishment Planner

## Project Overview
This project builds an end-to-end analytics and planning solution for a multi-store retail business facing two core problems:
- **Stockouts** → lost sales and poor customer experience
- **Overstock** → blocked working capital and higher holding costs

The solution combines **demand forecasting**, **inventory risk monitoring**, and a **replenishment policy** into an interactive Tableau dashboard that enables data-backed purchase decisions at the **store–SKU level**.


### North Star KPI
**Fill Rate (Service Level)**  
> Measures how much true customer demand is fulfilled.

Improving Fill Rate while controlling inventory levels is the primary objective of this project.

---


## Forecasting Methods Used
Forecasting is performed at the **Store–SKU–Day** level with a **28-day (4-week) horizon**.

### Demand Signal / Forecast Proxy
- **Baseline demand proxy**:  
  `avg_daily_demand` computed from the most recent 4–8 weeks
- Used consistently across:
  - Lost sales estimation
  - Fill rate computation
  - Replenishment planning inputs

### Forecast Accuracy Metrics
The following metrics are computed to evaluate forecast quality:
- **MAPE (Mean Absolute Percentage Error)**  
  Average daily percentage error (excluding zero-sales days)
- **WAPE (Weighted Absolute Percentage Error)**  
  Volume-weighted error, stable across high/low volume SKUs
- **Forecast Bias**  
  Signed error indicating over- or under-forecasting

These metrics are used for diagnostic purposes and decision confidence, not to tune models inside Tableau.

---

## End-to-End ETL Flow (How to Run)
### Step 1: Raw Data Inputs
- Copy following raw data files in /etl folder next to `etl_pipeline.py`
- run the following command to execute `etl_pipeline.py` 
   ```
   python .\etl_pipeline.py
   ```

## Curated output files generated
- The ETL pipeline will be generated the following output files in `/data/` folder

1. `fact_sales_store_sku_daily.csv`
   - date, store_id, sku_id
   - units_sold, revenue
   - promo_flag, holiday_flag, day_of_week

2. `fact_inventory_store_sku_daily.csv`
   - date, store_id, sku_id
   - on_hand_units
   - stockout_flag
   - days_of_cover

3. `replenishment_inputs_store_sku.csv`
   - avg_daily_demand
   - demand_std_dev
   - lead_time_days
   - service_level_target
   - safety_stock
   - reorder_point
   - recommended_order_qty

---


## Dashboard Tool Used
**Tableau Public**

### How to Open the Dashboard
1. Open **Tableau Public**
2. Load the packaged workbook (`RetailForecastReplenishment.twbx`) from `/dashboard/` folder
3. Navigate between views using dashboard tabs:
   - Executive Summary
   - Forecast Explorer
   - Inventory Risk Monitor
   - Replenishment Planner

**Note:**
1. All calculations and logic are embedded within the workbook.
2. Data is modeled using **Tableau Relationships (Logical Layer)**  
3. No physical joins are used
4. Relationships:
   - Sales ↔ Inventory on `(store_id, sku_id, date)`
   - Sales ↔ Replenishment Inputs on `(store_id, sku_id)`

This avoids grain mismatch and double counting.

---


## PART A - Framing 

[View Framing Document](final_story/PartA_Framing.pdf)
