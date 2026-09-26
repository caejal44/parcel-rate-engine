import requests

from src.common.reference_data import get_reference_data

import streamlit as st
import pandas as pd
import datetime

st.set_page_config(
    page_title="Parcel Shipping Rate Calculator",
    layout="wide"
)

#--------------------------------
# Reference Information
#--------------------------------

reference_data = get_reference_data()
origin_zip_df = reference_data.orig_zips.copy()

display_options = (origin_zip_df["orig_zip"] + "  |  " + origin_zip_df["location"] +
                   "  |  " + origin_zip_df["city"])
#--------------------------------
# App Setup
#--------------------------------
st.title("Parcel Rate Engine")
st.write("Compare shipping costs and services across parcel carriers.")


#--------------------------------
# Sidebar Setup
#--------------------------------
with st.sidebar:
    st.header("Shipment Details")
    st.caption("Enter package and delivery information to compare available services.")

# sidebar is used to collect user input for model consumption
origin = st.sidebar.selectbox("Origin ZIP", display_options)
origin_zip = origin.split("  |  ")[0]
destination = st.sidebar.text_input("Destination ZIP", max_chars=5, placeholder="12345")

now = datetime.datetime.now()
tomorrow = now + datetime.timedelta(days=1)

default_delivery = tomorrow.replace(hour=20, minute=0, second=0, microsecond=0)
ship = st.sidebar.datetime_input("Ship date/time", now, format="MM/DD/YYYY")
delivery = st.sidebar.datetime_input("Desired delivery date/time",
                                     default_delivery,
                                     format="MM/DD/YYYY")

weight = st.sidebar.number_input("Shipment Weight (lbs)", min_value = 0.1, value=1.0)
length = st.sidebar.number_input("Length (in)", min_value = 0.1, value=1.0)
width = st.sidebar.number_input("Width (in)", min_value = 0.1, value=1.0)
height = st.sidebar.number_input("Height (in)", min_value = 0.1, value=1.0)


declared_value = st.sidebar.number_input("Declared Value ($)", min_value = 0.0, max_value = 5000.0, value=0.0)

signature_type = st.sidebar.selectbox("Signature",
    ["No Signature",
        "Signature Required",
        "Adult Signature Required"])

signature = signature_type == "Signature Required"
adult_signature = signature_type == "Adult Signature Required"

residential_delivery = st.sidebar.checkbox("Residential Delivery")

packaging = st.sidebar.checkbox("Special Packaging")

saturday = st.sidebar.checkbox("Saturday Delivery")

reference = st.sidebar.text_input("PO / Reference")

rate_shipment = st.sidebar.button("Rate Shipment")

#--------------------------------
# Rate Shipment Logic
#--------------------------------
valid_destination = len(destination) == 5 and destination.isdigit()
valid_dates = delivery > ship
valid_ship_date = ship >= now

shipment_id = None
billable_response_data = None
quote_response_data = None

if rate_shipment:
    if not valid_destination:
        st.error("Enter a valid 5-digit destination ZIP.")

    elif not valid_ship_date:
        st.error("Ship date cannot be in the past.")

    elif not valid_dates:
        st.error("Requested delivery must be after the ship date.")

    else:
        shipment_data = {
            "orig_zip": origin_zip,
            "dest_zip": destination,
            "ship_date": ship.isoformat(),
            "requested_delivery": delivery.isoformat(),
            "actual_weight": weight,
            "length": length,
            "height": height,
            "width": width,
            "declared_value": declared_value,
            "residential_delivery": residential_delivery,
            "reference": reference,
            "signature_required": signature,
            "adult_signature_required": adult_signature,
            "additional_handling_packaging": packaging,
            "saturday_delivery": saturday,
        }

        API_BASE_URL = "https://t45bypccwk.execute-api.us-east-1.amazonaws.com"

        api_url = f"{API_BASE_URL}/shipments"

        try:
            response = requests.post(
                api_url,
                json=shipment_data
            )

            if response.status_code == 201:
                response_data = response.json()

                shipment_id = response_data["shipment_id"]
            else:
                error_data = response.json()

                st.error("Unable to rate shipment")
                st.write(error_data.get("details", "An unexpected error occurred."))

        except requests.exceptions.RequestException as e:
            st.error(f"Unable to connect to rating API: {e}")

        # create billable shipments
        if shipment_id is not None:
            billable_api_url = f"{API_BASE_URL}/shipments/{shipment_id}/billable-shipments"
            try:
                billable_response = requests.post(billable_api_url)

                if billable_response.status_code == 201:
                    billable_response_data = billable_response.json()

                else:
                    error_data = billable_response.json()

                    st.error("Unable to rate shipment")
                    st.write(error_data.get("details", "An unexpected error occurred."))

            except requests.exceptions.RequestException as e:
                st.error(f"Unable to connect to rating API: {e}")

        # create service quotes
        if billable_response_data is not None:
            quote_api_url = f"{API_BASE_URL}/shipments/{shipment_id}/service-quotes"
            try:
                quote_response = requests.post(quote_api_url)

                if quote_response.status_code == 201:
                    quote_response_data = quote_response.json()

                else:
                    error_data = quote_response.json()

                    st.error("Unable to rate shipment")
                    st.write(error_data.get("details", "An unexpected error occurred."))


            except requests.exceptions.RequestException as e:
                st.error(f"Unable to connect to rating API: {e}")


#--------------------------------
# Display Logic
#--------------------------------
    if quote_response_data is not None:

        # displays user information
        st.subheader("Shipment Summary")
        shipment_summary = {
            "Origin ZIP": origin_zip,
            "Destination ZIP": destination,
            "Ship Date": ship.strftime("%b %d, %Y %I:%M %p"),
            "Requested Delivery": delivery.strftime("%b %d, %Y %I:%M %p"),
            "Actual Weight": f"{weight:.1f} lb",
            "Dimensions": f"{length} × {width} × {height} in",
            "Declared Value": f"${declared_value:,.2f}",
            "Residential Delivery": "Yes" if residential_delivery else "No",
            "Reference": reference,
            "Signature Required": "Yes" if signature else "No",
            "Adult Signature Required": "Yes" if adult_signature else "No",
            "Special Packaging": "Yes" if packaging else "No",
            "Saturday Delivery": "Yes" if saturday else "No",
    }

        summary_df = pd.DataFrame(shipment_summary.items(),
            columns=["Shipment Detail", "Value"])

        st.dataframe(summary_df, hide_index=True, width="stretch")

        st.subheader("Rate Comparison")

        quotes = quote_response_data["quotes"]

        sorted_quotes = sorted(
            quotes,
            key=lambda quote: quote["total_charge"]
        )

        quote_summaries = []

        for quote in sorted_quotes:
            accessorial_total = sum(charge["amount"]
                for charge in quote["charges"])
            estimated_delivery = datetime.datetime.fromisoformat(
                quote["estimated_delivery"]
            ).strftime("%b %d, %Y %I:%M %p")

            quote_summary = {
                "Carrier": quote["carrier_name"],
                "Service": quote["service_name"],
                "Billable Weight": f"{quote["billable_weight"]} lb",
                "Estimated Delivery": estimated_delivery,
                "Transportation": f"${quote["transportation_charge"]:.2f}",
                "Accessorials": f"${accessorial_total:.2f}",
                "Fuel": f"${quote["fuel_charge"]:.2f}",
                "Total": f"${quote["total_charge"]:.2f}"
            }

            quote_summaries.append(quote_summary)

        quote_summary_df = pd.DataFrame(quote_summaries)

        st.dataframe(quote_summary_df, hide_index=True, width="stretch")

        st.subheader("Rate Details")

        for quote in sorted_quotes:

            estimated_delivery = datetime.datetime.fromisoformat(
                quote["estimated_delivery"]
            ).strftime("%b %d, %Y %I:%M %p")

            fuel_effective_date = datetime.datetime.fromisoformat(
                quote["fuel_effective_date"]
            ).strftime("%b %d, %Y")

            with st.expander(
                    f"{quote['carrier_name']} — "
                    f"{quote['service_name']} — "
                    f"{estimated_delivery} — "
                    f"${quote['total_charge']:.2f}"
            ):

                st.markdown("##### Shipment Details")

                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"Service Code: {quote['service_code']}")
                    st.write(f"Billable Weight: {quote['billable_weight']} lb")

                with col2:
                    st.write(f"Zone: {quote['zone']}")
                    st.write(f"Estimated Delivery: {estimated_delivery}")

                st.markdown("##### Charges")

                st.write(
                    f"Transportation: ${quote['transportation_charge']:.2f}"
                )

                for charge in quote["charges"]:
                    st.write(
                        f"{charge['charge_description']}: "
                        f"${charge['amount']:.2f}"
                    )

                st.write(f"Fuel: ${quote['fuel_charge']:.2f}")

                st.markdown(
                    f"##### Total: ${quote['total_charge']:.2f}"
                )
                st.markdown("##### Fuel Details")

                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"Fuel Type: {quote['fuel_type']}")
                    st.write(f"Fuel Price: ${quote['fuel_price']}/gal")

                with col2:
                    st.write(f"Fuel Effective Date: {fuel_effective_date}")
                    st.write(f"Fuel Percentage: {quote['fuel_pct'] * 100:.2f}%")

        # disclaimer
        st.write("Quotes rely on accuracy of input values and do not constitute a guarantee of price and/or delivery time.")
