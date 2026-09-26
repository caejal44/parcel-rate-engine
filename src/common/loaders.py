import pandas as pd
import pathlib

def _require_columns(df: pd.DataFrame, required: list[str], label:str) -> None:
    """quality check for required columns"""
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{label}: missing required columns: {missing}. Found {list(df.columns)}")

def load_zone_matrix(path: pathlib.Path) -> pd.DataFrame:
    """Load and validate carrier service ZIP-zone mappings."""

    required_identity_columns = [
        "carrier_service_code",
        "carrier_code",
        "service_code",
        "origin_zip_start",
        "origin_zip_end",
        "destination_zip_start",
        "destination_zip_end"
    ]

    availability_columns = [
        "source_zone",
        "normalized_zone",
        "transit_days",
        "transit_time"
    ]


    zip_columns = [
        "origin_zip_start",
        "origin_zip_end",
        "destination_zip_start",
        "destination_zip_end",
    ]

    df = pd.read_csv(path, dtype=str)

    required_columns = (
            required_identity_columns
            + availability_columns
    )

    _require_columns(
        df,
        required_columns,
        "zone_matrix",
    )

    # Clean strings first.
    for col in required_columns:
        df[col] = df[col].str.strip()

    df[availability_columns] = (
        df[availability_columns]
        .replace("", pd.NA)
    )

    # Identity fields can never be missing.
    invalid_rows = df[
        df[required_identity_columns].isna().any(axis=1)
    ]

    if not invalid_rows.empty:
        raise ValueError(
            "zone_matrix: missing identity values found at CSV rows "
            f"{(invalid_rows.index + 2).tolist()}"
        )

    # Availability must be completely populated or completely absent.
    availability_missing = df[availability_columns].isna()

    partially_missing = (
            availability_missing.any(axis=1)
            & ~availability_missing.all(axis=1)
    )

    if partially_missing.any():
        rows = (df.index[partially_missing] + 2).tolist()

        raise ValueError(
            "zone_matrix: zone/transit fields must either all be populated "
            f"or all be NA. Invalid CSV rows: {rows}"
        )


    # Validate ZIP formatting while preserving leading zeroes.
    for col in zip_columns:
        invalid_zip = ~df[col].str.fullmatch(r"\d{5}")

        if invalid_zip.any():
            rows = (df.index[invalid_zip] + 2).tolist()

            raise ValueError(
                f"zone_matrix: {col} must contain 5-digit ZIP codes. "
                f"Invalid CSV rows: {rows}"
            )

    # Numeric helper columns for range comparisons.
    df["origin_zip_start_num"] = df["origin_zip_start"].astype(int)
    df["origin_zip_end_num"] = df["origin_zip_end"].astype(int)

    df["destination_zip_start_num"] = (
        df["destination_zip_start"].astype(int)
    )
    df["destination_zip_end_num"] = (
        df["destination_zip_end"].astype(int)
    )

    df["normalized_zone"] = (
        pd.to_numeric(df["normalized_zone"], errors="raise")
        .astype("Int64")
    )

    df["transit_days"] = (
        pd.to_numeric(df["transit_days"], errors="raise")
        .astype("Int64")
    )

    available = ~df[availability_columns].isna().all(axis=1)

    invalid_transit_time = (
            available
            & ~df["transit_time"].str.fullmatch(
        r"(?:[01]\d|2[0-3]):[0-5]\d",
        na=False,
    )
    )

    if invalid_transit_time.any():
        rows = (
                df.index[invalid_transit_time] + 2
        ).tolist()

        raise ValueError(
            "zone_matrix: transit_time must use HH:MM format. "
            f"Invalid CSV rows: {rows}"
        )

    invalid_transit_days = (
            available
            & (df["transit_days"] <= 0)
    )

    if invalid_transit_days.any():
        rows = (df.index[invalid_transit_days] + 2).tolist()
        raise ValueError(
            "zone_matrix: transit_days must be greater than zero.  "
            f"Invalid CSV rows: {rows}"
        )

    # Validate ZIP ranges.
    invalid_origin_range = (
        df["origin_zip_start_num"]
        > df["origin_zip_end_num"]
    )

    if invalid_origin_range.any():
        rows = (df.index[invalid_origin_range] + 2).tolist()

        raise ValueError(
            "zone_matrix: origin ZIP start cannot exceed origin ZIP end. "
            f"Invalid CSV rows: {rows}"
        )

    invalid_destination_range = (
        df["destination_zip_start_num"]
        > df["destination_zip_end_num"]
    )

    if invalid_destination_range.any():
        rows = (
            df.index[invalid_destination_range] + 2
        ).tolist()

        raise ValueError(
            "zone_matrix: destination ZIP start cannot exceed "
            f"destination ZIP end. Invalid CSV rows: {rows}"
        )

    # Validate combined carrier-service identifier.
    expected_code = (
        df["carrier_code"]
        + df["service_code"]
    )

    invalid_code = (
        df["carrier_service_code"] != expected_code
    )

    if invalid_code.any():
        rows = (df.index[invalid_code] + 2).tolist()

        raise ValueError(
            "zone_matrix: carrier_service_code does not match "
            f"carrier_code + service_code at CSV rows {rows}"
        )

    # Duplicate carrier-service lane keys.
    duplicates = df.duplicated(
        subset=required_identity_columns,
        keep=False,
    )

    if duplicates.any():
        rows = (df.index[duplicates] + 2).tolist()

        raise ValueError(
            f"zone_matrix: duplicate rows found at CSV rows {rows}"
        )

    return df.reset_index(drop=True)

def load_service_configuration(path:pathlib.Path) -> pd.DataFrame:
    """load carrier/service information and service thresholds into dataframe"""
    string_columns = ["carrier_service_code",
                      "carrier_name",
                      "carrier_code",
                      "service_code",
                      "service_name",
                      "service_group",
                      "delivery_type",
                      "transport_mode"]
    numeric_columns = ["dim_factor",
                       "ah_weight_threshold",
                       "ah_length_threshold",
                       "ah_width_threshold",
                       "ah_length_plus_girth_threshold",
                       "large_package_length_threshold",
                       "large_package_length_plus_girth_threshold",
                       "large_package_weight",
                       "max_weight",
                       "max_length",
                       "max_length_plus_girth"]
    required_columns = string_columns + numeric_columns

    df = pd.read_csv(path, dtype=str)

    _require_columns(
        df,
        required_columns,
        "service_configuration",
    )

    for col in string_columns:
        df[col] = df[col].str.strip()

    df["delivery_type"] = df["delivery_type"].str.upper()

    df["transport_mode"] = df["transport_mode"].str.upper()

    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="raise")

    invalid_rows = df[df[required_columns].isna().any(axis=1)]
    if not invalid_rows.empty:
        raise ValueError(
            "service_configuration: missing values found at CSV rows "
            f"{(invalid_rows.index + 2).tolist()}"
        )

    if df["carrier_service_code"].duplicated().any():
        dupes = (
            df.loc[
                df["carrier_service_code"].duplicated(keep=False),
                "carrier_service_code",
            ]
            .drop_duplicates()
            .tolist()
        )
        raise ValueError(
            f"service_configuration: duplicate carrier_service_code values: {dupes}"
        )

    expected_code = (
            df["carrier_code"]
            + df["service_code"]
    )

    invalid_code = (
            df["carrier_service_code"] != expected_code)

    if invalid_code.any():
        rows = (df.index[invalid_code] + 2).tolist()

        raise ValueError(
            "service_configuration: carrier_service_code does not match "
            f"carrier_code + service_code at CSV rows {rows}")

    if (df[numeric_columns] < 0).any().any():
        raise ValueError("service_configuration: threshold values cannot be negative")

    if (df["dim_factor"] <= 0).any():
        raise ValueError("service_configuration: dim_factor must be greater than zero")

    invalid_delivery_type = ~df["delivery_type"].isin(["BOTH", "COMMERCIAL", "RESIDENTIAL"])

    if invalid_delivery_type.any():
        rows = (df.index[invalid_delivery_type] + 2).tolist()
        raise ValueError(
            "service_configuration: delivery_type must be one of BOTH, COMMERCIAL, RESIDENTIAL"
            f"Invalid CSV rows: {rows}"
        )

    invalid_transport_mode = ~df["transport_mode"].isin(["AIR", "ROAD"])

    if invalid_transport_mode.any():
        rows = (df.index[invalid_transport_mode] + 2).tolist()
        raise ValueError(
            "service_configuration: transport_mode must be one of AIR, ROAD"
            f"Invalid CSV rows: {rows}"
        )

    return df.reset_index(drop=True)

def load_das_zips(path:pathlib.Path) -> pd.DataFrame:
    """Load and validate ZIP codes subject to delivery-area surcharges."""
    required_columns = ["zip_code",
                        "carrier_code",
                        "das_type"]

    df = pd.read_csv(
        path,
        dtype={
            "zip_code": str,
            "carrier_code": str,
            "das_type": str
        },
    )

    _require_columns(df, required_columns, "das_zips")

    # Clean strings first.
    for col in required_columns:
        df[col] = df[col].str.strip()

    invalid_rows = df[
        df[required_columns].isna().any(axis=1)
    ]

    if not invalid_rows.empty:
        raise ValueError(
            "das_zips: missing values found at CSV rows "
            f"{(invalid_rows.index + 2).tolist()}"
        )

    # Validate ZIP formatting while preserving leading zeroes.
    invalid_zip = ~df["zip_code"].str.fullmatch(r"\d{5}")

    if invalid_zip.any():
        rows = (df.index[invalid_zip] + 2).tolist()

        raise ValueError(
            f"das_zips: zip_code must contain 5-digit ZIP codes. "
            f"Invalid CSV rows: {rows}"
            )

    df["das_type"] = df["das_type"].str.upper()

    invalid_das_type = ~df["das_type"].isin(
        ["DAS", "EDAS", "REM"]
    )

    if invalid_das_type.any():
        rows = (df.index[invalid_das_type] + 2).tolist()

        raise ValueError(
            "das_zips: das_type must be DAS, EDAS, or REM. "
            f"Invalid CSV rows: {rows}"
        )

    duplicate_mask = df.duplicated(
        subset=["zip_code", "carrier_code"],
        keep=False,
    )

    if duplicate_mask.any():
        dupes = (
            df.loc[
                duplicate_mask,
                ["zip_code", "carrier_code", "das_type"],
            ]
            .drop_duplicates()
            .values.tolist()
        )

        raise ValueError(
            f"das_zips: duplicate carrier/ZIP combinations: {dupes}"
        )
    return df.reset_index(drop=True)

def load_fuel_chart(path:pathlib.Path) -> pd.DataFrame:
    """Load fuel percentages based on EIA rate."""
    string_columns = ["carrier_code",
                        "transport_mode"]
    numeric_columns = ["fuel_price_min",
                        "fuel_pct"]

    df = pd.read_csv(path, dtype=str)

    required_columns = string_columns + numeric_columns

    _require_columns(df, required_columns, "fuel_chart")

    for col in string_columns:
        df[col] = df[col].str.strip()

    df["transport_mode"] = df["transport_mode"].str.upper()

    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="raise")

    invalid_rows = df[df[required_columns].isna().any(axis=1)]
    if not invalid_rows.empty:
        raise ValueError(
            "fuel_chart: missing values found at CSV rows "
            f"{(invalid_rows.index + 2).tolist()}"
        )

    duplicate_key = df.duplicated(
        subset=["carrier_code", "transport_mode", "fuel_price_min"],
        keep=False
    )

    if duplicate_key.any():
        rows = (df.index[duplicate_key] + 2).tolist()
        raise ValueError(
            "fuel_chart: duplicate carrier_code + transport_mode + "
            f"fuel_price_min at CSV rows {rows}"
        )

    invalid_transport_mode = ~df["transport_mode"].isin(["AIR", "ROAD"])

    if invalid_transport_mode.any():
        rows = (df.index[invalid_transport_mode] + 2).tolist()
        raise ValueError(
            "fuel_chart: transport_mode must be one of AIR, ROAD"
            f"Invalid CSV rows: {rows}"
        )

    zero_tiers = df[df["fuel_price_min"] == 0]

    all_groups = set(
        zip(df["carrier_code"], df["transport_mode"])
    )

    groups_with_zero = set(
        zip(zero_tiers["carrier_code"], zero_tiers["transport_mode"])
    )

    missing_zero_tier = all_groups - groups_with_zero

    if missing_zero_tier:
        raise ValueError(
            "fuel_chart: missing fuel_price_min=0 tier for "
            f"{sorted(missing_zero_tier)}"
        )

    if (df["fuel_price_min"] < 0).any():
        raise ValueError("fuel_chart: fuel_price_min cannot be negative")

    invalid_fuel_pct = (
            (df["fuel_pct"] < 0)
            | (df["fuel_pct"] > 1)
    )

    if invalid_fuel_pct.any():
        rows = (df.index[invalid_fuel_pct] + 2).tolist()
        raise ValueError(
            "fuel_chart: fuel_pct must be between 0 and 1. "
            f"Invalid CSV rows: {rows}"
        )

    return df.reset_index(drop=True)

def load_transportation_rates(path:pathlib.Path) -> pd.DataFrame:
    """Load transportation rates for carrier service code by zone/billable weight."""

    required_columns = ["carrier_service_code",
                      "zone",
                      "billable_weight",
                      "net_rate"]

    df = pd.read_csv(path, dtype=str)

    _require_columns(df, required_columns, "transportation_rates")


    df["carrier_service_code"] = df["carrier_service_code"].str.strip()

    invalid_rows = df[df[required_columns].isna().any(axis=1)]
    if not invalid_rows.empty:
        raise ValueError(
            "transportation_rates: missing values found at CSV rows "
            f"{(invalid_rows.index + 2).tolist()}"
        )

    df["zone"] = pd.to_numeric(df["zone"], errors="raise").astype("Int64")
    df["billable_weight"] = pd.to_numeric(df["billable_weight"], errors="raise").astype("Int64")
    df["net_rate"] = pd.to_numeric(df["net_rate"], errors="raise")


    duplicate_key = df.duplicated(
        subset=["carrier_service_code", "zone", "billable_weight"],
        keep=False
    )

    if duplicate_key.any():
        rows = (df.index[duplicate_key] + 2).tolist()
        raise ValueError(
            "transportation_rates: duplicate carrier_service_code + zone + "
            f"billable_weight at CSV rows {rows}"
        )

    if (df["zone"] <= 0).any():
        raise ValueError("transportation_rates: zone must be greater than 0")
    if (df["billable_weight"] <= 0).any():
        raise ValueError("transportation_rates: billable_weight must be greater than 0")
    if (df["net_rate"] <= 0).any():
        raise ValueError("transportation_rates: net_rate must be greater than 0")

    invalid_code = ~df["carrier_service_code"].str.fullmatch(r"\d{4}")

    if invalid_code.any():
        rows = (df.index[invalid_code] + 2).tolist()
        raise ValueError(
            "transportation_rates: carrier_service_code must be exactly "
            f"4 digits. Invalid CSV rows: {rows}"
        )

    return df.reset_index(drop=True)

def load_charge_rates(path:pathlib.Path) -> pd.DataFrame:
    """Load additional charge rates for carrier service code."""

    required_columns = ["carrier_service_code",
                        "charge_code",
                        "net_charge",
                        "fuel_applied",
                        "charge_description"]

    df = pd.read_csv(path, dtype=str)

    _require_columns(df, required_columns, "charge_rates")

    df["carrier_service_code"] = df["carrier_service_code"].str.strip()
    df["charge_code"] = df["charge_code"].str.strip().str.upper()
    df["charge_description"] = df["charge_description"].str.strip()

    invalid_rows = df[df[required_columns].isna().any(axis=1)]
    if not invalid_rows.empty:
        raise ValueError(
            "charge_rates: missing values found at CSV rows "
            f"{(invalid_rows.index + 2).tolist()}"
        )

    invalid_code = ~df["carrier_service_code"].str.fullmatch(r"\d{4}")

    if invalid_code.any():
        rows = (df.index[invalid_code] + 2).tolist()
        raise ValueError(
            "charge_rates: carrier_service_code must be exactly "
            f"4 digits. Invalid CSV rows: {rows}"
        )

    blank_description = df["charge_description"] == ""

    if blank_description.any():
        rows = (df.index[blank_description] + 2).tolist()
        raise ValueError(
            "charge_rates: charge_description cannot be blank. "
            f"Invalid CSV rows: {rows}"
        )

    duplicate_key = df.duplicated(
        subset=["carrier_service_code", "charge_code"],
        keep=False
    )

    if duplicate_key.any():
        rows = (df.index[duplicate_key] + 2).tolist()
        raise ValueError(
            "charge_rates: duplicate carrier_service_code + charge_code. "
            f"Invalid at CSV rows {rows}"
        )

    description_counts = (
        df.groupby("charge_code")["charge_description"]
        .nunique()
    )

    inconsistent_codes = description_counts[
        description_counts > 1
        ].index.tolist()

    if inconsistent_codes:
        raise ValueError(
            "charge_rates: inconsistent charge_description for charge_code(s): "
            f"{inconsistent_codes}"
        )

    df["net_charge"] = pd.to_numeric(df["net_charge"], errors="raise")

    df["fuel_applied"] = df["fuel_applied"].str.strip().str.upper()

    invalid_fuel_applied = ~df["fuel_applied"].isin(["TRUE", "FALSE"])

    if invalid_fuel_applied.any():
        rows = (df.index[invalid_fuel_applied] + 2).tolist()
        raise ValueError(
            "charge_rates: fuel_applied must be one of TRUE, FALSE. "
            f"Invalid CSV rows: {rows}"
        )
    df["fuel_applied"] = df["fuel_applied"].replace({"TRUE": True, "FALSE": False}).astype(bool)

    invalid_net_charge = df["net_charge"] < 0

    if invalid_net_charge.any():
        rows = (df.index[invalid_net_charge] + 2).tolist()
        raise ValueError(
            "charge_rates: net_charge must be greater than or equal to 0. "
            f"Invalid CSV rows: {rows}"
        )

    return df.reset_index(drop=True)

def load_orig_zips(path:pathlib.Path) -> pd.DataFrame:
    """Load origin zips."""
    required_columns = ["location", "city", "orig_zip"]

    df = pd.read_csv(path, dtype=str)

    _require_columns(df, required_columns, "orig_zips")

    df["location"] = df["location"].str.strip()
    df["city"] = df["city"].str.strip()
    df["orig_zip"] = df["orig_zip"].str.strip()

    invalid_rows = df[
        df[required_columns].isna().any(axis=1)
    ]

    if not invalid_rows.empty:
        raise ValueError(
            "orig_zips: missing values found at CSV rows "
            f"{(invalid_rows.index + 2).tolist()}"
        )

    # Validate ZIP formatting while preserving leading zeroes.
    invalid_zip = ~df["orig_zip"].str.fullmatch(r"\d{5}")

    if invalid_zip.any():
        rows = (df.index[invalid_zip] + 2).tolist()

        raise ValueError(
            f"orig_zips: zip_code must contain 5-digit ZIP codes. "
            f"Invalid CSV rows: {rows}"
        )

    duplicate_mask = df.duplicated(
        subset=["location", "orig_zip"],
        keep=False,
    )

    if duplicate_mask.any():
        dupes = (
            df.loc[
                duplicate_mask,
                ["location", "orig_zip"],
            ]
            .drop_duplicates()
            .values.tolist()
        )

        raise ValueError(
            f"orig_zips: duplicate location/ZIP combinations: {dupes}"
        )
    return df.reset_index(drop=True)













