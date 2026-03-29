"""
MVE: Ego-graph vs per-edge orientation on Bayesian networks.

Tests H1 (ego-context hypothesis): does ego-graph prompting improve
edge orientation accuracy over per-edge prompting at matched information?

Supports multiple networks: insurance (default), alarm, asia.
"""

import json
import os
import re
import time
import argparse
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from dataclasses import dataclass, field

import numpy as np
import networkx as nx
from openai import OpenAI

# ── Configuration ──────────────────────────────────────────────────

BASE_URL = "https://spymrrgsaneehk-8000.proxy.runpod.net/v1"
MODEL = os.environ.get("LOCALE_MODEL", "Qwen/Qwen3.5-27B-FP8")
API_KEY = "unused"
TEMPERATURE = 0.7
TEMP_LADDER = [0.3, 0.5, 0.7, 0.9, 1.1]  # Diverse temperatures for K=5 passes
MAX_TOKENS = 1500  # Enough for thinking mode; non-thinking uses dynamic sizing
K_PASSES = 5  # stochastic passes per prompt
MIN_EGO_DEGREE = 3  # Hybrid mode: use ego only for nodes with degree >= this
SEED_DATA = 42
N_SAMPLES = 5000
MAX_CONCURRENCY = 32  # vLLM batching sweet spot on A40

# Insurance network variable descriptions (domain knowledge)
VAR_DESCRIPTIONS = {
    "Age": "Driver's age group: Adolescent, Adult, Senior",
    "SocioEcon": "Socioeconomic status: Prole, Middle, UpperMiddle, Wealthy",
    "RiskAversion": "Risk tolerance level: Psychopath, Adventurous, Normal, Cautious",
    "VehicleYear": "Vehicle model year: Current, Older",
    "MakeModel": "Vehicle make and model category",
    "SeniorTrain": "Whether senior training program was completed",
    "DrivingSkill": "Driver's overall driving skill level",
    "DrivQuality": "Quality of driving: Poor, Normal, Excellent",
    "DrivHist": "Driving violation history: None, One, Many",
    "Accident": "Accident involvement and severity",
    "Mileage": "Annual mileage: FiveThou, TwentyThou, FiftyThou, Domino",
    "Antilock": "Whether vehicle has antilock braking system",
    "Airbag": "Whether vehicle has airbag",
    "Cushioning": "Vehicle cushioning quality: Poor, Fair, Good, Excellent",
    "Theft": "Vehicle theft risk",
    "CarValue": "Current market value of the car",
    "HomeBase": "Where the car is usually parked: Secure, Garage, Street, City",
    "AntiTheft": "Whether car has anti-theft device",
    "PropCost": "Property damage cost from accident",
    "OtherCarCost": "Cost of damage to other car",
    "OtherCar": "Whether another car was involved",
    "MedCost": "Medical cost from accident",
    "ILiCost": "Liability cost from accident",
    "GoodStudent": "Whether driver is a good student (discount eligible)",
    "ThisCarDam": "Damage to this car: None, Mild, Moderate, Severe",
    "ThisCarCost": "Cost of damage to this car",
    "RuggedAuto": "How rugged the vehicle is: EggShell, Football, Tank",
}

# Disguised names: neutral labels that prevent memorization of Insurance network
# while descriptions still provide the domain knowledge needed for causal reasoning.
DISGUISED_NAMES = {
    "Age": "V01",
    "SocioEcon": "V02",
    "RiskAversion": "V03",
    "VehicleYear": "V04",
    "MakeModel": "V05",
    "SeniorTrain": "V06",
    "DrivingSkill": "V07",
    "DrivQuality": "V08",
    "DrivHist": "V09",
    "Accident": "V10",
    "Mileage": "V11",
    "Antilock": "V12",
    "Airbag": "V13",
    "Cushioning": "V14",
    "Theft": "V15",
    "CarValue": "V16",
    "HomeBase": "V17",
    "AntiTheft": "V18",
    "PropCost": "V19",
    "OtherCarCost": "V20",
    "OtherCar": "V21",
    "MedCost": "V22",
    "ILiCost": "V23",
    "GoodStudent": "V24",
    "ThisCarDam": "V25",
    "ThisCarCost": "V26",
    "RuggedAuto": "V27",
}

# Alarm network variable descriptions (medical monitoring domain)
ALARM_DESCRIPTIONS = {
    "ANAPHYLAXIS": "Whether patient is having anaphylactic reaction",
    "ARTCO2": "Arterial CO2 level: Low, Normal, High",
    "BP": "Blood pressure: Low, Normal, High",
    "CATECHOL": "Catecholamine level: Normal, High",
    "CO": "Cardiac output: Low, Normal, High",
    "CVP": "Central venous pressure: Low, Normal, High",
    "DISCONNECT": "Whether ventilator is disconnected from patient",
    "ERRCAUTER": "Whether there is electrocautery interference on monitors",
    "ERRLOWOUTPUT": "Whether there is a low cardiac output error reading",
    "EXPCO2": "End-tidal CO2: Low, Normal, High, Zero",
    "FIO2": "Fraction of inspired oxygen: Low, Normal",
    "HISTORY": "Patient history of lung disease or other conditions",
    "HR": "Heart rate: Low, Normal, High",
    "HRBP": "Heart rate / blood pressure monitor reading",
    "HREKG": "Heart rate from EKG monitor",
    "HRSAT": "Heart rate from pulse oximeter",
    "HYPOVOLEMIA": "Whether patient has hypovolemia (low blood volume)",
    "INSUFFANESTH": "Whether anesthesia is insufficient",
    "INTUBATION": "Intubation status: Normal, Esophageal, OneSided",
    "KINKEDTUBE": "Whether the breathing tube is kinked",
    "LVEDVOLUME": "Left ventricular end-diastolic volume: Low, Normal, High",
    "LVFAILURE": "Whether left ventricle is failing",
    "MINVOL": "Minute ventilation: Low, Normal, High, Zero",
    "MINVOLSET": "Minute ventilation setting on ventilator: Low, Normal, High",
    "PAP": "Pulmonary artery pressure: Low, Normal, High",
    "PCWP": "Pulmonary capillary wedge pressure: Low, Normal, High",
    "PRESS": "Airway pressure: Low, Normal, High, Zero",
    "PULMEMBOLUS": "Whether patient has pulmonary embolism",
    "PVSAT": "Pulmonary venous oxygen saturation: Low, Normal, High",
    "SAO2": "Arterial oxygen saturation: Low, Normal, High",
    "SHUNT": "Pulmonary shunt: Normal, High",
    "STROKEVOLUME": "Stroke volume: Low, Normal, High",
    "TPR": "Total peripheral resistance: Low, Normal, High",
    "VENTALV": "Alveolar ventilation: Low, Normal, High, Zero",
    "VENTLUNG": "Lung ventilation: Low, Normal, High, Zero",
    "VENTMACH": "Ventilator machine output: Low, Normal, High, Zero",
    "VENTTUBE": "Tube ventilation: Low, Normal, High, Zero",
}

# Sachs network variable descriptions (protein signaling)
SACHS_DESCRIPTIONS = {
    "Raf": "Raf kinase: a serine/threonine-specific protein kinase in the MAPK/ERK signaling pathway",
    "Mek": "MEK (MAPK/ERK kinase): a dual-specificity kinase that phosphorylates ERK",
    "Plcg": "Phospholipase C gamma: hydrolyzes PIP2 into DAG and IP3",
    "PIP2": "Phosphatidylinositol 4,5-bisphosphate: a phospholipid component of cell membranes",
    "PIP3": "Phosphatidylinositol (3,4,5)-trisphosphate: a secondary messenger in cell signaling",
    "Erk": "ERK (Extracellular signal-regulated kinase): a terminal kinase in the MAPK pathway",
    "Akt": "Protein kinase B (Akt): a serine/threonine kinase involved in cell survival",
    "PKA": "Protein kinase A: a cAMP-dependent kinase that regulates many cellular processes",
    "PKC": "Protein kinase C: a calcium-dependent kinase activated by diacylglycerol",
    "P38": "p38 MAPK: a stress-activated protein kinase involved in inflammation",
    "Jnk": "JNK (c-Jun N-terminal kinase): a stress-activated kinase in the MAPK family",
}

# Child network variable descriptions (congenital heart disease diagnosis)
CHILD_DESCRIPTIONS = {
    "BirthAsphyxia": "Whether birth asphyxia occurred: Yes, No",
    "Disease": "Underlying cardiac disease type: PFC, TGA, Fallot, PAIVS, TAPVD, Lung",
    "Sick": "Whether the newborn appears sick: Yes, No",
    "Age": "Age category of the patient: 0-3 days, 4-10 days, 11-30 days",
    "LVH": "Left ventricular hypertrophy on ECG: Yes, No",
    "DuctFlow": "Direction of ductal blood flow: Lt_to_Rt, None, Rt_to_Lt",
    "CardiacMixing": "Degree of cardiac mixing: None, Mild, Complete, Transp",
    "LungParench": "Lung parenchymal disease status: Normal, Congested, Abnormal",
    "LungFlow": "Pulmonary blood flow: Normal, Low, High",
    "HypDistrib": "Hypoxia distribution pattern: Equal, Unequal",
    "HypoxiaInO2": "Hypoxia response to supplemental oxygen: Mild, Moderate, Severe",
    "CO2": "CO2 levels: Normal, Low, High",
    "ChestXray": "Chest X-ray findings: Normal, Oligaemic, Plethoric, Grd_Glass, Asy/Patchy",
    "Grunting": "Whether newborn is grunting: Yes, No",
    "GruntingReport": "Grunting reported by nurse: Yes, No",
    "LowerBodyO2": "Lower body oxygen saturation: <5, 5-12, >12",
    "RUQO2": "Right upper quadrant oxygen saturation: <5, 5-12, >12",
    "CO2Report": "CO2 level reported: <7.5, >=7.5",
    "XrayReport": "X-ray report findings: Normal, Oligaemic, Plethoric, Grd_Glass, Asy/Patchy",
    "Sick2": "Whether the newborn appears sick (second assessment): Yes, No",
}

# Asia network variable descriptions (pulmonary medicine)
ASIA_DESCRIPTIONS = {
    "asia": "Whether the patient has recently visited Asia: Yes, No",
    "tub": "Whether the patient has tuberculosis: Yes, No",
    "smoke": "Whether the patient is a smoker: Yes, No",
    "lung": "Whether the patient has lung cancer: Yes, No",
    "bronc": "Whether the patient has bronchitis: Yes, No",
    "either": "Whether the patient has either tuberculosis or lung cancer: Yes, No",
    "xray": "Whether the chest X-ray result is positive: Yes, No",
    "dysp": "Whether the patient has dyspnea (shortness of breath): Yes, No",
}

# Hailfinder network variable descriptions (severe weather forecasting)
HAILFINDER_DESCRIPTIONS = {
    "N34StarFcst": "Forecast for severe weather in the region: Above, Below",
    "SubjVertMo": "Subjective assessment of vertical motion: StrongUp, WeakUp, Neutral, Down",
    "QGVertMotion": "Quasi-geostrophic vertical motion: StrongUp, WeakUp, Neutral, Down",
    "CombVerMo": "Combined vertical motion assessment: StrongUp, WeakUp, Neutral, Down",
    "AreaMeso_ALS": "Mesoscale area of lift/support: StrongUp, WeakUp, Neutral, Down",
    "SatContMoist": "Satellite-derived moisture content: VeryWet, Wet, Neutral, Dry",
    "RaoContMoist": "Rawinsonde-derived moisture content: VeryWet, Wet, Neutral, Dry",
    "CombMoisture": "Combined moisture assessment: VeryWet, Wet, Neutral, Dry",
    "AreaMoDryAir": "Area of dry air aloft: VlgArea, LrgArea, SmArea, NoArea",
    "VISCloudCov": "Visible satellite cloud coverage: Cloudy, PC, Clear",
    "IRCloudCover": "Infrared satellite cloud coverage: Cloudy, PC, Clear",
    "CombClouds": "Combined cloud coverage assessment: Cloudy, PC, Clear",
    "CldShadeOth": "Cloud shading from non-convective sources: Cloudy, PC, Clear",
    "AMInstabMt": "Morning instability over mountains: None, Weak, Moderate, Strong",
    "InsInMt": "Instability index in mountain region: None, Weak, Moderate, Strong",
    "WndHodograph": "Wind hodograph shape: DCVZFaworworble, Other, Unfavorable",
    "OutflowFrMt": "Outflow boundaries from mountain convection: None, Weak, Strong",
    "MorningBound": "Morning boundary features: None, Weak, Strong",
    "Boundaries": "Boundary convergence features: None, Weak, Strong",
    "CldShadeConv": "Cloud shading from convection: None, Some, Much",
    "CompPlFcst": "Composite plains forecast: AreaNotAct, Actnvd, LissTyp, Slght, Mdrt, Strng",
    "CapChange": "CAPE change during afternoon: Decreasing, LittleChange, Increasing",
    "LoLevMoworture": "Low-level moisture: VeryWet, Wet, Neutral, Dry",
    "InsChange": "Instability change during afternoon: Decreasing, LittleChange, Increasing",
    "MountainFcst": "Mountain convection forecast: XNIL, SIG",
    "Date": "Date/season category affecting weather patterns",
    "Scenario": "Meteorological scenario type influencing weather development",
    "ScenRelAMCIN": "Scenario-relative AM convective inhibition: AB, LI, HI",
    "MorningCIN": "Morning convective inhibition: None, Weak, Moderate, Strong",
    "AMCINInScen": "AM CIN relative to scenario expectations: LessUnworble, Average, MoreUnworble",
    "CapInScen": "CAPE relative to scenario expectations: LessThanAv, Average, MoreThanAv",
    "ScenRelAMIns": "Scenario-relative AM instability: AB, LI, HI",
    "LIfr12ZDENSd": "Lifted index from 12Z Denver sounding: LIGt0, NIL_to_M4, LIM4_to_M8, LILe_M8",
    "AMDewptCalPl": "AM dewpoint on the Colorado plains: Instability, ShdwInst, DryLine, Moist",
    "AMInsWliScen": "AM instability within scenario: Less, Average, More",
    "InsSclInScen": "Instability scale within scenario: LessThanAv, Average, MoreThanAv",
    "ScenRel3_4": "Scenario-relative 3-4 factor: AB, LI, HI",
    "LatestCIN": "Latest CIN (convective inhibition): None, Weak, Moderate, Strong",
    "LLIW": "Low-Level Instability Winds: Unfav, Neut, Fav, VFav",
    "CurPropConv": "Current propensity for convection: None, Weak, Moderate, Strong",
    "ScnRelPlFcst": "Scenario-relative plains forecast: AB, LI, HI",
    "PlainsFcst": "Plains convection forecast: XNIL, SIG",
    "N0_7muVerMo": "0-7 km mean vertical motion: StrongUp, WeakUp, Neutral, Down",
    "SfcWndShfDis": "Surface wind shift distance: LI, HI",
    "SynForcng": "Synoptic forcing: SigNeg, Neg, Neut, Pos, SigPos",
    "TempDis": "Temperature discontinuity: QStatworry, Cont, Disc",
    "WindAloft": "Winds aloft characteristics: LV, SV, Mod, Str",
    "WindFieldMt": "Wind field over mountains: Unfav, Neut, Fav",
    "WindFieldPln": "Wind field over plains: Unfav, Neut, Fav",
    "MvmtFeatures": "Movement of weather features: Retro, Quasi, Forward",
    "RHRatio": "Relative humidity ratio (surface to midlevels): MoworLess, Drier, Moister",
    "MeanRH": "Mean relative humidity: Low, Medium, High",
    "LowLLapse": "Low-level lapse rate: Small, Medium, Large",
    "MidLLapse": "Mid-level lapse rate: Small, Medium, Large",
    "Dewpoints": "Surface dewpoints: LowEverworhere, LowAtStation, LowSClworworher, Moderate, High",
    "R5Fcst": "Region 5 forecast: XNIL, SIG",
}

# Hepar2 network variable descriptions (liver disease diagnosis)
HEPAR2_DESCRIPTIONS = {
    "ChHepatitis": "Chronic hepatitis (viral liver inflammation): Present, Absent",
    "Cirrhosis": "Liver cirrhosis (scarring and fibrosis): Present, Absent",
    "PBC": "Primary biliary cholangitis (autoimmune bile duct disease): Present, Absent",
    "THepatitis": "Toxic hepatitis (drug/chemical-induced liver damage): Present, Absent",
    "Steatosis": "Hepatic steatosis (fatty liver disease): Present, Absent",
    "RHepatitis": "Reactive hepatitis (secondary liver inflammation): Present, Absent",
    "Hyperbilirubinemia": "Elevated bilirubin in blood: Present, Absent",
    "gallstones": "Gallstones (cholelithiasis): Present, Absent",
    "fibrosis": "Liver fibrosis (tissue scarring): Present, Absent",
    "vh_amn": "Viral hepatitis marker (amnesia/history): Present, Absent",
    "transfusion": "History of blood transfusion: Yes, No",
    "injections": "History of injections/needle exposure: Yes, No",
    "hepatotoxic": "Exposure to hepatotoxic substances: Yes, No",
    "alcoholism": "History of alcoholism: Yes, No",
    "obesity": "Obesity status: Yes, No",
    "sex": "Biological sex: Male, Female",
    "age": "Age category: Young, Adult, Elderly",
    "bilirubin": "Serum bilirubin level: Normal, Elevated, Very_High",
    "phosphatase": "Alkaline phosphatase level: Normal, Elevated",
    "proteins": "Serum protein level: Normal, Low",
    "edema": "Peripheral edema: Present, Absent",
    "platelet": "Platelet count: Normal, Low",
    "inr": "INR (prothrombin time): Normal, Prolonged",
    "alcohol": "Current alcohol use: Yes, No",
    "encephalopathy": "Hepatic encephalopathy: Present, Absent",
    "alt": "ALT (alanine aminotransferase) level: Normal, Elevated, Very_High",
    "ast": "AST (aspartate aminotransferase) level: Normal, Elevated, Very_High",
    "ggtp": "GGT (gamma-glutamyl transferase) level: Normal, Elevated",
    "cholesterol": "Serum cholesterol level: Normal, Elevated, Low",
    "triglycerides": "Serum triglyceride level: Normal, Elevated",
    "ESR": "Erythrocyte sedimentation rate: Normal, Elevated",
    "hbsag": "Hepatitis B surface antigen: Positive, Negative",
    "hbsag_anti": "Hepatitis B surface antibody: Positive, Negative",
    "hbc_anti": "Hepatitis B core antibody: Positive, Negative",
    "hcv_anti": "Hepatitis C antibody: Positive, Negative",
    "hbeag": "Hepatitis B e-antigen: Positive, Negative",
    "ama": "Anti-mitochondrial antibody: Positive, Negative",
    "le_cells": "LE cells (lupus erythematosus cells): Present, Absent",
    "joints": "Joint symptoms: Present, Absent",
    "pain": "Abdominal pain: Present, Absent",
    "pain_ruq": "Right upper quadrant pain: Present, Absent",
    "pressure_ruq": "Right upper quadrant pressure/tenderness: Present, Absent",
    "fatigue": "Fatigue: Present, Absent",
    "hepatomegaly": "Hepatomegaly (enlarged liver): Present, Absent",
    "hepatalgia": "Liver pain (hepatalgia): Present, Absent",
    "spleen": "Splenomegaly (enlarged spleen): Present, Absent",
    "spiders": "Spider angiomas (spider nevi): Present, Absent",
    "albumin": "Serum albumin level: Normal, Low",
    "edge": "Liver edge palpation: Normal, Firm, Hard",
    "irregular_liver": "Irregular liver surface: Yes, No",
    "palms": "Palmar erythema: Present, Absent",
    "itching": "Pruritus (itching): Present, Absent",
    "skin": "Skin changes (jaundice/discoloration): Present, Absent",
    "jaundice": "Jaundice (icterus): Present, Absent",
    "upper_pain": "Upper abdominal pain: Present, Absent",
    "fat": "Fatty food intolerance: Present, Absent",
    "flatulence": "Flatulence: Present, Absent",
    "amylase": "Serum amylase level: Normal, Elevated",
    "anorexia": "Anorexia (loss of appetite): Present, Absent",
    "nausea": "Nausea: Present, Absent",
    "urea": "Blood urea level: Normal, Elevated",
    "density": "Urine specific gravity: Normal, Low",
    "consciousness": "Level of consciousness: Normal, Altered",
    "choledocholithotomy": "History of choledocholithotomy: Yes, No",
    "carcinoma": "Hepatocellular carcinoma: Present, Absent",
}

# Cancer network variable descriptions (lung cancer diagnosis)
CANCER_DESCRIPTIONS = {
    "Pollution": "Level of environmental pollution exposure: low, high",
    "Smoker": "Whether the patient is a smoker: True, False",
    "Cancer": "Whether the patient has lung cancer: True, False",
    "Xray": "Result of a chest X-ray examination: positive, negative",
    "Dyspnoea": "Whether the patient experiences shortness of breath: True, False",
}

# Water network variable descriptions (wastewater treatment)
# 8 measurements x 4 time slices (12:00, 12:15, 12:30, 12:45)
WATER_DESCRIPTIONS = {
    "C_NI_12_00": "Nitrification capacity index at 12:00",
    "C_NI_12_15": "Nitrification capacity index at 12:15",
    "C_NI_12_30": "Nitrification capacity index at 12:30",
    "C_NI_12_45": "Nitrification capacity index at 12:45",
    "CKNI_12_00": "Kjeldahl nitrogen in influent (incoming wastewater) at 12:00",
    "CKNI_12_15": "Kjeldahl nitrogen in influent (incoming wastewater) at 12:15",
    "CKNI_12_30": "Kjeldahl nitrogen in influent (incoming wastewater) at 12:30",
    "CKNI_12_45": "Kjeldahl nitrogen in influent (incoming wastewater) at 12:45",
    "CBODD_12_00": "Biochemical oxygen demand in denitrification tank at 12:00",
    "CBODD_12_15": "Biochemical oxygen demand in denitrification tank at 12:15",
    "CBODD_12_30": "Biochemical oxygen demand in denitrification tank at 12:30",
    "CBODD_12_45": "Biochemical oxygen demand in denitrification tank at 12:45",
    "CKND_12_00": "Kjeldahl nitrogen in denitrification tank at 12:00",
    "CKND_12_15": "Kjeldahl nitrogen in denitrification tank at 12:15",
    "CKND_12_30": "Kjeldahl nitrogen in denitrification tank at 12:30",
    "CKND_12_45": "Kjeldahl nitrogen in denitrification tank at 12:45",
    "CNOD_12_00": "Nitrate concentration in denitrification tank at 12:00",
    "CNOD_12_15": "Nitrate concentration in denitrification tank at 12:15",
    "CNOD_12_30": "Nitrate concentration in denitrification tank at 12:30",
    "CNOD_12_45": "Nitrate concentration in denitrification tank at 12:45",
    "CBODN_12_00": "Biochemical oxygen demand in nitrification tank at 12:00",
    "CBODN_12_15": "Biochemical oxygen demand in nitrification tank at 12:15",
    "CBODN_12_30": "Biochemical oxygen demand in nitrification tank at 12:30",
    "CBODN_12_45": "Biochemical oxygen demand in nitrification tank at 12:45",
    "CKNN_12_00": "Kjeldahl nitrogen in nitrification tank at 12:00",
    "CKNN_12_15": "Kjeldahl nitrogen in nitrification tank at 12:15",
    "CKNN_12_30": "Kjeldahl nitrogen in nitrification tank at 12:30",
    "CKNN_12_45": "Kjeldahl nitrogen in nitrification tank at 12:45",
    "CNON_12_00": "Nitrate concentration in nitrification tank at 12:00",
    "CNON_12_15": "Nitrate concentration in nitrification tank at 12:15",
    "CNON_12_30": "Nitrate concentration in nitrification tank at 12:30",
    "CNON_12_45": "Nitrate concentration in nitrification tank at 12:45",
}

# Mildew network variable descriptions (agricultural crop disease management)
# Temporal model with period suffixes _0 through _4
MILDEW_DESCRIPTIONS = {
    "lai_0": "Leaf area index (canopy density measure) at period 0",
    "lai_1": "Leaf area index (canopy density measure) at period 1",
    "lai_2": "Leaf area index (canopy density measure) at period 2",
    "lai_3": "Leaf area index (canopy density measure) at period 3",
    "lai_4": "Leaf area index (canopy density measure) at period 4",
    "dm_1": "Accumulated dry matter biomass at period 1",
    "dm_2": "Accumulated dry matter biomass at period 2",
    "dm_3": "Accumulated dry matter biomass at period 3",
    "dm_4": "Accumulated dry matter biomass at period 4",
    "foto_1": "Rate of photosynthetic production at period 1",
    "foto_2": "Rate of photosynthetic production at period 2",
    "foto_3": "Rate of photosynthetic production at period 3",
    "foto_4": "Rate of photosynthetic production at period 4",
    "meldug_1": "Powdery mildew infection severity at period 1",
    "meldug_2": "Powdery mildew infection severity at period 2",
    "meldug_3": "Powdery mildew infection severity at period 3",
    "meldug_4": "Powdery mildew infection severity at period 4",
    "mikro_1": "Microclimate conditions in crop canopy at period 1",
    "mikro_2": "Microclimate conditions in crop canopy at period 2",
    "mikro_3": "Microclimate conditions in crop canopy at period 3",
    "middel_1": "Fungicide treatment dose applied at period 1",
    "middel_2": "Fungicide treatment dose applied at period 2",
    "middel_3": "Fungicide treatment dose applied at period 3",
    "straaling_1": "Incoming solar radiation at period 1",
    "straaling_2": "Incoming solar radiation at period 2",
    "straaling_3": "Incoming solar radiation at period 3",
    "straaling_4": "Incoming solar radiation at period 4",
    "temp_1": "Mean air temperature at period 1",
    "temp_2": "Mean air temperature at period 2",
    "temp_3": "Mean air temperature at period 3",
    "temp_4": "Mean air temperature at period 4",
    "nedboer_1": "Precipitation amount at period 1",
    "nedboer_2": "Precipitation amount at period 2",
    "nedboer_3": "Precipitation amount at period 3",
    "udbytte": "Final grain yield",
}

# Win95pts network variable descriptions (Windows 95 printer troubleshooting)
WIN95PTS_DESCRIPTIONS = {
    "AppOK": "Application software integrity",
    "DataFile": "Data file integrity",
    "DskLocal": "Available local disk space",
    "PrtSpool": "Print spooler enabled/disabled",
    "PrtOn": "Printer power state",
    "PrtPaper": "Paper presence in printer",
    "NetPrint": "Network vs local printer",
    "PrtDriver": "Printer driver installed correctly",
    "PrtThread": "Print thread status",
    "DrvSet": "Driver settings correctness",
    "DrvOK": "Driver software integrity",
    "PrtSel": "Printer selected as active",
    "PrtPath": "Network printer path configuration",
    "NtwrkCnfg": "Network configuration settings",
    "PTROFFLINE": "Printer online/offline state",
    "PrtCbl": "Printer cable connection",
    "PrtPort": "Printer port configuration",
    "DSApplctn": "Application type (DOS vs Windows)",
    "PrtMpTPth": "Print mapping path to network printer",
    "PrtMem": "Printer memory capacity",
    "PrtTimeOut": "Printer timeout setting",
    "TnrSpply": "Toner supply level",
    "PgOrnttnOK": "Page orientation setting correctness",
    "PrntngArOK": "Printing area/margins setting",
    "GrphcsRltdDrvrSttngs": "Graphics-related driver settings",
    "EPSGrphc": "Whether document contains EPS graphics",
    "PrtPScript": "Printer PostScript support",
    "TrTypFnts": "Document uses TrueType fonts",
    "FntInstlltn": "Font installation status",
    "PrntrAccptsTrtyp": "Printer accepts TrueType fonts",
    "ScrnFntNtPrntrFnt": "Screen font doesn't match printer font",
    "PrtQueue": "Print queue length",
    "AppData": "Application data generated correctly",
    "EMFOK": "Enhanced Metafile spool file created correctly",
    "GDIIN": "GDI input data correct",
    "GDIOUT": "GDI output rendered correctly",
    "PrtDataOut": "Print data output from spooler correct",
    "PrtFile": "Print-to-file output created",
    "FllCrrptdBffr": "Printer buffer state",
    "PrtData": "Print data received by printer",
    "PC2PRT": "Data path from PC to printer working",
    "DS_LCLOK": "Local data stream OK",
    "DS_NTOK": "Network data stream OK",
    "CblPrtHrdwrOK": "Cable and printer hardware operational",
    "LclOK": "Local printing subsystem OK",
    "NetOK": "Network printing subsystem OK",
    "CmpltPgPrntd": "Complete page printed without truncation",
    "AppDtGnTm": "Application data generation time",
    "PrntPrcssTm": "Print processing time",
    "DeskPrntSpd": "Desktop-to-printer speed",
    "NtSpd": "Network printing speed",
    "LclGrbld": "Local printing produces garbled output",
    "NtGrbld": "Network printing produces garbled output",
    "GrbldOtpt": "Overall garbled output detected",
    "TTOK": "TrueType font rendering OK",
    "NnTTOK": "Non-TrueType font rendering OK",
    "NnPSGrphc": "Non-PostScript graphics rendering OK",
    "PSGRAPHIC": "PostScript graphics rendering OK",
    "AvlblVrtlMmry": "Available virtual memory",
    "PSERRMEM": "PostScript memory error status",
    "GrbldPS": "PostScript output garbled",
    "IncmpltPS": "PostScript output incomplete",
    "HrglssDrtnAftrPrnt": "Hourglass cursor duration after print",
    "REPEAT": "Output repetition pattern",
    "TstpsTxt": "Test PostScript text output",
    "PrtStatPaper": "Printer paper status indicator",
    "PrtStatToner": "Printer toner status indicator",
    "PrtStatMem": "Printer memory status indicator",
    "PrtStatOff": "Printer offline status indicator",
    "PrtIcon": "Printer icon appearance in Windows",
    "Problem1": "No output from printer",
    "Problem2": "Printing takes too long",
    "Problem3": "Incomplete page printed",
    "Problem4": "Graphics don't print correctly",
    "Problem5": "Font/text doesn't print correctly",
    "Problem6": "Garbled output",
}

# Network configurations
NETWORK_CONFIGS = {
    "insurance": {
        "pgmpy_name": "insurance",
        "descriptions": None,  # set below after VAR_DESCRIPTIONS is defined
        "test_nodes": ["DrivingSkill", "DrivQuality", "Accident", "CarValue", "SocioEcon"],
        "domain": "insurance",
    },
    "alarm": {
        "pgmpy_name": "alarm",
        "descriptions": ALARM_DESCRIPTIONS,
        "test_nodes": ["VENTLUNG", "CATECHOL", "HR", "LVEDVOLUME", "VENTALV"],
        "domain": "medical monitoring",
    },
    "sachs": {
        "pgmpy_name": "sachs",
        "descriptions": SACHS_DESCRIPTIONS,
        "test_nodes": ["PKA", "PKC", "Mek", "Erk", "Raf", "Akt", "PIP3", "PIP2", "Jnk", "P38", "Plcg"],
        "domain": "protein signaling",
    },
    "child": {
        "pgmpy_name": "child",
        "descriptions": CHILD_DESCRIPTIONS,
        "test_nodes": ["Disease", "LungParench", "HypoxiaInO2", "CardiacMixing", "Sick", "HypDistrib", "ChestXray", "Grunting"],
        "domain": "congenital heart disease diagnosis",
    },
    "asia": {
        "pgmpy_name": "asia",
        "descriptions": ASIA_DESCRIPTIONS,
        "test_nodes": [],  # all d>=2 via --all-nodes
        "domain": "pulmonary medicine",
    },
    "hailfinder": {
        "pgmpy_name": "hailfinder",
        "descriptions": HAILFINDER_DESCRIPTIONS,
        "test_nodes": [],  # all d>=2 via --all-nodes
        "domain": "severe weather forecasting",
    },
    "hepar2": {
        "pgmpy_name": "hepar2",
        "descriptions": HEPAR2_DESCRIPTIONS,
        "test_nodes": [],  # all d>=2 via --all-nodes
        "domain": "liver disease diagnosis",
    },
    "cancer": {
        "pgmpy_name": "cancer",
        "descriptions": CANCER_DESCRIPTIONS,
        "test_nodes": [],
        "domain": "lung cancer diagnosis",
    },
    "water": {
        "pgmpy_name": "water",
        "descriptions": WATER_DESCRIPTIONS,
        "test_nodes": [],
        "domain": "wastewater treatment",
    },
    "mildew": {
        "pgmpy_name": "mildew",
        "descriptions": MILDEW_DESCRIPTIONS,
        "test_nodes": [],
        "domain": "agricultural crop disease management",
    },
    "win95pts": {
        "pgmpy_name": "win95pts",
        "descriptions": WIN95PTS_DESCRIPTIONS,
        "test_nodes": [],
        "domain": "printer troubleshooting",
    },
}

# Test nodes selected for structural diversity (from raw_idea.md)
TEST_NODES = ["DrivingSkill", "DrivQuality", "Accident", "CarValue", "SocioEcon"]


@dataclass
class OrientationResult:
    """Result of a single orientation attempt for one edge."""
    edge: tuple  # (u, v) — ground truth direction
    predicted: str  # "u->v", "v->u", "uncertain"
    correct: bool
    condition: str  # "per_edge" or "ego_graph"
    pass_idx: int
    center_node: str  # which test node's ego this came from


# ── Data Setup ─────────────────────────────────────────────────────

def load_network(name="insurance"):
    """Load a Bayesian network ground truth from pgmpy."""
    from pgmpy.utils import get_example_model
    model = get_example_model(name)
    gt_edges = set(model.edges())
    return model, gt_edges


def sample_data(model, n=N_SAMPLES, seed=SEED_DATA):
    """Sample observational data from the Insurance network."""
    from pgmpy.sampling import BayesianModelSampling
    np.random.seed(seed)
    sampler = BayesianModelSampling(model)
    data = sampler.forward_sample(size=n, seed=seed)
    return data


def estimate_skeleton(data, alpha=0.05):
    """Run PC algorithm to estimate skeleton + separating sets."""
    from pgmpy.estimators import PC as PCEstimator
    from pgmpy.estimators.CITests import chi_square
    from functools import partial

    # pgmpy 1.0.0 has a bug where build_skeleton passes data=None
    # to get_ci_test. Work around by passing a pre-bound callable.
    ci_func = partial(chi_square, data=data, boolean=True)
    est = PCEstimator(data)
    skeleton, sep_sets = est.build_skeleton(
        ci_test=ci_func,
        significance_level=alpha,
        show_progress=False,
    )
    return skeleton, sep_sets


def get_ego_graph_info(node, skeleton, sep_sets, gt_edges):
    """Extract ego-graph information for a node.

    Returns:
        neighbors: list of neighbor names
        neighbor_adjacencies: dict of which neighbors are adjacent to each other
        ci_facts: list of CI fact strings for the ego
        edges_to_orient: list of (u, v) edges incident to this node (in GT direction)
    """
    neighbors = list(skeleton.neighbors(node))

    # Neighbor-neighbor adjacencies
    neighbor_adj = {}
    for i, n1 in enumerate(neighbors):
        for n2 in neighbors[i+1:]:
            key = (n1, n2)
            adjacent = skeleton.has_edge(n1, n2)
            neighbor_adj[key] = adjacent

    # CI / separating set facts
    ci_facts = []
    for (n1, n2), is_adj in neighbor_adj.items():
        if not is_adj:
            # Find separating set — pgmpy uses frozenset keys
            sep = None
            for key_format in [(n1, n2), (n2, n1), frozenset({n1, n2})]:
                if key_format in sep_sets:
                    sep = sep_sets[key_format]
                    break

            if sep is not None:
                sep_str = ", ".join(sorted(sep)) if sep else "empty set"
                in_sep = node in sep if sep else False
                ci_facts.append({
                    "pair": (n1, n2),
                    "separated_by": sep_str,
                    "center_in_sep": in_sep,
                    "type": "non-collider" if in_sep else "collider"
                })

    # Edges to orient (map to GT direction)
    edges_to_orient = []
    for nbr in neighbors:
        if (node, nbr) in gt_edges:
            edges_to_orient.append((node, nbr))
        elif (nbr, node) in gt_edges:
            edges_to_orient.append((nbr, node))
        else:
            # Edge in skeleton but not in GT — skeleton error
            edges_to_orient.append((node, nbr))  # arbitrary direction

    return neighbors, neighbor_adj, ci_facts, edges_to_orient


# ── Name Resolution ────────────────────────────────────────────────

# Global flags set by run_mve; prompt builders read them.
_use_disguised = False
_domain_text = "an insurance domain"


def display_name(real_name):
    """Return the display name for a variable (real or disguised)."""
    if _use_disguised:
        return DISGUISED_NAMES.get(real_name, real_name)
    return real_name


# ── Prompt Construction ────────────────────────────────────────────

def build_per_edge_prompt(node, neighbor, ci_facts, sep_sets):
    """Build a per-edge prompt (Condition A: MosaCD-style)."""
    dn = display_name(node)
    dn_nbr = display_name(neighbor)
    node_desc = VAR_DESCRIPTIONS.get(node, node)
    nbr_desc = VAR_DESCRIPTIONS.get(neighbor, neighbor)

    # Find relevant separating set (pgmpy uses frozenset keys)
    sep_info = ""
    sep = None
    for key_format in [(node, neighbor), (neighbor, node), frozenset({node, neighbor})]:
        if key_format in sep_sets:
            sep = sep_sets[key_format]
            break
    if sep is not None:
        sep_names = ", ".join(sorted(display_name(s) for s in sep)) if sep else "empty set"
        sep_info = f"\nSeparating set: {{{sep_names}}}"

    prompt = f"""You are a causal reasoning expert. Given two variables from a {_domain_text}, determine the causal direction.

Variable 1: {dn} — {node_desc}
Variable 2: {dn_nbr} — {nbr_desc}

These two variables are connected in the causal skeleton (they are not conditionally independent given any subset of other variables).{sep_info}

Which is the correct causal direction? Answer with ONLY one of:
A) {dn} -> {dn_nbr}
B) {dn_nbr} -> {dn}
C) Uncertain

Answer:"""
    return prompt


def build_contrastive_per_edge_prompt(node, neighbor, ci_facts, sep_sets):
    """Build a contrastive per-edge prompt that forces evaluation of both directions.

    Instead of asking 'which direction?', presents both hypotheses and asks
    the model to evaluate evidence for each before deciding. This combats
    overconfident domain-biased answers.
    """
    dn = display_name(node)
    dn_nbr = display_name(neighbor)
    node_desc = VAR_DESCRIPTIONS.get(node, node)
    nbr_desc = VAR_DESCRIPTIONS.get(neighbor, neighbor)

    sep_info = ""
    sep = None
    for key_format in [(node, neighbor), (neighbor, node), frozenset({node, neighbor})]:
        if key_format in sep_sets:
            sep = sep_sets[key_format]
            break
    if sep is not None:
        sep_names = ", ".join(sorted(display_name(s) for s in sep)) if sep else "empty set"
        sep_info = f"\nSeparating set: {{{sep_names}}}"

    prompt = f"""You are a causal reasoning expert. Two variables from a {_domain_text} are connected in the causal skeleton.{sep_info}

Variable 1: {dn} — {node_desc}
Variable 2: {dn_nbr} — {nbr_desc}

Consider both possible causal directions:

HYPOTHESIS A: {dn} causes {dn_nbr}
- What mechanism would support this? Give one sentence.

HYPOTHESIS B: {dn_nbr} causes {dn}
- What mechanism would support this? Give one sentence.

Now evaluate: which hypothesis has stronger support from domain knowledge and the causal structure?

Final answer (ONLY one line): A, B, or C (uncertain)
Answer:"""
    return prompt


def build_enriched_per_edge_prompt(node, neighbor, neighbors, neighbor_adj, ci_facts):
    """Build an enriched per-edge prompt (Condition C: per-edge + ego context).

    Same neighborhood and CI context as the ego prompt, but asks about
    ONE edge at a time. Tests whether the ego advantage comes from
    joint orientation or just from having more context.
    """
    dn = display_name(node)
    dn_nbr = display_name(neighbor)
    node_desc = VAR_DESCRIPTIONS.get(node, node)
    nbr_desc = VAR_DESCRIPTIONS.get(neighbor, neighbor)

    # Build other-neighbor list (exclude the target neighbor)
    other_nbrs = [n for n in neighbors if n != neighbor]
    other_lines = []
    for i, nbr in enumerate(other_nbrs, 1):
        other_desc = VAR_DESCRIPTIONS.get(nbr, nbr)
        other_lines.append(f"  {i}. {display_name(nbr)} — {other_desc}")
    other_block = "\n".join(other_lines) if other_lines else "  (none)"

    # Build relevant CI facts
    ci_lines = []
    for cf in ci_facts:
        n1, n2 = cf["pair"]
        dn1, dn2 = display_name(n1), display_name(n2)
        if neighbor in (n1, n2) or node in (n1, n2):
            sep_names = ", ".join(sorted(display_name(s) for s in cf["separated_by"].split(", "))) if cf["separated_by"] != "empty set" else "empty set"
            ci_lines.append(
                f"  - {dn1} and {dn2}: separated by {{{sep_names}}} "
                f"({cf['type']} at {dn})"
            )
    ci_block = "\n".join(ci_lines) if ci_lines else "  (no relevant CI facts)"

    prompt = f"""You are a causal reasoning expert. Given two variables from a {_domain_text}, determine the causal direction. You are also given the local neighborhood context for additional reasoning.

TARGET EDGE: {dn} — {node_desc}  ↔  {dn_nbr} — {nbr_desc}

OTHER NEIGHBORS of {dn} (also connected in the skeleton):
{other_block}

RELEVANT CONDITIONAL INDEPENDENCE FACTS:
{ci_block}

Consider:
1. Domain knowledge: which variable plausibly causes the other?
2. The neighborhood context: how does the target edge relate to other connections?
3. CI constraints: if {dn} is in a separating set (non-collider), the two separated variables should NOT both point into {dn}.

Which is the correct causal direction? Answer with ONLY one of:
A) {dn} -> {dn_nbr}
B) {dn_nbr} -> {dn}
C) Uncertain

Answer:"""
    return prompt


def build_ego_graph_prompt(node, neighbors, neighbor_adj, ci_facts):
    """Build an ego-graph prompt (Condition B: LOCALE-style)."""
    dn = display_name(node)
    node_desc = VAR_DESCRIPTIONS.get(node, node)

    # Build neighbor list
    nbr_lines = []
    for i, nbr in enumerate(neighbors, 1):
        nbr_desc = VAR_DESCRIPTIONS.get(nbr, nbr)
        nbr_lines.append(f"  {i}. {display_name(nbr)} — {nbr_desc}")
    nbr_block = "\n".join(nbr_lines)

    # Build cross-neighbor info
    cross_lines = []
    for (n1, n2), is_adj in neighbor_adj.items():
        dn1, dn2 = display_name(n1), display_name(n2)
        if is_adj:
            cross_lines.append(f"  - {dn1} and {dn2}: ADJACENT (connected in skeleton)")
        else:
            # Find CI fact
            for cf in ci_facts:
                if cf["pair"] == (n1, n2) or cf["pair"] == (n2, n1):
                    sep_names = ", ".join(sorted(display_name(s) for s in cf["separated_by"].split(", "))) if cf["separated_by"] != "empty set" else "empty set"
                    cross_lines.append(
                        f"  - {dn1} and {dn2}: NOT adjacent, separated by {{{sep_names}}} "
                        f"({cf['type']} at {dn})"
                    )
                    break
            else:
                cross_lines.append(f"  - {dn1} and {dn2}: NOT adjacent")
    cross_block = "\n".join(cross_lines) if cross_lines else "  (no cross-neighbor pairs)"

    # Build edge list for response
    edge_lines = []
    for nbr in neighbors:
        edge_lines.append(f"  - {dn} -- {display_name(nbr)}: direction?")
    edge_block = "\n".join(edge_lines)

    prompt = f"""You are a causal reasoning expert. Given a central variable and its neighborhood in a causal skeleton from a {_domain_text}, determine the causal direction of each edge.

CENTER NODE: {dn} — {node_desc}

NEIGHBORS ({len(neighbors)} connected variables):
{nbr_block}

CROSS-NEIGHBOR RELATIONSHIPS:
{cross_block}

EDGES TO ORIENT:
{edge_block}

For each edge, consider:
1. Domain knowledge: which variable plausibly causes the other?
2. Local consistency: are the directions consistent with each other and the CI evidence?
3. If {dn} appears in a separating set (non-collider), it cannot have both neighbors pointing into it for that triple.
4. If {dn} is NOT in a separating set (collider), both neighbors should point into it for that triple.

For EACH edge, answer with the direction. Use this exact format, one line per edge:
{dn} -> [neighbor] OR [neighbor] -> {dn} OR uncertain

Answer:"""
    return prompt


def compute_data_hints(node, neighbors, data):
    """Compute statistical hints from data for data-informed prompting.

    Returns a dict with:
    - conditional_probs: P(neighbor_mode | node_mode) for each neighbor
    - mutual_info: normalized MI between node and each neighbor
    - asymmetry: Asymmetric dependency measures (higher = more likely parent)
    """
    import pandas as pd
    from collections import Counter

    hints = {}
    node_col = data[node] if node in data.columns else None
    if node_col is None:
        return hints

    for nbr in neighbors:
        nbr_col = data[nbr] if nbr in data.columns else None
        if nbr_col is None:
            continue

        # Compute conditional entropy H(Y|X) and H(X|Y) for asymmetry
        # If H(Y|X) < H(X|Y), then X→Y is more likely (X explains Y better)
        xy_counts = Counter(zip(node_col, nbr_col))
        x_counts = Counter(node_col)
        y_counts = Counter(nbr_col)
        n = len(data)

        # H(Y|X) — entropy of neighbor given node
        h_yx = 0.0
        for (x_val, y_val), count in xy_counts.items():
            p_xy = count / n
            p_x = x_counts[x_val] / n
            if p_xy > 0 and p_x > 0:
                h_yx -= p_xy * np.log2(p_xy / p_x)

        # H(X|Y) — entropy of node given neighbor
        h_xy = 0.0
        for (x_val, y_val), count in xy_counts.items():
            p_xy = count / n
            p_y = y_counts[y_val] / n
            if p_xy > 0 and p_y > 0:
                h_xy -= p_xy * np.log2(p_xy / p_y)

        # Asymmetry: positive means node→nbr is more likely
        asymmetry = h_xy - h_yx

        # Normalized mutual information
        h_x = -sum((c/n) * np.log2(c/n) for c in x_counts.values() if c > 0)
        h_y = -sum((c/n) * np.log2(c/n) for c in y_counts.values() if c > 0)
        mi = h_x - h_xy  # I(X;Y) = H(X) - H(X|Y)
        nmi = mi / max(min(h_x, h_y), 1e-10)

        # Top conditional patterns (for human-readable hints)
        patterns = []
        for x_val in sorted(x_counts.keys(), key=lambda v: -x_counts[v])[:3]:
            y_given_x = Counter()
            for (xv, yv), c in xy_counts.items():
                if xv == x_val:
                    y_given_x[yv] = c
            total = sum(y_given_x.values())
            mode_y = y_given_x.most_common(1)[0]
            pct = mode_y[1] / total * 100
            if pct > 60:  # Only include strong patterns
                patterns.append(f"When {display_name(node)}={x_val}, {display_name(nbr)} is usually {mode_y[0]} ({pct:.0f}%)")

        hints[nbr] = {
            "asymmetry": asymmetry,
            "nmi": nmi,
            "patterns": patterns,
        }

    return hints


def build_ego_graph_prompt_v2(node, neighbors, neighbor_adj, ci_facts):
    """Improved ego prompt (v2): structured CI reasoning + step-by-step.

    Key changes from v1:
    1. Explicitly enumerates CI constraints as rules BEFORE asking for answers
    2. Asks model to reason about each edge individually within ego context
    3. Adds anti-bias instruction to combat domain priors
    4. Still single query (keeps cost advantage)
    """
    dn = display_name(node)
    node_desc = VAR_DESCRIPTIONS.get(node, node)

    # Build neighbor list
    nbr_lines = []
    for i, nbr in enumerate(neighbors, 1):
        nbr_desc = VAR_DESCRIPTIONS.get(nbr, nbr)
        nbr_lines.append(f"  {i}. {display_name(nbr)} — {nbr_desc}")
    nbr_block = "\n".join(nbr_lines)

    # Build CI constraints as explicit rules
    rule_lines = []
    rule_idx = 1
    for (n1, n2), is_adj in neighbor_adj.items():
        dn1, dn2 = display_name(n1), display_name(n2)
        if is_adj:
            rule_lines.append(f"  R{rule_idx}. {dn1} and {dn2} are adjacent (connected by another edge).")
        else:
            for cf in ci_facts:
                if cf["pair"] == (n1, n2) or cf["pair"] == (n2, n1):
                    sep_names = ", ".join(sorted(display_name(s) for s in cf["separated_by"].split(", "))) if cf["separated_by"] != "empty set" else "the empty set"
                    if cf["type"] == "non-collider":
                        rule_lines.append(
                            f"  R{rule_idx}. {dn1} ⊥ {dn2} | {{{sep_names}}} — {dn} is a NON-COLLIDER. "
                            f"This means {dn1} and {dn2} must NOT both point into {dn}."
                        )
                    else:
                        rule_lines.append(
                            f"  R{rule_idx}. {dn1} ⊥ {dn2} | {{{sep_names}}} — {dn} is a COLLIDER. "
                            f"This means {dn1} and {dn2} should both point into {dn}."
                        )
                    break
            else:
                rule_lines.append(f"  R{rule_idx}. {dn1} and {dn2} are not adjacent (no direct connection).")
        rule_idx += 1
    rules_block = "\n".join(rule_lines) if rule_lines else "  (no structural constraints)"

    # Build edge list
    edge_lines = []
    for nbr in neighbors:
        edge_lines.append(f"  - {dn} -- {display_name(nbr)}")
    edge_block = "\n".join(edge_lines)

    prompt = f"""You are a causal structure learning expert. Given a variable and its neighborhood in a causal skeleton, orient each edge using BOTH statistical constraints and domain knowledge.

IMPORTANT: The statistical constraints below are derived from data and are reliable. When domain intuition conflicts with statistical constraints, the constraints take priority.

CENTER NODE: {dn} — {node_desc}

NEIGHBORS ({len(neighbors)} variables):
{nbr_block}

STATISTICAL CONSTRAINTS (from conditional independence tests):
{rules_block}

EDGES TO ORIENT:
{edge_block}

Apply the constraint rules above, then use domain knowledge for remaining ambiguity. Be concise.

For EACH edge, give ONLY the direction. One per line, no explanation:
{dn} -> [neighbor] OR [neighbor] -> {dn} OR uncertain

Answer:"""
    return prompt


def build_ego_graph_prompt_v3(node, neighbors, neighbor_adj, ci_facts, data_hints):
    """Data-informed ego prompt (v3): v2 + statistical patterns from data.

    Key addition: includes actual conditional probability patterns and
    entropy-based asymmetry hints. Should fix systematic errors where
    domain intuition is wrong but data clearly shows the direction.
    """
    dn = display_name(node)
    node_desc = VAR_DESCRIPTIONS.get(node, node)

    # Build neighbor list with data hints
    nbr_lines = []
    for i, nbr in enumerate(neighbors, 1):
        nbr_desc = VAR_DESCRIPTIONS.get(nbr, nbr)
        line = f"  {i}. {display_name(nbr)} — {nbr_desc}"
        if nbr in data_hints and data_hints[nbr]["nmi"] > 0.05:
            nmi = data_hints[nbr]["nmi"]
            line += f"  [MI with {dn}: {nmi:.2f}]"
        nbr_lines.append(line)
    nbr_block = "\n".join(nbr_lines)

    # Build CI constraints as explicit rules (same as v2)
    rule_lines = []
    rule_idx = 1
    for (n1, n2), is_adj in neighbor_adj.items():
        dn1, dn2 = display_name(n1), display_name(n2)
        if is_adj:
            rule_lines.append(f"  R{rule_idx}. {dn1} and {dn2} are adjacent.")
        else:
            for cf in ci_facts:
                if cf["pair"] == (n1, n2) or cf["pair"] == (n2, n1):
                    sep_names = ", ".join(sorted(display_name(s) for s in cf["separated_by"].split(", "))) if cf["separated_by"] != "empty set" else "the empty set"
                    if cf["type"] == "non-collider":
                        rule_lines.append(
                            f"  R{rule_idx}. {dn1} ⊥ {dn2} | {{{sep_names}}} — {dn} is a NON-COLLIDER. "
                            f"{dn1} and {dn2} must NOT both point into {dn}."
                        )
                    else:
                        rule_lines.append(
                            f"  R{rule_idx}. {dn1} ⊥ {dn2} | {{{sep_names}}} — {dn} is a COLLIDER. "
                            f"{dn1} and {dn2} should both point into {dn}."
                        )
                    break
            else:
                rule_lines.append(f"  R{rule_idx}. {dn1} and {dn2} are not adjacent.")
        rule_idx += 1
    rules_block = "\n".join(rule_lines) if rule_lines else "  (no structural constraints)"

    # Build data patterns block (conditional probabilities only — asymmetry is unreliable)
    data_lines = []
    for nbr in neighbors:
        if nbr in data_hints:
            h = data_hints[nbr]
            # Conditional probability patterns (useful for reasoning, not directional)
            for p in h["patterns"][:2]:
                data_lines.append(f"  - {p}")
    data_block = "\n".join(data_lines) if data_lines else "  (no strong patterns)"

    # Build edge list
    edge_lines = []
    for nbr in neighbors:
        edge_lines.append(f"  - {dn} -- {display_name(nbr)}")
    edge_block = "\n".join(edge_lines)

    prompt = f"""You are a causal structure learning expert. Orient each edge using structural constraints and domain knowledge. Data patterns are provided for context but do NOT directly indicate causal direction.

IMPORTANT: Structural constraints from CI tests are most reliable. Use data patterns to understand variable relationships, NOT to infer direction. Domain knowledge is the tiebreaker.

CENTER NODE: {dn} — {node_desc}

NEIGHBORS ({len(neighbors)} variables):
{nbr_block}

STRUCTURAL CONSTRAINTS (from conditional independence tests):
{rules_block}

DATA PATTERNS (from {N_SAMPLES} observations):
{data_block}

EDGES TO ORIENT:
{edge_block}

Apply constraints first, then check data patterns, then use domain knowledge. Be concise.

For EACH edge, give ONLY the direction. One per line, no explanation:
{dn} -> [neighbor] OR [neighbor] -> {dn} OR uncertain

Answer:"""
    return prompt


# ── LLM Querying ───────────────────────────────────────────────────

def strip_think_blocks(text):
    """Remove thinking blocks from model output.

    Handles:
    1. XML-style <think>...</think>
    2. Qwen3.5-9B pattern: "Thinking Process:...\\n</think>\\n\\nAnswer"
       (starts with plain text but ends with </think> tag)
    3. Plain-text thinking without any tags
    """
    # Pattern 2: Qwen3.5-9B — starts with "Thinking Process:" and has </think> later
    think_end = text.find("</think>")
    if think_end != -1:
        text = text[think_end + len("</think>"):].strip()
        return text

    # Pattern 1: XML-style <think>...</think>
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    return text


def query_llm(client, prompt, temperature=TEMPERATURE, enable_thinking=True):
    """Send a single query to the Qwen endpoint, stripping think blocks."""
    try:
        # Dynamic max_tokens: thinking needs full budget, non-thinking needs minimal
        tokens = MAX_TOKENS if enable_thinking else 500
        kwargs = dict(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=tokens,
            temperature=temperature,
        )
        if not enable_thinking:
            kwargs["extra_body"] = {"chat_template_kwargs": {"enable_thinking": False}}
        response = client.chat.completions.create(**kwargs)
        raw = response.choices[0].message.content.strip()
        return strip_think_blocks(raw)
    except Exception as e:
        print(f"  [LLM error: {e}]")
        return ""


def parse_per_edge_response(response, node, neighbor):
    """Parse per-edge response into a direction.

    Uses display names (which may be disguised) for matching against response.
    Returns direction using real names for ground-truth comparison.
    """
    dn = display_name(node)
    dn_nbr = display_name(neighbor)

    # Work from the last few lines (where the answer typically is)
    lines = [l.strip() for l in response.strip().split("\n") if l.strip()]
    tail = "\n".join(lines[-5:]) if len(lines) > 5 else response
    tail_upper = tail.upper()

    # Check for explicit A/B/C answer in tail
    # Patterns: "A)", "A.", "answer: A", "answer A", standalone "A" at end of line
    if re.search(r'\bA\s*[).]', tail_upper) or f"{dn.upper()} -> {dn_nbr.upper()}" in tail_upper:
        return f"{node}->{neighbor}"
    if re.search(r'\bB\s*[).]', tail_upper) or f"{dn_nbr.upper()} -> {dn.upper()}" in tail_upper:
        return f"{neighbor}->{node}"
    if re.search(r'\bC\s*[).]', tail_upper):
        return "uncertain"

    # Check for contrastive format: "Final answer: A/B/C" or "Answer: A/B/C"
    final_match = re.search(r'(?:FINAL\s+)?ANSWER[:\s]+([ABC])\b', tail_upper)
    if final_match:
        ans = final_match.group(1)
        if ans == "A":
            return f"{node}->{neighbor}"
        elif ans == "B":
            return f"{neighbor}->{node}"
        else:
            return "uncertain"

    # Fall back to full response scan for arrow patterns
    r_lower = response.lower()
    dn_l = dn.lower()
    dn_nbr_l = dn_nbr.lower()

    # Try both display names and real names (model may ignore disguised names)
    for n_l, nn_l in [(dn_l, dn_nbr_l)] + ([(node.lower(), neighbor.lower())] if _use_disguised and (dn != node) else []):
        a_hits = len(re.findall(rf'{re.escape(n_l)}\s*->\s*{re.escape(nn_l)}|{re.escape(n_l)}\s*causes\s*{re.escape(nn_l)}', r_lower))
        b_hits = len(re.findall(rf'{re.escape(nn_l)}\s*->\s*{re.escape(n_l)}|{re.escape(nn_l)}\s*causes\s*{re.escape(n_l)}', r_lower))

        if a_hits > b_hits:
            return f"{node}->{neighbor}"
        if b_hits > a_hits:
            return f"{neighbor}->{node}"
        if a_hits > 0:
            last_a = r_lower.rfind(f"{n_l} ->")
            last_b = r_lower.rfind(f"{nn_l} ->")
            if last_a > last_b:
                return f"{node}->{neighbor}"
            return f"{neighbor}->{node}"

    return "uncertain"


def _try_parse_ego_edge(response, response_lower, name_center, name_nbr, node, nbr):
    """Try to parse a single ego edge direction using given name variants.

    Returns direction string or None if no match found.
    """
    nc_l = name_center.lower()
    nn_l = name_nbr.lower()

    # Forward arrows
    for arrow in [" -> ", " → ", " ——> ", " --> "]:
        if f"{nc_l}{arrow}{nn_l}" in response_lower:
            return f"{node}->{nbr}"
        if f"{nn_l}{arrow}{nc_l}" in response_lower:
            return f"{nbr}->{node}"

    # Reverse arrows
    for arrow in [" <- ", " ← ", " <-- "]:
        if f"{nc_l}{arrow}{nn_l}" in response_lower:
            return f"{nbr}->{node}"
        if f"{nn_l}{arrow}{nc_l}" in response_lower:
            return f"{node}->{nbr}"

    # Exact case arrows
    if f"{name_center} -> {name_nbr}" in response or f"{name_center} → {name_nbr}" in response:
        return f"{node}->{nbr}"
    if f"{name_nbr} -> {name_center}" in response or f"{name_nbr} → {name_center}" in response:
        return f"{nbr}->{node}"
    if f"{name_center} <- {name_nbr}" in response or f"{name_center} ← {name_nbr}" in response:
        return f"{nbr}->{node}"
    if f"{name_nbr} <- {name_center}" in response or f"{name_nbr} ← {name_center}" in response:
        return f"{node}->{nbr}"

    return None


def parse_ego_graph_response(response, node, neighbors):
    """Parse ego-graph response into per-edge directions.

    Tries display names first, then falls back to real names (handles
    cases where the model ignores disguised names and uses real ones).
    """
    results = {}
    dn = display_name(node)
    response_lower = response.lower()

    for nbr in neighbors:
        dn_nbr = display_name(nbr)

        # Try display names first
        direction = _try_parse_ego_edge(response, response_lower, dn, dn_nbr, node, nbr)

        # If display names didn't match and we're using disguised names,
        # fall back to real names (model may ignore V-codes and use domain terms)
        if direction is None and _use_disguised and (dn != node or dn_nbr != nbr):
            direction = _try_parse_ego_edge(response, response_lower, node, nbr, node, nbr)

        if direction is not None:
            results[nbr] = direction
            continue

        # Check for "Parent"/"Child" labels (try both display and real names)
        found = False
        for check_name in [dn_nbr, nbr] if _use_disguised else [dn_nbr]:
            if check_name in response and ("parent" in response_lower or "child" in response_lower):
                for line in response.split("\n"):
                    line_l = line.lower().strip()
                    if check_name.lower() in line_l:
                        if "parent" in line_l:
                            results[nbr] = f"{nbr}->{node}"
                            found = True
                            break
                        elif "child" in line_l:
                            results[nbr] = f"{node}->{nbr}"
                            found = True
                            break
            if found:
                break

        if not found:
            results[nbr] = "uncertain"

    return results


# ── Main Experiment ────────────────────────────────────────────────

def run_mve(args):
    """Run the MVE: ego vs per-edge on Insurance."""

    global N_SAMPLES, K_PASSES, SEED_DATA
    if getattr(args, 'n_samples', None) is not None:
        N_SAMPLES = args.n_samples
    if getattr(args, 'k_passes', None) is not None:
        K_PASSES = args.k_passes
    if getattr(args, 'seed', None) is not None:
        SEED_DATA = args.seed
    pc_alpha = getattr(args, 'alpha', None) or 0.05
    use_debiased = getattr(args, 'debiased', False)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── Network selection ──
    network_name = getattr(args, 'network', 'insurance')
    net_cfg = NETWORK_CONFIGS[network_name]
    global VAR_DESCRIPTIONS, DISGUISED_NAMES, TEST_NODES, _domain_text
    _domain_text = net_cfg["domain"] + " domain"
    if net_cfg["descriptions"] is not None:
        VAR_DESCRIPTIONS = net_cfg["descriptions"]
        DISGUISED_NAMES = {name: f"V{i+1:02d}" for i, name in enumerate(sorted(VAR_DESCRIPTIONS.keys()))}
    # else: use Insurance defaults already defined
    TEST_NODES = net_cfg["test_nodes"]

    print("=" * 60)
    print(f"LOCALE MVE: Ego-graph vs Per-edge on {network_name.title()}")
    print("=" * 60)

    # ── Step 0: Setup ──
    print(f"\n[Step 0] Loading {network_name.title()} network...")
    model, gt_edges = load_network(net_cfg["pgmpy_name"])
    print(f"  Ground truth: {len(model.nodes())} nodes, {len(gt_edges)} edges")

    print(f"\n[Step 0] Sampling {N_SAMPLES} observations (seed={SEED_DATA})...")
    data = sample_data(model, n=N_SAMPLES, seed=SEED_DATA)

    print(f"\n[Step 0] Estimating PC skeleton (alpha={pc_alpha})...")
    skeleton, sep_sets = estimate_skeleton(data, alpha=pc_alpha)
    skel_edges = set(skeleton.edges()) | {(v, u) for u, v in skeleton.edges()}
    n_skel_edges = len(skeleton.edges())
    print(f"  Skeleton: {len(skeleton.nodes())} nodes, {n_skel_edges} undirected edges")

    # ── Step 1: Select test nodes ──
    if getattr(args, 'all_nodes', False):
        # Override: use all skeleton nodes with degree >= 2
        TEST_NODES = sorted([n for n in skeleton.nodes() if len(list(skeleton.neighbors(n))) >= 2],
                           key=lambda n: -len(list(skeleton.neighbors(n))))
        print(f"\n[Step 1] Full coverage: {len(TEST_NODES)} nodes with d>=2")
    print(f"\n[Step 1] Test nodes: {TEST_NODES}")
    for node in TEST_NODES:
        nbrs = list(skeleton.neighbors(node))
        print(f"  {node}: degree={len(nbrs)}, neighbors={nbrs}")

    # Collect all edges to orient across test nodes
    all_test_edges = set()
    node_edges = {}
    for node in TEST_NODES:
        neighbors, neighbor_adj, ci_facts, edges_to_orient = get_ego_graph_info(
            node, skeleton, sep_sets, gt_edges
        )
        node_edges[node] = {
            "neighbors": neighbors,
            "neighbor_adj": neighbor_adj,
            "ci_facts": ci_facts,
            "edges_to_orient": edges_to_orient,
        }
        for e in edges_to_orient:
            all_test_edges.add(tuple(sorted(e)))

    print(f"  Total unique edges across test nodes: {len(all_test_edges)}")

    # ── Step 2: Build prompts ──
    print("\n[Step 2] Building prompts...")

    # ── Step 3: Query LLM ──
    enable_thinking = not getattr(args, 'no_think', False)
    global _use_disguised
    _use_disguised = getattr(args, 'disguise', False)
    think_label = "thinking" if enable_thinking else "non-thinking"
    disguise_label = ", disguised" if _use_disguised else ", real names"
    debias_label = ", debiased" if use_debiased else ""
    print(f"\n[Step 3] Querying LLM ({MODEL}, {think_label}{disguise_label}{debias_label}) with K={K_PASSES} passes...")
    # Thinking mode needs longer timeout (responses can be 3000+ tokens at ~15 tok/s)
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=600.0)

    # Verify endpoint
    try:
        test_resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "Say 'ready'"}],
            max_tokens=10,
            **({"extra_body": {"chat_template_kwargs": {"enable_thinking": False}}} if not enable_thinking else {}),
        )
        print(f"  Endpoint verified: {test_resp.choices[0].message.content.strip()}")
    except Exception as e:
        print(f"  ERROR: Cannot reach endpoint at {BASE_URL}: {e}")
        print("  Make sure vLLM is running. Exiting.")
        return

    # ── Build all jobs upfront ──
    run_enriched = getattr(args, 'enriched', False)
    print("\n  Building query jobs...")
    pe_jobs = []    # (node, k, gt_edge, nbr, prompt)
    ego_jobs = []   # (node, k, neighbors, prompt)
    enr_jobs = []   # (node, k, gt_edge, nbr, prompt) — enriched per-edge

    for node in TEST_NODES:
        info = node_edges[node]
        neighbors = info["neighbors"]
        neighbor_adj = info["neighbor_adj"]
        ci_facts = info["ci_facts"]
        edges_to_orient = info["edges_to_orient"]

        for k in range(K_PASSES):
            shuffled_neighbors = neighbors.copy()
            random.seed(SEED_DATA + k * 100 + TEST_NODES.index(node))
            random.shuffle(shuffled_neighbors)

            # Per-edge jobs (Condition A)
            use_contrastive = getattr(args, 'contrastive', False)
            for gt_edge in edges_to_orient:
                u, v = gt_edge
                nbr = v if u == node else u
                # Answer-order debiasing: swap presentation order on odd passes
                if use_debiased and k % 2 == 1:
                    prompt_node, prompt_nbr = nbr, node
                else:
                    prompt_node, prompt_nbr = node, nbr
                if use_contrastive:
                    prompt = build_contrastive_per_edge_prompt(prompt_node, prompt_nbr, ci_facts, sep_sets)
                else:
                    prompt = build_per_edge_prompt(prompt_node, prompt_nbr, ci_facts, sep_sets)
                pe_jobs.append((prompt_node, k, gt_edge, prompt_nbr, prompt))

            # Ego-graph jobs (Condition B)
            use_v2 = getattr(args, 'ego_v2', False)
            use_v3 = getattr(args, 'ego_v3', False)
            if use_v3:
                data_hints = compute_data_hints(node, neighbors, data)
                prompt = build_ego_graph_prompt_v3(node, shuffled_neighbors, neighbor_adj, ci_facts, data_hints)
            elif use_v2:
                prompt = build_ego_graph_prompt_v2(node, shuffled_neighbors, neighbor_adj, ci_facts)
            else:
                prompt = build_ego_graph_prompt(node, shuffled_neighbors, neighbor_adj, ci_facts)
            ego_jobs.append((node, k, neighbors, prompt))

            # Enriched per-edge jobs (Condition C) — same context as ego, one edge at a time
            if run_enriched:
                for gt_edge in edges_to_orient:
                    u, v = gt_edge
                    nbr = v if u == node else u
                    prompt = build_enriched_per_edge_prompt(
                        node, nbr, neighbors, neighbor_adj, ci_facts
                    )
                    enr_jobs.append((node, k, gt_edge, nbr, prompt))

    total_queries = len(pe_jobs) + len(ego_jobs) + len(enr_jobs)
    use_v2 = getattr(args, 'ego_v2', False)
    if enable_thinking:
        concurrency = 1  # Cloudflare 100s timeout; serial execution minimizes timeouts
    elif use_v2:
        concurrency = 4
    else:
        concurrency = MAX_CONCURRENCY
    conditions = f"{len(pe_jobs)} per-edge + {len(ego_jobs)} ego-graph"
    if enr_jobs:
        conditions += f" + {len(enr_jobs)} enriched"
    print(f"  {conditions} = {total_queries} total queries")
    print(f"  Concurrency: {concurrency}")

    # ── Fire all queries concurrently ──
    results_a = []
    results_b = []
    completed = 0
    t_start = time.time()

    use_temp_ladder = getattr(args, 'temp_ladder', False)

    def get_temp(k):
        if use_temp_ladder:
            return TEMP_LADDER[k % len(TEMP_LADDER)]
        return TEMPERATURE

    def run_pe_job(job):
        node, k, gt_edge, nbr, prompt = job
        resp = query_llm(client, prompt, temperature=get_temp(k), enable_thinking=enable_thinking)
        return job, resp

    def run_ego_job(job):
        node, k, neighbors, prompt = job
        resp = query_llm(client, prompt, temperature=get_temp(k), enable_thinking=enable_thinking)
        return job, resp

    print("\n  Firing per-edge queries...")
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = {pool.submit(run_pe_job, j): j for j in pe_jobs}
        for future in as_completed(futures):
            job, resp = future.result()
            node, k, gt_edge, nbr, prompt = job
            predicted = parse_per_edge_response(resp, node, nbr)
            u, v = gt_edge
            gt_dir = f"{u}->{v}"
            results_a.append(OrientationResult(
                edge=gt_edge, predicted=predicted,
                correct=(predicted == gt_dir),
                condition="per_edge", pass_idx=k, center_node=node,
            ))
            completed += 1
            if completed % 20 == 0:
                elapsed = time.time() - t_start
                print(f"    {completed}/{total_queries} done ({elapsed:.1f}s)")

    print("  Firing ego-graph queries...")
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = {pool.submit(run_ego_job, j): j for j in ego_jobs}
        for future in as_completed(futures):
            job, resp = future.result()
            node, k, neighbors, prompt = job
            ego_preds = parse_ego_graph_response(resp, node, neighbors)
            info = node_edges[node]
            for gt_edge in info["edges_to_orient"]:
                u, v = gt_edge
                nbr = v if u == node else u
                predicted = ego_preds.get(nbr, "uncertain")
                gt_dir = f"{u}->{v}"
                results_b.append(OrientationResult(
                    edge=gt_edge, predicted=predicted,
                    correct=(predicted == gt_dir),
                    condition="ego_graph", pass_idx=k, center_node=node,
                ))
            completed += 1
            if completed % 5 == 0:
                elapsed = time.time() - t_start
                print(f"    {completed}/{total_queries} done ({elapsed:.1f}s)")

    # ── Enriched per-edge (Condition C) ──
    results_c = []
    if enr_jobs:
        print("  Firing enriched per-edge queries...")
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = {pool.submit(run_pe_job, j): j for j in enr_jobs}
            for future in as_completed(futures):
                job, resp = future.result()
                node, k, gt_edge, nbr, prompt = job
                predicted = parse_per_edge_response(resp, node, nbr)
                u, v = gt_edge
                gt_dir = f"{u}->{v}"
                results_c.append(OrientationResult(
                    edge=gt_edge, predicted=predicted,
                    correct=(predicted == gt_dir),
                    condition="enriched_pe", pass_idx=k, center_node=node,
                ))
                completed += 1
                if completed % 20 == 0:
                    elapsed = time.time() - t_start
                    print(f"    {completed}/{total_queries} done ({elapsed:.1f}s)")

    total_queries_a = len(pe_jobs)
    total_queries_b = len(ego_jobs)
    total_queries_c = len(enr_jobs)
    elapsed = time.time() - t_start
    print(f"\n  All queries complete in {elapsed:.1f}s ({total_queries/elapsed:.1f} queries/s)")

    # Per-node progress summary
    for node in TEST_NODES:
        a_correct = sum(1 for r in results_a if r.center_node == node and r.correct)
        a_total = sum(1 for r in results_a if r.center_node == node)
        b_correct = sum(1 for r in results_b if r.center_node == node and r.correct)
        b_total = sum(1 for r in results_b if r.center_node == node)
        line = f"  {node}: PE {a_correct}/{a_total} ({100*a_correct/max(a_total,1):.1f}%), "
        line += f"EGO {b_correct}/{b_total} ({100*b_correct/max(b_total,1):.1f}%)"
        if results_c:
            c_correct = sum(1 for r in results_c if r.center_node == node and r.correct)
            c_total = sum(1 for r in results_c if r.center_node == node)
            line += f", ENR {c_correct}/{c_total} ({100*c_correct/max(c_total,1):.1f}%)"
        print(line)

    # ── Step 4: Analyze ──
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    # Overall accuracy
    acc_a = sum(1 for r in results_a if r.correct) / max(len(results_a), 1)
    acc_b = sum(1 for r in results_b if r.correct) / max(len(results_b), 1)
    unc_a = sum(1 for r in results_a if r.predicted == "uncertain") / max(len(results_a), 1)
    unc_b = sum(1 for r in results_b if r.predicted == "uncertain") / max(len(results_b), 1)

    delta = acc_b - acc_a

    print(f"\nCondition A (per-edge):  {acc_a:.1%} accuracy, {unc_a:.1%} uncertain")
    print(f"Condition B (ego-graph): {acc_b:.1%} accuracy, {unc_b:.1%} uncertain")
    if results_c:
        acc_c = sum(1 for r in results_c if r.correct) / max(len(results_c), 1)
        unc_c = sum(1 for r in results_c if r.predicted == "uncertain") / max(len(results_c), 1)
        print(f"Condition C (enriched):  {acc_c:.1%} accuracy, {unc_c:.1%} uncertain")
        print(f"Delta (B - A):           {delta:+.1%}")
        print(f"Delta (B - C):           {(acc_b - acc_c):+.1%}  [joint vs context-only]")
        print(f"\nQueries: A={total_queries_a}, B={total_queries_b}, C={total_queries_c}")
    else:
        print(f"Delta (B - A):           {delta:+.1%}")
        print(f"\nQueries: A={total_queries_a}, B={total_queries_b} (ratio: {total_queries_a/max(total_queries_b,1):.1f}x)")

    # Per-node breakdown
    print("\nPer-node breakdown:")
    if results_c:
        print(f"{'Node':<15} {'Per-edge':>10} {'Enriched':>10} {'Ego-graph':>10} {'B-A':>8} {'B-C':>8}")
        print("-" * 66)
    else:
        print(f"{'Node':<15} {'Per-edge':>10} {'Ego-graph':>10} {'Delta':>10}")
        print("-" * 48)
    for node in TEST_NODES:
        a_node = [r for r in results_a if r.center_node == node]
        b_node = [r for r in results_b if r.center_node == node]
        acc_a_node = sum(1 for r in a_node if r.correct) / max(len(a_node), 1)
        acc_b_node = sum(1 for r in b_node if r.correct) / max(len(b_node), 1)
        if results_c:
            c_node = [r for r in results_c if r.center_node == node]
            acc_c_node = sum(1 for r in c_node if r.correct) / max(len(c_node), 1)
            print(f"{node:<15} {acc_a_node:>9.1%} {acc_c_node:>9.1%} {acc_b_node:>9.1%} "
                  f"{acc_b_node - acc_a_node:>+7.1%} {acc_b_node - acc_c_node:>+7.1%}")
        else:
            d = acc_b_node - acc_a_node
            print(f"{node:<15} {acc_a_node:>9.1%} {acc_b_node:>9.1%} {d:>+9.1%}")

    # Majority vote accuracy (across K passes)
    print("\nMajority-vote accuracy (across K passes):")
    all_conditions = [("per_edge", results_a), ("ego_graph", results_b)]
    if results_c:
        all_conditions.insert(1, ("enriched_pe", results_c))
    for condition, results in all_conditions:
        edge_votes = {}
        for r in results:
            key = (r.center_node, tuple(sorted(r.edge)))
            if key not in edge_votes:
                edge_votes[key] = {"correct": 0, "total": 0, "gt": r.edge}
            if r.correct:
                edge_votes[key]["correct"] += 1
            edge_votes[key]["total"] += 1

        majority_correct = sum(
            1 for v in edge_votes.values() if v["correct"] > v["total"] / 2
        )
        print(f"  {condition}: {majority_correct}/{len(edge_votes)} edges correct by majority vote "
              f"({100*majority_correct/max(len(edge_votes),1):.1f}%)")

    # Hybrid analysis: ego for d>=3, per-edge for d<3
    if getattr(args, 'hybrid', False):
        print("\nHybrid analysis (ego for d>=3, per-edge for d<3):")
        hybrid_correct = 0
        hybrid_total = 0
        hybrid_queries = 0
        for node in TEST_NODES:
            degree = len(node_edges[node]["neighbors"])
            if degree >= MIN_EGO_DEGREE:
                # Use ego results
                node_results = [r for r in results_b if r.center_node == node]
                source = "ego"
            else:
                # Use per-edge results
                node_results = [r for r in results_a if r.center_node == node]
                source = "pe"
            correct = sum(1 for r in node_results if r.correct)
            total = len(node_results)
            hybrid_correct += correct
            hybrid_total += total
            acc = correct / max(total, 1)
            print(f"  {node} (d={degree}): {source} → {acc:.0%} ({correct}/{total})")
        hybrid_acc = hybrid_correct / max(hybrid_total, 1)
        print(f"  HYBRID OVERALL: {hybrid_acc:.1%} (vs PE {acc_a:.1%}, Ego {acc_b:.1%})")

    # CI violation analysis (for ego-graph: check if predictions violate non-collider constraints)
    print("\nCI consistency check (non-collider violations):")
    ci_conditions = [("per_edge", results_a), ("ego_graph", results_b)]
    if results_c:
        ci_conditions.insert(1, ("enriched_pe", results_c))
    for condition, results in ci_conditions:
        violations = 0
        checks = 0
        for node in TEST_NODES:
            info = node_edges[node]
            for cf in info["ci_facts"]:
                if cf["type"] == "non-collider":
                    n1, n2 = cf["pair"]
                    # Check if both n1->node and n2->node (both parents = collider, violates non-collider)
                    for k in range(K_PASSES):
                        node_results = [r for r in results
                                       if r.center_node == node and r.pass_idx == k]
                        n1_pred = None
                        n2_pred = None
                        for r in node_results:
                            e_sorted = tuple(sorted(r.edge))
                            if n1 in e_sorted and node in e_sorted:
                                n1_pred = r.predicted
                            if n2 in e_sorted and node in e_sorted:
                                n2_pred = r.predicted

                        if n1_pred and n2_pred:
                            checks += 1
                            # Both pointing into node = collider = violation of non-collider
                            if (n1_pred == f"{n1}->{node}" and n2_pred == f"{n2}->{node}"):
                                violations += 1

        print(f"  {condition}: {violations}/{checks} violations ({100*violations/max(checks,1):.1f}%)")

    # Go/No-Go
    print("\n" + "=" * 60)
    delta_pp = delta * 100
    if delta_pp > 10:
        verdict = "STRONG GO — Full build. Target CLeaR 2027."
    elif delta_pp > 5:
        verdict = "GO — Proceed. Focus on structures where phi helps."
    elif delta_pp > 0:
        verdict = "WEAK GO — Value may be in cost savings, not accuracy."
    elif delta_pp > -5:
        verdict = "MARGINAL — Re-examine approach. Consider cost angle."
    else:
        verdict = "NO-GO — Kill this angle."

    print(f"Delta = {delta_pp:+.1f} pp")
    print(f"Verdict: {verdict}")
    print("=" * 60)

    # ── Save results ──
    results_dict = {
        "metadata": {
            "network": network_name,
            "model": MODEL,
            "temperature": TEMPERATURE if not use_temp_ladder else TEMP_LADDER,
            "k_passes": K_PASSES,
            "n_samples": N_SAMPLES,
            "seed": SEED_DATA,
            "test_nodes": TEST_NODES,
            "n_test_edges": len(all_test_edges),
            "n_skeleton_edges": n_skel_edges,
            "n_gt_edges": len(gt_edges),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "disguised_names": _use_disguised,
            "enable_thinking": enable_thinking,
            "ego_prompt_version": "v3" if getattr(args, 'ego_v3', False) else ("v2" if getattr(args, 'ego_v2', False) else "v1"),
            "contrastive_pe": getattr(args, 'contrastive', False),
            "temp_ladder": getattr(args, 'temp_ladder', False),
            "enriched": run_enriched,
            "debiased": use_debiased,
            "pc_alpha": pc_alpha,
        },
        "summary": {
            "acc_per_edge": acc_a,
            "acc_ego_graph": acc_b,
            "delta": delta,
            "delta_pp": delta_pp,
            "uncertain_per_edge": unc_a,
            "uncertain_ego_graph": unc_b,
            "queries_per_edge": total_queries_a,
            "queries_ego_graph": total_queries_b,
            "verdict": verdict,
        },
        "per_node": {},
        "raw_results_a": [
            {"edge": list(r.edge), "predicted": r.predicted, "correct": r.correct,
             "pass_idx": r.pass_idx, "center_node": r.center_node}
            for r in results_a
        ],
        "raw_results_b": [
            {"edge": list(r.edge), "predicted": r.predicted, "correct": r.correct,
             "pass_idx": r.pass_idx, "center_node": r.center_node}
            for r in results_b
        ],
    }

    # Save enriched results (Condition C) if present — fixes XN-006 blocker
    if results_c:
        acc_c = sum(1 for r in results_c if r.correct) / max(len(results_c), 1)
        unc_c = sum(1 for r in results_c if r.predicted == "uncertain") / max(len(results_c), 1)
        results_dict["summary"]["acc_enriched_pe"] = acc_c
        results_dict["summary"]["uncertain_enriched_pe"] = unc_c
        results_dict["summary"]["queries_enriched_pe"] = total_queries_c
        results_dict["raw_results_c"] = [
            {"edge": list(r.edge), "predicted": r.predicted, "correct": r.correct,
             "pass_idx": r.pass_idx, "center_node": r.center_node}
            for r in results_c
        ]

    for node in TEST_NODES:
        a_node = [r for r in results_a if r.center_node == node]
        b_node = [r for r in results_b if r.center_node == node]
        node_info = {
            "degree": len(node_edges[node]["neighbors"]),
            "neighbors": node_edges[node]["neighbors"],
            "ci_facts": node_edges[node]["ci_facts"],
            "gt_edges": [list(e) for e in node_edges[node]["edges_to_orient"]],
            "acc_per_edge": sum(1 for r in a_node if r.correct) / max(len(a_node), 1),
            "acc_ego_graph": sum(1 for r in b_node if r.correct) / max(len(b_node), 1),
        }
        if results_c:
            c_node = [r for r in results_c if r.center_node == node]
            node_info["acc_enriched_pe"] = sum(1 for r in c_node if r.correct) / max(len(c_node), 1)
        results_dict["per_node"][node] = node_info

    out_file = out_dir / "mve_results.json"
    with open(out_file, "w") as f:
        json.dump(results_dict, f, indent=2)
    print(f"\nResults saved to {out_file}")


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(line_buffering=True)  # Ensure output is visible in background mode
    parser = argparse.ArgumentParser(description="LOCALE MVE: Insurance ego vs per-edge")
    parser.add_argument("--output-dir", default="experiments/results/mve",
                       help="Output directory for results")
    parser.add_argument("--no-think", action="store_true",
                       help="Disable thinking mode (faster, less reasoning)")
    parser.add_argument("--disguise", action="store_true",
                       help="Use disguised variable names (V01, V02, ...) to control for memorization")
    parser.add_argument("--network", default="insurance",
                       choices=list(NETWORK_CONFIGS.keys()),
                       help="Which Bayesian network to test on")
    parser.add_argument("--enriched", action="store_true",
                       help="Add Condition C: enriched per-edge (ego context, one edge at a time)")
    parser.add_argument("--ego-v2", action="store_true",
                       help="Use improved ego prompt v2 (structured CI reasoning)")
    parser.add_argument("--temp-ladder", action="store_true",
                       help="Use varied temperatures [0.3,0.5,0.7,0.9,1.1] across K passes")
    parser.add_argument("--hybrid", action="store_true",
                       help="Hybrid mode: ego for d>=3, per-edge for d<3 (post-hoc analysis)")
    parser.add_argument("--ego-v3", action="store_true",
                       help="Use data-informed ego prompt v3 (statistical hints from data)")
    parser.add_argument("--contrastive", action="store_true",
                       help="Use contrastive per-edge prompt (argue both directions)")
    parser.add_argument("--all-nodes", action="store_true",
                       help="Test all nodes with degree >= 2 (full coverage)")
    parser.add_argument("--n-samples", type=int, default=None,
                       help="Override N_SAMPLES for data generation (default: 5000)")
    parser.add_argument("--k-passes", type=int, default=None,
                       help="Override K_PASSES for number of votes (default: 5)")
    parser.add_argument("--alpha", type=float, default=None,
                       help="PC algorithm significance level (default: 0.05)")
    parser.add_argument("--debiased", action="store_true",
                       help="Answer-order debiasing: swap variable order on odd passes")
    parser.add_argument("--seed", type=int, default=None,
                       help="Override SEED_DATA for data sampling (default: 42)")
    args = parser.parse_args()
    run_mve(args)
