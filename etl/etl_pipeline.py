import os
import sys
import subprocess
import logging
from pathlib import Path


# ============================================================
# LOGGER SETUP
# ============================================================
def setup_logger(logs_dir, log_file_name):
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / log_file_name

    logger = logging.getLogger("retail_etl")
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# ============================================================
# PROJECT ROOT DISCOVERY
# ============================================================
def find_project_root(logger=None):
    """
    Find project root by walking upward from script location and cwd.
    Preference is given to directories containing requirements.txt
    or multiple expected data files.
    """
    candidates = []

    try:
        candidates.append(Path(__file__).resolve().parent)
        logger.info("Using script location as root candidate")
    except Exception as exc:
        logger.warning(f"Unable to resolve __file__: {exc}")

    candidates.append(Path.cwd().resolve())
    logger.info("Using current working directory as root candidate")

    def score_dir(folder):
        try:
            names = {p.name for p in folder.iterdir()}
        except Exception:
            return 0

        score = 0
        if "requirements.txt" in names:
            score += 10

        expected_files = {
            "sales_daily.csv",
            "inventory_daily.csv",
            "products.json",
            "purchase_orders.csv",
            "calendar.csv",
            "stores.csv",
        }
        score += sum(1 for f in expected_files if f in names)
        return score

    best_dir = None
    best_score = -1

    for start in candidates:
        for parent in [start] + list(start.parents):
            s = score_dir(parent)
            if s > best_score:
                best_score = s
                best_dir = parent
            if s >= 12:
                logger.info(f"Strong project root identified: {parent}")
                return parent

    logger.info(f"Fallback project root selected: {best_dir}")

    return best_dir if best_dir else candidates[0]


# ============================================================
# FILE DISCOVERY
# ============================================================
def find_file(root, filename, logger=None):
    """
    Recursively find a file under root.
    Skips common generated/system folders.
    """
    skip_dirs = {
        "output", "logs", "__pycache__", ".git",
        ".venv", "venv", "env", ".mypy_cache"
    }

    try:
        for p in root.rglob(filename):
            if any(part in skip_dirs for part in p.parts):
                continue
            if p.is_file():
                logger.info(f"Found file '{filename}' at {p}")
                return p
    except Exception as exc:
        logger.error(f"Error while searching for {filename}: {exc}", exc_info=True)

    logger.warning(f"File not found: {filename}")
    return None

# This function builds the FOUND_FILES dictionary based on the file paths discovered in the configuration.
def build_found_files(config, logger):
    """
    Build FOUND_FILES dict from discovered config file paths.
    """
    found = {
        "sales": config.sales_file,
        "inventory": config.inventory_file,
        "products": config.products_file,
        "purchase_orders": config.purchase_orders_file,
        "calendar": config.calendar_file,
        "stores": config.stores_file,
    }

    missing = [k for k, v in found.items() if v is None]
    if missing:
        logger.error("Missing required file paths for: %s", missing)
        raise FileNotFoundError("Missing required files: " + ", ".join(missing))

    return found

# ============================================================
# DIRECTORY CREATION
# ============================================================
def ensure_dirs(dirs, logger=None):
    for d in dirs:
        try:
            Path(d).mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured directory exists: {d}")
        except Exception as exc:
            logger.error(f"Failed to create directory {d}: {exc}", exc_info=True)
            raise

# ============================================================
# BUILD PATHS DICT
# ============================================================

# This function builds the PATHS dictionary based on the provided configuration.
def build_paths(config):
    """
    Build PATHS dict used by the pipeline.
    """
    return {
        "output": config.output_dir,
        "plots": config.plots_dir,
        "logs": config.logs_dir
    }


# ============================================================
# INSTALL REQUIRED PACKAGES
# ============================================================
def install_packages(requirements_path, logger=None):
    if requirements_path and requirements_path.exists():
        try:
            logger.info(f"Installing dependencies from {requirements_path}")
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "-r", str(requirements_path)]
            )
            logger.info("Dependency installation completed successfully")
        except subprocess.CalledProcessError as exc:
            logger.error("Dependency installation failed", exc_info=True)
            raise
    else:
        logger.warning("requirements.txt not found. Skipping dependency installation.")


# ============================================================
# CONFIGURATION
# ============================================================
class PipelineConfig:
    def __init__(self):
        # Temporary logger for bootstrap
        bootstrap_logger = logging.getLogger("bootstrap")
        bootstrap_logger.addHandler(logging.StreamHandler(sys.stdout))
        bootstrap_logger.setLevel(logging.INFO)

        # Discover project root
        self.project_root = find_project_root(bootstrap_logger)

        # Directories
        self.output_dir = self.project_root / "data"
        self.logs_dir = self.project_root / "logs"
        self.plots_dir = self.output_dir / "plots"

        # Logger (real)
        self.log_file_name = "retail_demand_forecasting.log"
        self.logger = setup_logger(self.logs_dir, self.log_file_name)

        self.logger.info("Pipeline configuration initialization started")
        self.logger.info(f"Project root resolved to: {self.project_root}")

        # Discover raw files
        self.sales_file = find_file(self.project_root, "sales_daily.csv", self.logger)
        self.inventory_file = find_file(self.project_root, "inventory_daily.csv", self.logger)
        self.products_file = find_file(self.project_root, "products.json", self.logger)
        self.purchase_orders_file = find_file(self.project_root, "purchase_orders.csv", self.logger)
        self.calendar_file = find_file(self.project_root, "calendar.csv", self.logger)
        self.stores_file = find_file(self.project_root, "stores.csv", self.logger)

        # Check that all required files were found
        required = {
            "sales_daily.csv": self.sales_file,
            "inventory_daily.csv": self.inventory_file,
            "products.json": self.products_file,
            "purchase_orders.csv": self.purchase_orders_file,
            "calendar.csv": self.calendar_file,
            "stores.csv": self.stores_file,
        }

        missing = [k for k, v in required.items() if v is None]
        if missing:
            self.logger.error("Missing required raw files:")
            for f in missing:
                self.logger.error(f" - {f}")
            raise FileNotFoundError(
                "Missing required raw file(s):\n- " + "\n- ".join(missing)
            )

        # Output filenames
        self.out_fact_sales = "fact_sales_store_sku_daily.csv"
        self.out_fact_inventory = "fact_inventory_store_sku_daily.csv"
        self.out_replenishment = "replenishment_inputs_store_sku.csv"

        # requirements.txt
        self.required_library_path = find_file(self.project_root, "requirements.txt", self.logger)

        # Windows
        self.demand_window_days = 56
        self.cover_window_days = 28

        self.logger.info("Pipeline configuration initialized successfully")

# ============================================================
# THIRD-PARTY IMPORTS (after install step)
# ============================================================
import logging
import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

# Utility function to print a banner in logs
def log_banner(logger, title):
    """
    Prints a readable section header using the logger.
    (Logger handlers will print to console and log file in the same format.)
    """
    line = "=" * 78
    logger.info("")
    logger.info(line)
    logger.info(title)
    logger.info(line)

# Utility function to read CSV safely and drop unnamed columns
def read_csv_safely(path, logger, **kwargs):
    """
    Read CSV and drop accidental 'Unnamed' columns (often created by trailing commas).
    """
    try:
        logger.info("Reading CSV: %s", path)
        df = pd.read_csv(path, **kwargs)

        # Remove any extra unnamed columns
        unnamed_cols = [c for c in df.columns if str(c).lower().startswith("unnamed")]
        if unnamed_cols:
            logger.warning("Dropping unnamed columns: %s", unnamed_cols)
            df = df.drop(columns=unnamed_cols)

        return df

    except FileNotFoundError:
        logger.error("CSV file not found: %s", path)
        raise
    except Exception as exc:
        logger.exception("Failed to read CSV: %s | Error: %s", path, exc)
        raise


# Utility function to read JSON safely
def read_json_safely(path, logger):
    """
    Read JSON safely.
    """
    try:
        logger.info("Reading JSON: %s", path)
        return pd.read_json(path)
    except FileNotFoundError:
        logger.error("JSON file not found: %s", path)
        raise
    except Exception as exc:
        logger.exception("Failed to read JSON: %s | Error: %s", path, exc)
        raise

# Utility function to standardize ID columns by stripping spaces and converting to uppercase
def standardize_ids(df, cols, logger=None):
    """
    Standardize ID columns: strip spaces and convert to uppercase.
    """
    try:
        for col in cols:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().str.upper()
        return df
    except Exception as exc:
        if logger:
            logger.exception("Failed to standardize ID columns %s | Error: %s", cols, exc)
        raise

# Utility function to normalize category columns to lowercase snake_case
def normalize_category(series):
    """
    Normalize category values to lowercase snake_case.
    Example: 'Home Care' -> 'home_care'
    """
    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_", regex=True)
    )

# Utility function to coerce datetime columns safely
def coerce_datetime(df, col, logger=None):
    """
    Convert a column to datetime safely.
    Invalid values become NaT (not a time).
    """
    try:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
        return df
    except Exception as exc:
        if logger:
            logger.exception("Failed to convert datetime for column '%s' | Error: %s", col, exc)
        raise

# Utility function to create a complete daily grid for each store-SKU combination
def ensure_complete_daily_grid(df, date_col, key_cols, value_cols, fill_value, logger=None):
    """
    Ensure every store-SKU has a continuous daily series.
    This is intentionally written in a very readable way.

    How it works:
    1) Determine global min/max date
    2) For each store-sku group, reindex on full date range
    3) Fill missing values with fill_value
    """
    try:
        df = df.copy()
        df = coerce_datetime(df, date_col, logger)

        min_date = df[date_col].min()
        max_date = df[date_col].max()

        if pd.isna(min_date) or pd.isna(max_date):
            # If date column is broken, fail early with a clear message
            raise ValueError("Date column contains no valid dates after parsing.")

        all_dates = pd.date_range(min_date, max_date, freq="D")

        if logger:
            logger.info(
                "Creating complete daily grid | %s to %s | keys=%s",
                str(min_date.date()), str(max_date.date()), key_cols
            )

        out_parts = []
        grouped = df.groupby(key_cols, dropna=False)

        for keys, g in grouped:
            g = g.sort_values(date_col).set_index(date_col)

            # Reindex to full daily range
            g = g.reindex(all_dates)

            # Fill value columns
            for vc in value_cols:
                if vc in g.columns:
                    g[vc] = g[vc].fillna(fill_value)

            # Put key cols back
            if not isinstance(keys, tuple):
                keys = (keys,)
            for i, kc in enumerate(key_cols):
                g[kc] = keys[i]

            g = g.reset_index().rename(columns={"index": date_col})
            out_parts.append(g)

        out = pd.concat(out_parts, ignore_index=True)
        return out

    except Exception as exc:
        if logger:
            logger.exception("Failed to create complete daily grid | Error: %s", exc)
        raise
		
# ============================================================
# OUTLIER FLAGGING + BOXPLOT (SIMPLIFIED)
# ============================================================

# This is a simple implementation of outlier detection using the IQR method.
def add_outlier_flag_iqr_by_group(df, group_cols, value_col, flag_col, logger=None):
    """
    Flag outliers using IQR rule within each group.
    Outlier rule:
      value < Q1 - 1.5*IQR OR value > Q3 + 1.5*IQR
    """
    try:
        df = df.copy()

        q1 = df.groupby(group_cols)[value_col].transform(lambda s: s.quantile(0.25))
        q3 = df.groupby(group_cols)[value_col].transform(lambda s: s.quantile(0.75))
        iqr = q3 - q1

        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr

        df[flag_col] = (df[value_col] < lower) | (df[value_col] > upper)

        if logger:
            logger.info("Outlier flag added: %s (based on %s)", flag_col, value_col)

        return df

    except Exception as exc:
        if logger:
            logger.exception("Failed outlier detection | Error: %s", exc)
        raise

# This function saves a boxplot of the specified value column to the given path.
def save_boxplot(df, value_col, title, out_path, logger=None):
    """
    Save a boxplot image to file.
    """
    try:
        
        out_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info("Saving boxplot: %s", out_path)

        plt.figure(figsize=(12, 5))
        sns.boxplot(x=df[value_col].dropna())
        plt.title(title)
        plt.xlabel(value_col)
        plt.tight_layout()
        plt.savefig(out_path)
        plt.close()

        logger.info("Boxplot saved successfully: %s", out_path)

    except Exception as exc:
        logger.exception("Failed to save boxplot | Error: %s", exc)
        raise

# ============================================================
# LOAD RAW DATA (USING FOUND_FILES DICT)
# ============================================================

# This function loads all required datasets from the file paths discovered in FOUND_FILES.
def load_raw_datasets(found_files, logger):
    """
    Load all required datasets from discovered file paths.
    found_files should contain absolute paths.
    """
    try:
        log_banner(logger, "Loading Raw Datasets")

        sales = read_csv_safely(found_files["sales"], logger)
        inventory = read_csv_safely(found_files["inventory"], logger)
        calendar = read_csv_safely(found_files["calendar"], logger)
        purchase_orders = read_csv_safely(found_files["purchase_orders"], logger)
        stores = read_csv_safely(found_files["stores"], logger)
        products = read_json_safely(found_files["products"], logger)

        logger.info("Raw datasets loaded successfully")
        return sales, inventory, products, calendar, purchase_orders, stores

    except KeyError as exc:
        logger.error("Missing key in FOUND_FILES: %s", exc)
        raise
    except Exception as exc:
        logger.exception("Failed to load raw datasets | Error: %s", exc)
        raise


# ============================================================
# CLEANING & STANDARDIZATION (SIMPLIFIED)
# ============================================================

# Function to clean and standardize the calendar dataset
def clean_calendar(calendar, logger):
    try:
        logger.info("Cleaning calendar")
        calendar = calendar.copy()
        calendar = coerce_datetime(calendar, "date", logger)

        for col in ["day_of_week", "is_weekend", "promo_flag", "holiday_flag"]:
            if col in calendar.columns:
                calendar[col] = pd.to_numeric(calendar[col], errors="coerce").fillna(0).astype(int)

        calendar = calendar.drop_duplicates(subset=["date"]).sort_values("date")
        return calendar

    except Exception as exc:
        logger.exception("Failed to clean calendar | Error: %s", exc)
        raise

# Function to clean and standardize the stores dataset
def clean_stores(stores, logger):
    try:
        logger.info("Cleaning stores")
        stores = stores.copy()
        stores = standardize_ids(stores, ["store_id"], logger)

        if "region" in stores.columns:
            stores["region"] = stores["region"].astype(str).str.strip().str.upper()

        if "city_tier" in stores.columns:
            stores["city_tier"] = pd.to_numeric(stores["city_tier"], errors="coerce")

        if "store_size" in stores.columns:
            stores["store_size"] = stores["store_size"].astype(str).str.strip().str.upper()

        stores = stores.drop_duplicates(subset=["store_id"])
        return stores

    except Exception as exc:
        logger.exception("Failed to clean stores | Error: %s", exc)
        raise

# Function to clean and standardize the products dataset
def clean_products(products, logger):
    try:
        logger.info("Cleaning products")
        products = products.copy()
        products = standardize_ids(products, ["sku_id"], logger)

        if "category" in products.columns:
            products["category"] = normalize_category(products["category"])

        for col in ["price", "cost", "shelf_life_days", "moq_units"]:
            if col in products.columns:
                products[col] = pd.to_numeric(products[col], errors="coerce")

        return products

    except Exception as exc:
        logger.exception("Failed to clean products | Error: %s", exc)
        raise

# Function to clean and standardize the purchase orders dataset
def clean_purchase_orders(po, logger):
    try:
        logger.info("Cleaning purchase orders")
        po = po.copy()
        po = standardize_ids(po, ["po_id", "store_id", "sku_id"], logger)

        po = coerce_datetime(po, "order_date", logger)
        po = coerce_datetime(po, "expected_receipt_date", logger)

        for col in ["order_qty", "lead_time_days"]:
            if col in po.columns:
                po[col] = pd.to_numeric(po[col], errors="coerce")

        # Deduplicate by po_id
        if "po_id" in po.columns:
            po = po.drop_duplicates(subset=["po_id"], keep="first")

        # Infer lead_time_days if missing and dates exist
        if "lead_time_days" in po.columns:
            missing = po["lead_time_days"].isna()
            if missing.any() and {"order_date", "expected_receipt_date"}.issubset(po.columns):
                inferred = (po.loc[missing, "expected_receipt_date"] - po.loc[missing, "order_date"]).dt.days
                po.loc[missing, "lead_time_days"] = inferred

        return po

    except Exception as exc:
        logger.exception("Failed to clean purchase orders | Error: %s", exc)
        raise

# Function to clean and standardize the sales dataset, merging calendar flags and ensuring complete daily grid
def clean_sales(sales, calendar, logger):
    try:
        logger.info("Cleaning sales")
        sales = sales.copy()
        sales = standardize_ids(sales, ["store_id", "sku_id"], logger)
        sales = coerce_datetime(sales, "date", logger)

        # Aggregate duplicates by summing numeric columns
        numeric_cols = [c for c in sales.columns if c not in ["date", "store_id", "sku_id"]]
        agg = {c: "sum" for c in numeric_cols}
        sales = sales.groupby(["date", "store_id", "sku_id"], as_index=False).agg(agg)

        if "units_sold" in sales.columns:
            sales["units_sold"] = pd.to_numeric(sales["units_sold"], errors="coerce").fillna(0)

        # Ensure calendar-derived columns ALWAYS exist
        for col in ["day_of_week", "promo_flag", "holiday_flag"]:
            if col not in sales.columns:
                logger.warning("Calendar column '%s' missing in sales. Filling with 0.", col)   
                sales[col] = 0
            else:
                sales[col] = pd.to_numeric(sales[col], errors="coerce").fillna(0).astype(int)        
        

        # Fill missing dates as 0 sales
        sales = ensure_complete_daily_grid(
            sales,
            date_col="date",
            key_cols=["store_id", "sku_id"],
            value_cols=["units_sold"],
            fill_value=0.0,
            logger=logger
        )

        return sales

    except Exception as exc:
        logger.exception("Failed to clean sales | Error: %s", exc)
        raise

# Function to clean and standardize the inventory dataset
def clean_inventory(inventory, logger):
    try:
        logger.info("Cleaning inventory")
        inventory = inventory.copy()
        inventory = standardize_ids(inventory, ["store_id", "sku_id"], logger)
        inventory = coerce_datetime(inventory, "date", logger)

        if "on_hand_close" in inventory.columns:
            inventory["on_hand_close"] = pd.to_numeric(inventory["on_hand_close"], errors="coerce")

        # Keep last snapshot per day
        inventory = inventory.sort_values(["date"]).drop_duplicates(
            subset=["date", "store_id", "sku_id"], keep="last"
        )

        # Forward fill within store-sku, then 0
        inventory = inventory.sort_values(["store_id", "sku_id", "date"])
        inventory["on_hand_close"] = inventory.groupby(["store_id", "sku_id"])["on_hand_close"].ffill().fillna(0)

        inventory = ensure_complete_daily_grid(
            inventory,
            date_col="date",
            key_cols=["store_id", "sku_id"],
            value_cols=["on_hand_close"],
            fill_value=0.0,
            logger=logger
        )

        return inventory

    except Exception as exc:
        logger.exception("Failed to clean inventory | Error: %s", exc)
        raise
    
# ============================================================
# CURATED OUTPUT BUILDERS (MISSING METHODS ADDED)
# ============================================================

# Function to build the fact_sales_store_sku_daily dataset by merging sales with product info and calculating revenue and margin proxy
def build_fact_sales(sales, logger):
    """
    Output 1: fact_sales_store_sku_daily.csv
    Required columns:
      date, store_id, sku_id, units_sold, revenue, margin_proxy,
      promo_flag, holiday_flag, day_of_week
    """
    try:
        logger.info("Building fact_sales_store_sku_daily")

        required_cols = [
            "date", "store_id", "sku_id",
            "units_sold", "revenue", "margin_proxy",
            "promo_flag", "holiday_flag", "day_of_week"
        ]

        missing = [c for c in required_cols if c not in sales.columns]
        if missing:
            raise ValueError(f"Missing required columns in sales data: {missing}")
        
        df = sales[required_cols].copy()

        df["units_sold"] = pd.to_numeric(df["units_sold"], errors="coerce").fillna(0)
        df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce").fillna(0)
        df["margin_proxy"] = pd.to_numeric(df["margin_proxy"], errors="coerce").fillna(0)

        
        # Calendar flags must be integers
        for col in ["promo_flag", "holiday_flag", "day_of_week"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

        logger.info("fact_sales_store_sku_daily built successfully")
        return df

    except Exception as exc:
        logger.exception("Failed to build fact sales | Error: %s", exc)
        raise

# Function to build the fact_inventory_store_sku_daily dataset by merging inventory with sales to calculate stockout flags and days of cover
def build_fact_inventory(inventory, sales, config, logger):
    """
    Output 2: fact_inventory_store_sku_daily.csv
    Required columns:
      date, store_id, sku_id, on_hand_units, stockout_flag, days_of_cover
    days_of_cover = on_hand_units / avg_daily_demand_4w
    """
    try:
        logger.info("Building fact_inventory_store_sku_daily")

        inventory = inventory.copy()
        sales = sales.copy()

        # Rename inventory close to on_hand_units
        if "on_hand_close" in inventory.columns:
            inventory["on_hand_units"] = pd.to_numeric(inventory["on_hand_close"], errors="coerce").fillna(0)
        elif "on_hand_units" in inventory.columns:
            inventory["on_hand_units"] = pd.to_numeric(inventory["on_hand_units"], errors="coerce").fillna(0)
        else:
            raise ValueError("Inventory data missing on_hand_close/on_hand_units column")

        max_date = sales["date"].max()
        start = max_date - pd.Timedelta(days=config.cover_window_days - 1)

        demand_4w = (
            sales.loc[(sales["date"] >= start) & (sales["date"] <= max_date)]
            .groupby(["store_id", "sku_id"], as_index=False)["units_sold"]
            .mean()
            .rename(columns={"units_sold": "avg_daily_demand_4w"})
        )

        df = inventory.merge(demand_4w, on=["store_id", "sku_id"], how="left")
        df["avg_daily_demand_4w"] = pd.to_numeric(df["avg_daily_demand_4w"], errors="coerce").fillna(0.01)

        df["stockout_flag"] = (df["on_hand_units"] == 0).astype(int)
        df["days_of_cover"] = df["on_hand_units"] / df["avg_daily_demand_4w"]

        out = df[
            [
                "date", "store_id", "sku_id",
                "on_hand_units", "stockout_flag", "days_of_cover"
            ]
        ].copy()

        return out

    except Exception as exc:
        logger.exception("Failed to build fact inventory | Error: %s", exc)
        raise

# Function to build the replenishment_inputs_store_sku dataset by calculating demand statistics, lead time, service level, safety stock, reorder point, and recommended order quantity for each store-sku combination
def build_replenishment_inputs(sales, purchase_orders, products, config, logger):
    """
    Output 3: replenishment_inputs_store_sku.csv

    For each store-sku:
      avg_daily_demand (last 4-8 weeks) -> using demand_window_days
      demand_std_dev
      lead_time_days (from purchase_orders)
      service_level_target (category-based)
      reorder_point, safety_stock, recommended_order_qty
    """
    try:
        logger.info("Building replenishment_inputs_store_sku")

        max_date = sales["date"].max()
        start = max_date - pd.Timedelta(days=config.demand_window_days - 1)
        recent = sales.loc[(sales["date"] >= start) & (sales["date"] <= max_date)].copy()

        stats = (
            recent.groupby(["store_id", "sku_id"], as_index=False)["units_sold"]
            .agg(avg_daily_demand="mean", demand_std_dev="std")
        )
        stats["demand_std_dev"] = stats["demand_std_dev"].fillna(0.0)

        lead_time = (
            purchase_orders.groupby(["store_id", "sku_id"], as_index=False)["lead_time_days"]
            .mean()
        )

        df = stats.merge(lead_time, on=["store_id", "sku_id"], how="left")
        global_median_lt = purchase_orders["lead_time_days"].median() if "lead_time_days" in purchase_orders.columns else 3
        df["lead_time_days"] = df["lead_time_days"].fillna(global_median_lt)
        df["lead_time_days"] = df["lead_time_days"].clip(lower=0)

        df = df.merge(products[["sku_id", "category"]], on="sku_id", how="left")

        # category-based service level policy
        service_level_map = {
            "dairy": 0.95,
            "grocery": 0.97,
            "snacks": 0.96,
            "beverages": 0.96,
            "homecare": 0.94,
            "personalcare": 0.94,
        }
        df["service_level_target"] = df["category"].map(service_level_map).fillna(0.95)

        # Z-score
        try:
            from scipy.stats import norm
            df["z_score"] = df["service_level_target"].apply(lambda x: float(norm.ppf(x)))
        except Exception:
            approx = {0.90: 1.282, 0.94: 1.555, 0.95: 1.645, 0.96: 1.751, 0.97: 1.881, 0.98: 2.054, 0.99: 2.326}
            df["z_score"] = df["service_level_target"].round(2).map(approx).fillna(1.645)

        df["safety_stock"] = (df["z_score"] * df["demand_std_dev"] * np.sqrt(df["lead_time_days"].clip(lower=0))).round(2)
        df["reorder_point"] = (df["avg_daily_demand"] * df["lead_time_days"] + df["safety_stock"]).round(2)
        df["recommended_order_qty"] = (np.ceil(df["avg_daily_demand"] * config.cover_window_days)).clip(lower=0)

        out = df[
            [
                "store_id", "sku_id",
                "avg_daily_demand", "demand_std_dev",
                "lead_time_days", "service_level_target",
                "reorder_point", "safety_stock",
                "recommended_order_qty",
            ]
        ].copy()

        return out

    except Exception as exc:
        logger.exception("Failed to build replenishment inputs | Error: %s", exc)
        raise


# ============================================================
# MAIN
# ============================================================
def run_pipeline():
    # CONFIG should already have .logger, .output_dir, .logs_dir, etc.
    CONFIG = PipelineConfig()
    logger = CONFIG.logger

    try:
        ensure_dirs([CONFIG.output_dir, CONFIG.logs_dir], logger)
        # Build PATHS and FOUND_FILES
        PATHS = build_paths(CONFIG)
        FOUND_FILES = build_found_files(CONFIG, logger)

        install_packages(CONFIG.required_library_path, logger)

        log_banner(logger, "Retail Demand Forecasting - ETL Pipeline")

        # Load raw data
        sales_raw, inv_raw, products_raw, cal_raw, po_raw, stores_raw = load_raw_datasets(FOUND_FILES, logger)

        # Clean data
        calendar = clean_calendar(cal_raw, logger)
        stores = clean_stores(stores_raw, logger)
        products = clean_products(products_raw, logger)
        purchase_orders = clean_purchase_orders(po_raw, logger)

        sales = clean_sales(sales_raw, calendar, logger)
        inventory = clean_inventory(inv_raw, logger)

        # Outliers + boxplot
        if "units_sold" in sales.columns:
            sales = add_outlier_flag_iqr_by_group(
                sales,
                group_cols=["store_id", "sku_id"],
                value_col="units_sold",
                flag_col="outlier_flag",
                logger=logger
            )

            plot_path = PATHS["plots"] / "units_sold_boxplot.png"
            save_boxplot(sales, "units_sold", "Boxplot – units_sold", plot_path, logger)

        # Build curated outputs (your existing build_fact_* functions can be reused)
        fact_sales = build_fact_sales(sales, logger)
        fact_inventory = build_fact_inventory(inventory, sales, CONFIG, logger)
        repl_inputs = build_replenishment_inputs(sales, purchase_orders, products, CONFIG, logger)

        # Save outputs
        out_sales_path = PATHS["output"] / CONFIG.out_fact_sales
        out_inv_path = PATHS["output"] / CONFIG.out_fact_inventory
        out_repl_path = PATHS["output"] / CONFIG.out_replenishment

        logger.info("Saving outputs to %s", PATHS["output"])
        fact_sales.to_csv(out_sales_path, index=False)
        fact_inventory.to_csv(out_inv_path, index=False)
        repl_inputs.to_csv(out_repl_path, index=False)

        log_banner(logger, "Outputs Generated")
        logger.info("✅ %s -> %s", CONFIG.out_fact_sales, out_sales_path)
        logger.info("✅ %s -> %s", CONFIG.out_fact_inventory, out_inv_path)
        logger.info("✅ %s -> %s", CONFIG.out_replenishment, out_repl_path)

        # Quick checks
        log_banner(logger, "Quick Quality Checks")
        logger.info("Project root: %s", CONFIG.project_root)
        logger.info("Rows – Sales fact: %s", f"{len(fact_sales):,}")
        logger.info("Rows – Inventory fact: %s", f"{len(fact_inventory):,}")
        logger.info("Rows – Replenishment inputs: %s", f"{len(repl_inputs):,}")

        if "outlier_flag" in sales.columns:
            logger.info("Outliers flagged (units_sold): %s", f"{int(sales['outlier_flag'].sum()):,}")

        # Example: top stockouts
        stockouts = fact_inventory.groupby(["store_id", "sku_id"], as_index=False)["stockout_flag"].sum()
        stockouts = stockouts.sort_values("stockout_flag", ascending=False).head(10)
        logger.info("Top 10 store-sku by stockout days:\n%s", stockouts.to_string(index=False))

        # keep for lint clarity
        _ = stores

        logger.info("ETL completed successfully ✅")

    except Exception as exc:
        logger.exception("ETL pipeline failed ❌ | Error: %s", exc)
        sys.exit(1)	


# Entry point for the script
if __name__ == "__main__":
    run_pipeline()