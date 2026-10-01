# Parcel Rate Engine

A cloud-based parcel rating application that models the process of turning raw shipment information into eligible carrier services and fully priced service quotes.

Parcel Rate Engine was built to apply software engineering and cloud development to real-world parcel logistics concepts. The application evaluates service eligibility, dimensional and billable weight, transit commitments, transportation rates, accessorial charges, delivery-area surcharges, fuel surcharges, and other shipment characteristics before returning comparable service quotes.

The project uses fictional carriers and simulated pricing data. It is intended as a portfolio and software engineering project rather than a commercial shipping application.

## Live Project

**Project page:**  
https://joshlane.dev/projects/parcel-rate-engine/index.html

**Live demo:**  
https://josh-lane-parcel-rate.streamlit.app

---

## What It Does

A user enters the characteristics of a shipment, including:

- Origin and destination ZIP codes
- Ship date and requested delivery date
- Actual weight
- Package dimensions
- Residential/commercial delivery
- Declared value
- Signature requirements
- Packaging type
- Saturday delivery requirements

The backend then determines which carrier services can handle the shipment and calculates the characteristics needed to rate each eligible service.

The resulting quotes include:

- Carrier and service
- Zone
- Billable weight
- Transportation charge
- Accessorial charges
- Fuel surcharge
- Total charge
- Fuel price and effective date used for rating

The Streamlit interface presents eligible services in a rate comparison and provides detailed charge information for each quote.

---

## Rating Flow

The application separates shipment input, carrier-specific rating characteristics, and pricing into distinct domain models:

```text
RawShipment
     │
     ▼
Lane & Service Eligibility
     │
     ▼
BillableShipment(s)
     │
     ▼
ServiceQuote(s)
```

### RawShipment

Represents the physical shipment and customer request before carrier-specific rules are applied.

### BillableShipment

Represents the derived characteristics required to rate an eligible carrier service.

A single raw shipment can produce multiple billable shipments because dimensional factors, service eligibility, zones, and other rating rules may differ by carrier and service.

### ServiceQuote

Applies transportation rates, accessorial rules, fuel surcharges, and other pricing logic to a billable shipment to produce a final service quote.

This separation keeps physical shipment data distinct from carrier-specific rating decisions and pricing.

---

## Business Rules

The rating engine implements a number of parcel-rating concepts, including:

### Service Eligibility

Available services are determined using:

- Origin ZIP
- Destination ZIP
- Carrier/service lane availability
- Residential/commercial eligibility
- Transit time
- Requested delivery date

A lane may return all, some, or no carrier services depending on the shipment.

### Dimensional & Billable Weight

Dimensional weight is calculated using the dimensional factor configured for the carrier service.

```text
DIM Weight = (Length × Width × Height) / DIM Factor

Billable Weight = ceil(max(Actual Weight, DIM Weight))
```

### Additional Handling

Shipments can qualify for additional handling based on:

- Weight
- Dimensions
- Packaging

When multiple conditions apply, the engine uses defined precedence rules to determine the applicable additional-handling classification.

### Large Package & Over Maximum Limits

Physical shipment characteristics are evaluated independently for large-package and over-maximum classifications.

Over-maximum classification takes precedence over large-package classification when both conditions apply.

### Accessorial Charges

The engine supports simulated charges for conditions including:

- Residential delivery
- Saturday delivery
- Signature required
- Adult signature required
- Delivery-area surcharges
- Extended delivery areas
- Remote delivery areas
- Additional handling
- Large packages
- Over-maximum shipments
- Declared value

Pricing logic also handles precedence between certain accessorials to prevent incompatible charges from being billed together.

### Fuel Surcharges

Fuel surcharges are based on the transportation charge plus accessorials configured as fuel-eligible.

```text
Fuel Charge = Fuel-Eligible Charges × Fuel Percentage
```

Fuel type is determined by the transportation mode of the service.

---

## Automated Fuel Data

The application retrieves current fuel-price data from the U.S. Energy Information Administration (EIA).

Two fuel types are maintained:

- Diesel
- Jet fuel

An AWS Lambda function retrieves the latest observations and stores them in DynamoDB using the fuel type and effective date.

AWS EventBridge Scheduler invokes the fuel-update process automatically each day.

When a shipment is rated, the quote engine retrieves the most recent applicable fuel observation and uses a simulated fuel-surcharge table to determine the percentage applied to the shipment.

CloudWatch monitoring is used to observe the scheduled Lambda execution and identify failures in the external data-refresh process.

---

## Architecture

```text
                         ┌──────────────────┐
                         │    Streamlit     │
                         │   Web Interface  │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │   API Gateway    │
                         └────────┬─────────┘
                                  │
                  ┌───────────────┼────────────────┐
                  ▼               ▼                ▼
          ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
          │ Raw Shipment │ │   Billable   │ │Service Quote │
          │    Lambda    │ │   Shipment   │ │    Lambda    │
          │              │ │    Lambda    │ │              │
          └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
                 │                │                 │
                 └────────────────┼─────────────────┘
                                  ▼
                         ┌──────────────────┐
                         │     DynamoDB     │
                         └──────────────────┘


      ┌──────────────────┐
      │ EventBridge      │
      │ Scheduler        │
      └────────┬─────────┘
               ▼
      ┌──────────────────┐
      │ Fuel Update      │
      │ Lambda           │
      └────────┬─────────┘
               ▼
      ┌──────────────────┐
      │ EIA Fuel API     │
      └────────┬─────────┘
               ▼
      ┌──────────────────┐
      │ DynamoDB Fuel    │
      │ Data             │
      └──────────────────┘
```

---

## Technology

### Backend

- Python
- Pydantic
- pandas
- REST APIs

### AWS

- AWS Lambda
- Amazon API Gateway
- Amazon DynamoDB
- Amazon EventBridge Scheduler
- Amazon CloudWatch
- Amazon SNS

### Frontend

- Streamlit

### External Data

- U.S. Energy Information Administration API

### Portfolio Hosting

- Amazon S3
- Amazon CloudFront
- Amazon Route 53
- AWS Certificate Manager

---

## API Workflow

The public demo uses a three-stage workflow.

### Create Shipment

```http
POST /shipments
```

Validates and persists the raw shipment request.

### Create Billable Shipments

```http
POST /shipments/{shipment_id}/billable-shipments
```

Determines eligible carrier services and derives the carrier/service-specific characteristics needed for rating.

### Create Service Quotes

```http
POST /shipments/{shipment_id}/service-quotes
```

Rates the eligible billable shipments and returns comparable service quotes.

The `shipment_id` created by the first request acts as the identifier throughout the workflow.

---

## Reference Data & Rate Documentation

The application uses simulated reference data to support rating logic, including:

- Carrier and service configuration
- Origin ZIP ranges
- Zone mappings
- Transit times
- Transportation rates
- Accessorial charge tables
- Delivery-area ZIP classifications
- Fuel surcharge tables

### Fictional Carriers

The current implementation models two fictional parcel carriers:

- **PartnerLine Logistics**
- **ConTracks**

Each carrier has its own service portfolio, eligibility rules, dimensional factors, thresholds, rates, and accessorial charges.

All carrier names, services, rates, and charge structures in this project are fictional or simulated and should not be interpreted as published pricing from an actual carrier.

### Rate Documentation

Sample rate and charge documentation used to illustrate the pricing structures modeled by the application is available in [`docs/rate-cards`](docs/rate-cards/).

The documentation includes:

- PartnerLine Logistics transportation rate tables
- PartnerLine Logistics additional charges
- ConTracks transportation rate tables
- ConTracks additional charges

These workbooks are provided as supporting documentation for the project and use fictional carriers and simulated pricing data. They are separate from the application's runtime reference-data files.

---

## Design Decisions

Several architectural decisions were made intentionally as the project developed.

### Separate Raw and Billable Shipments

Raw shipment information is preserved independently from carrier-specific calculations. This allows one shipment to generate multiple billable representations without modifying the original shipment.

### Keep Classification Separate From Pricing

Shipment characteristics such as additional handling and large-package classifications are determined before pricing.

The pricing layer decides which resulting charges should actually be billed based on precedence rules.

### Data-Driven Carrier Configuration

Carrier services, thresholds, transportation rates, charge rates, zones, and other reference information are maintained outside the core rating logic where practical.

This reduces the amount of carrier-specific pricing information embedded directly in application code.

### Preserve Fuel History

Fuel observations are stored by fuel type and effective date rather than maintaining only a single current value.

The quote engine can therefore identify the latest applicable observation while retaining historical fuel data.

---

## Current Scope

Version **1.0.0** represents the completed MVP.

The current application supports:

- Shipment validation and persistence
- Lane and service eligibility
- Transit commitments
- Dimensional and billable weight
- Carrier/service-specific shipment classification
- Transportation pricing
- Accessorial pricing and precedence
- Declared-value charges
- Fuel surcharge calculation
- Automated EIA fuel updates
- Persistent service quotes
- Public REST API workflow
- Interactive Streamlit rate comparison
- AWS monitoring and scheduled processing
- Public cloud deployment

The MVP intentionally focuses on creating and rating new shipments. Shipment history, rerating existing shipments, authentication, and production carrier integrations are outside the current scope.

---

## Potential Future Development

Possible future versions could include:

- Published/list rates with customer-specific discounts
- Rate-version effective dating
- Shipment and quote history
- Rerating workflows
- Authentication and user ownership
- Idempotent request handling
- Additional carriers and services
- Expanded reference-data management
- Enhanced external API retry and observability
- A dedicated web frontend

These are potential extensions rather than requirements for the v1.0 MVP.

---

## Disclaimer

Parcel Rate Engine is a portfolio project created to demonstrate software engineering, cloud architecture, API development, and parcel-logistics domain modeling.

Carrier names and services are fictional. Rates, accessorial charges, thresholds, zones, and other pricing data are simulated and are not intended to represent the current tariffs, service guides, or pricing of any real parcel carrier.

The application should not be used to make actual shipping or purchasing decisions.

---

## Author

**Joshua Lane**

Portfolio: https://joshlane.dev  
LinkedIn: https://www.linkedin.com/in/joshua-lane-902a46170  
GitHub: https://github.com/caejal44