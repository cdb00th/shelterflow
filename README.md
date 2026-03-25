# ShelterFlow

An open-source data pipeline and analytics toolkit for animal shelters.

## Overview


## Architecture
Bronze -> Silver -> Gold medallion architecture.

## Getting the Data
1. Download the Austin Animal Center dataset from [Kaggle](https://www.kaggle.com/datasets/aaronschlegel/austin-animal-center-shelter-intakes-and-outcomes)
2. Place `aac_intakes.csv` and `aac_outcomes.csv` in `data/bronze/`

## Setup
1. Clone the repo
2. Create and activate the virtual environment:
```
   python -m venv .venv
   source .venv/bin/activate  # Mac/Linux
   .venv\Scripts\activate     # Windows	
```
3. Install dependencies:
```
   pip install -r requirements.txt
```

## Running the Pipeline
```
python pipelines/bronze_ingest.py
```

## Project Structure
```
shelterflow/
   data/
      bronze/
      silver/
      gold/
   pipelines/
   dbt_shelterflow/
   dashboard/
   docker/
```
