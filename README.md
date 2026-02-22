# Retail Demand Forecasting & Inventory Replenishment Planner

# PART A

## 1) Business Objective

**Primary objective:** Reduce **stockouts** (lost sales + customer dissatisfaction) while controlling **overstock** (cash blocked + holding cost + potential expiry/waste) by implementing a **SKU–Store daily forecast + reorder-point replenishment policy**.

**What success looks like in business terms:**

* Customers find products available when they want them (higher service level / fill rate).
* Working capital is used efficiently (lower excess inventory without increasing stockouts).
* Replenishment decisions are consistent, explainable, and scalable across store–SKU combinations.

---

## 2) North Star Metric

### Option 1: Service Level (Fill Rate) / Stockout Rate Reduction

**Definition**:
Fill rate measures how much true customer demand is fulfilled from available inventory.

```
Fill Rate = Units Sold / Estimated True Demand

```

**Summary:**

- Direct measure of product availability and customer experience
- Accurately captures stockout impact by correcting for censored sales
- Commonly used in retail and supply chain planning
- Naturally aligns with reorder point and safety stock policies

**Limitations:**

- Does not directly show financial impact
- Requires demand estimation during stockouts

---

### Option 2: Lost Sales Avoided (Units or ₹)

**Definition:**
Measures unmet demand recovered through improved inventory availability.

```
Lost Sales (Units) ≈ Forecasted Demand − Actual Sales (during stockouts)
Lost Revenue (₹) = Lost Units × Price
```

**Summary:**

- Quantifies financial impact of stockouts
- Intuitive and ROI-focused for leadership
- Helps prioritize high-impact SKUs and stores

**Limitations:**

- Highly dependent on forecast accuracy
- Influenced by price, promotions, and mix
- Less actionable for day-to-day replenishment decisions

---

## Chosen North Star Metric: Fill Rate (Service Level)

### Justification

Fill Rate is chosen because it best aligns operational decisions with customer experience and is directly controllable through inventory policy.

**Key reasons:**

- Directly addresses the stockout vs. overstock problem
- Actionable via reorder point and safety stock levers
- Stable and comparable across SKUs and stores
- Customer-centric and operationally meaningful
- Can be translated into **lost sales avoided (₹)** for executive reporting

---

## Recommended Metric Hierarchy

- **North Star:** Fill Rate (Service Level)
- **Executive Impact Metric:** Lost Sales Avoided (₹)
- **Operational Guardrails:** Overstock rate, DOH, holding cost

This structure ensures operational focus on availability, financial visibility for leadership, and transparent trade-offs between service level and inventory cost.

---

## 3) Supporting KPIs

### Forecast Quality (Demand Signal)

1. **WAPE (Weighted Absolute Percentage Error)**
   ```
   WAPE = Σ|Actual − Forecast| / ΣActual
   ```

   **Reason:** Stable across SKUs with varying volumes.

---

2. **MAPE (Mean Absolute Percentage Error)**
   ```
   MAPE = avg(|Actual − Forecast| / Actual)
   ```

   **Reason:** Easy to interpret, but unreliable for low-volume SKUs.

---

3. **Forecast Bias (Signed Error / Tracking Signal)**
   ```
   Bias = Σ(Forecast − Actual) / ΣActual
   ```

   **Reason:** Positive bias leads to overstock; negative bias causes stockouts.

---

### Availability / Stockout Outcomes

4. **Stockout Rate (Days)**
   ```
   Stockout Rate = Days with On-Hand = 0 / Total Days
   ```

   **Reason:** Simple operational indicator of availability issues.

---

5. **Fill Rate (North Star)**
   **Reason:** Measures how much true customer demand is fulfilled.

---

6. **Lost Sales Proxy (Units / ₹)**
   ```
   Lost Units = Σ(Forecasted Demand − Sales) on stockout days 
   Lost ₹ = Lost Units × Price
   ```

   **Reason:** Quantifies business impact of stockouts.

---

### Inventory Efficiency / Cost

7. **Days of Inventory on Hand (DOH)**
   ```
   DOH = On-hand Units / Avg Daily Forecasted Demand
   ```

   **Reason:** Core planning metric; easy to threshold.

---

8. **Overstock Rate**
   ```
   % of SKUs where DOH > Threshold
   ```

   **Reason:** Flags excess inventory risk (e.g., 30/45/60 days).

---

9. **Inventory Turns (Proxy)**
   ```
   Turns = Sales / Avg Inventory
   ```

   **Reason:** Indicates how efficiently inventory is moving.

---

10. **Inventory Turns (Proxy)**
      ```
      Turns = Sales / Avg Inventory
      ```

      **Reason:** Indicates how efficiently inventory is moving.
---

## 4) Scope Definition

### Forecasting Scope

- **forecasting horizon:** Next  **28 days (4 weeks)** .
- **Granularity:** **Store–SKU–Day** level demand forecasts
  - Roll-ups supported at **weekly**, **store**, and **category** levels for reporting and analysis

---

### Replenishment Planning Scope

- **Inventory Policy:** **Reorder Point (ROP) + Safety Stock**
  - Reorder quantity calculated to raise inventory up to a target level based on forecasted demand and service level
- **Lead Time Estimation:**
  - Derived from `purchase_orders.csv`
  - Uses **mean lead time** and **lead time variability** to size safety stock

---

## 5) Stakeholder Questions

These should guide what the dashboard and narrative must answer.

1. **Where are we most at risk of stockouts next 4 weeks?**

   Which store–SKU pairs, and on which days, with confidence/alerting thresholds?
2. **Where are we most likely to be overstocked—and why?**

   Is it slow-moving demand, forecast bias, long lead times, or poor ordering cadence?
3. **What should we reorder today/this week, and how much?**

   A clear recommended **order quantity** per SKU–store, based on ROP + safety stock.
4. **What service level are we targeting, and what’s the tradeoff?**

   How does moving from (say) 90% to 95% service level change inventory value?
5. **What’s the expected business impact of this plan?**

   Projected fill rate improvement + **lost sales avoided (₹)** and change in holding cost.
6. **How do promotions/holidays affect demand and replenishment needs?**

   Do we have uplift factors and do reorder suggestions reflect calendar events?
7. **Which SKUs need special handling due to shelf life?**

   Prevent excess ordering when DOH exceeds shelf life days.

---

## Forecasting Method Used

### Primary Method: Time-Series Demand Forecasting with Calendar & Business Signals

Demand is forecasted at the **Store–SKU–Day** level using a **time-series forecasting approach**, where historical sales patterns are combined with calendar and business drivers.

**Key components:**

- **Historical sales trends** (level, seasonality, day-of-week effects)
- **Calendar features** from `calendar.csv` (weekday, holidays, promotions)
- **Stockout-aware adjustment**:
  When on-hand inventory is zero, observed sales are treated as *censored*, and demand is inferred from the model rather than raw sales.

**Why this method was chosen:**

- Well-suited for short-term horizons (**28 days**)
- Interpretable and explainable for business stakeholders
- Scales efficiently across thousands of Store–SKU combinations
- Naturally supports replenishment logic (ROP + Safety Stock)

---

### Model Type (Conceptual)

- **Baseline:** Moving Average / Exponential Smoothing (per SKU–store)
- **Enhanced:** Time-series regression with calendar effects
  (trend + seasonality + promo/holiday flags)

---

### Output

- Daily demand forecasts per Store–SKU
- Aggregated forecasts at weekly, store, and category levels
- Forecast error metrics (WAPE, MAPE, Bias) used for validation

---

This approach balances **accuracy, interpretability, and operational usability**, making it suitable for inventory planning and replenishment decisions.

---

# PART B
