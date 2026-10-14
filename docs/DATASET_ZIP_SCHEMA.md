# Schema inventory for `Datasets.zip`

This inventory reads only the first header row of each raw text extract. It contains column names only; no patient records or identifier values are copied into the project.

All five raw text files include a column named `Patient ID`. Keep that field local and use it only to group records during splitting; do not publish it in GitHub or Power BI exports.

## Datasets/RawBrainCancer.txt

67 columns; Patient ID present: **True**.

1. `Age recode with <1 year olds`
2. `Race recode (White, Black, Other)`
3. `Sex`
4. `Year of diagnosis`
5. `Site recode ICD-O-3/WHO 2008`
6. `Behavior code ICD-O-3`
7. `TNM 7/CS v0204+ Schema (thru 2017)`
8. `TNM 7/CS v0204+ Schema recode`
9. `AYA site recode 2020 Revision`
10. `Lymphoid neoplasm recode 2021 Revision`
11. `ICCC site recode 3rd edition/IARC 2017`
12. `Site recode ICD-O-3 2023 Revision`
13. `Site recode ICD-O-3 2023 Revision Expanded`
14. `Primary Site`
15. `Histologic Type ICD-O-3`
16. `Grade Recode (thru 2017)`
17. `Laterality`
18. `Grade Clinical (2018+)`
19. `Grade Pathological (2018+)`
20. `Diagnostic Confirmation`
21. `ICD-O-3 Hist/behav`
22. `ICD-O-3 Hist/behav, malignant`
23. `Histology recode - broad groupings`
24. `ICCC site recode extended 3rd edition/IARC 2017`
25. `Site recode ICD-O-3/WHO 2008 (for SIRs)`
26. `Site recode - rare tumors`
27. `RX Summ--Surg Prim Site (1998+)`
28. `RX Summ--Scope Reg LN Sur (2003+)`
29. `RX Summ--Surg Oth Reg/Dis (2003+)`
30. `RX Summ--Surg/Rad Seq`
31. `Reason no cancer-directed surgery`
32. `Radiation recode`
33. `Chemotherapy recode (yes, no/unk)`
34. `Scope of reg lymph nd surg (1998-2002)`
35. `RX Summ--Reg LN Examined (1998-2002)`
36. `Surgery of oth reg/dis sites (1998-2002)`
37. `Site specific surgery (1973-1997 varying detail by year and site)`
38. `Radiation to Brain or CNS Recode (1988-1997)`
39. `RX Summ--Systemic/Sur Seq (2007+)`
40. `Time from diagnosis to treatment in days recode`
41. `Gleason Patterns Clinical Recode (2010+)`
42. `Gleason Patterns Pathological Recode (2010+)`
43. `Gleason Score Clinical Recode (2010+)`
44. `Gleason Score Pathological Recode (2010+)`
45. `PSA Lab Value Recode (2010+)`
46. `Tumor Size Over Time Recode (1988+)`
47. `COD to site recode`
48. `SEER cause-specific death classification`
49. `SEER other cause of death classification`
50. `Survival months`
51. `Survival months flag`
52. `COD to site rec KM`
53. `COD to site recode ICD-O-3 2023 Revision`
54. `COD to site recode ICD-O-3 2023 Revision Expanded (1999+)`
55. `Vital status recode (study cutoff used)`
56. `Total number of in situ/malignant tumors for patient`
57. `Total number of benign/borderline tumors for patient`
58. `Race recode (W, B, AI, API)`
59. `Origin recode NHIA (Hispanic, Non-Hisp)`
60. `Race and origin recode (NHW, NHB, NHAIAN, NHAPI, Hispanic)`
61. `Race/ethnicity`
62. `Year of follow-up recode`
63. `Year of death recode`
64. `Patient ID`
65. `Marital status at diagnosis`
66. `Median household income inflation adj to 2022`
67. `Rural-Urban Continuum Code`

## Datasets/RawBreastCancer.txt

82 columns; Patient ID present: **True**.

1. `Age recode with <1 year olds`
2. `Race recode (White, Black, Other)`
3. `Sex`
4. `Year of diagnosis`
5. `Site recode ICD-O-3/WHO 2008`
6. `Primary Site`
7. `Histologic Type ICD-O-3`
8. `Grade Recode (thru 2017)`
9. `Laterality`
10. `Site recode ICD-O-3/WHO 2008 (for SIRs)`
11. `Site recode - rare tumors`
12. `RX Summ--Surg Prim Site (1998+)`
13. `RX Summ--Scope Reg LN Sur (2003+)`
14. `RX Summ--Surg Oth Reg/Dis (2003+)`
15. `RX Summ--Surg/Rad Seq`
16. `Reason no cancer-directed surgery`
17. `Radiation recode`
18. `Chemotherapy recode (yes, no/unk)`
19. `Scope of reg lymph nd surg (1998-2002)`
20. `RX Summ--Reg LN Examined (1998-2002)`
21. `Surgery of oth reg/dis sites (1998-2002)`
22. `Site specific surgery (1973-1997 varying detail by year and site)`
23. `Radiation to Brain or CNS Recode (1988-1997)`
24. `RX Summ--Systemic/Sur Seq (2007+)`
25. `Time from diagnosis to treatment in days recode`
26. `Schema Discriminator 2: Oropharyngeal p16 (2018+)`
27. `Breslow Tumor Thickness (2018+)`
28. `Brain Molecular Markers (2018+)`
29. `High Risk Cytogenetics (2018+)`
30. `JAK2 (2018+)`
31. `KIT Gene Immunohistochemistry (2018+)`
32. `KRAS (2018+)`
33. `Methylation of O6-Methylguanine-Methyltransferase (2018+)`
34. `Microsatellite Instability (MSI) (2018+)`
35. `AFP Post-Orchiectomy Lab Value Recode (2010+)`
36. `AFP Pretreatment Interpretation Recode (2010+)`
37. `B Symptoms Recode (2010+)`
38. `Breslow Thickness Recode (2010+)`
39. `CA-125 Pretreatment Interpretation Recode (2010+)`
40. `CEA Pretreatment Interpretation Recode (2010+)`
41. `Chromosome 19q: Loss of Heterozygosity (LOH) Recode (2010+)`
42. `Chromosome 1p: Loss of Heterozygosity (LOH) Recode (2010+)`
43. `Fibrosis Score Recode (2010+)`
44. `Gestational Trophoblastic Prognostic Scoring Index Recode (2010+)`
45. `Gleason Patterns Clinical Recode (2010+)`
46. `Gleason Patterns Pathological Recode (2010+)`
47. `Gleason Score Clinical Recode (2010+)`
48. `Gleason Score Pathological Recode (2010+)`
49. `hCG Post-Orchiectomy Range Recode (2010+)`
50. `Invasion Beyond Capsule Recode (2010+)`
51. `Ipsilateral Adrenal Gland Involvement Recode (2010+)`
52. `LDH Post-Orchiectomy Range Recode (2010+)`
53. `LDH Pretreatment Level Recode (2010+)`
54. `PSA Lab Value Recode (2010+)`
55. `Mets at DX-Distant LN (2016+)`
56. `Mets at DX-Other (2016+)`
57. `Breast Subtype (2010+)`
58. `COD to site recode`
59. `SEER cause-specific death classification`
60. `SEER other cause of death classification`
61. `Survival months`
62. `Survival months flag`
63. `COD to site rec KM`
64. `COD to site recode ICD-O-3 2023 Revision`
65. `COD to site recode ICD-O-3 2023 Revision Expanded (1999+)`
66. `Vital status recode (study cutoff used)`
67. `Sequence number`
68. `First malignant primary indicator`
69. `Primary by international rules`
70. `Record number recode`
71. `Total number of in situ/malignant tumors for patient`
72. `Total number of benign/borderline tumors for patient`
73. `Race recode (W, B, AI, API)`
74. `Origin recode NHIA (Hispanic, Non-Hisp)`
75. `Race and origin recode (NHW, NHB, NHAIAN, NHAPI, Hispanic)`
76. `Race/ethnicity`
77. `IHS Link`
78. `Year of follow-up recode`
79. `Year of death recode`
80. `Patient ID`
81. `Marital status at diagnosis`
82. `Median household income inflation adj to 2022`

## Datasets/RawLiverCancer.txt

56 columns; Patient ID present: **True**.

1. `Age recode with <1 year olds`
2. `Race recode (White, Black, Other)`
3. `Sex`
4. `Year of diagnosis`
5. `Site recode ICD-O-3/WHO 2008`
6. `Behavior code ICD-O-3`
7. `Primary Site`
8. `Histologic Type ICD-O-3`
9. `Behavior recode for analysis`
10. `Grade Recode (thru 2017)`
11. `Derived Summary Grade 2018 (2018+)`
12. `Grade Clinical (2018+)`
13. `Grade Pathological (2018+)`
14. `Laterality`
15. `Site recode - rare tumors`
16. `Combined Summary Stage (2004+)`
17. `Summary stage 2000 (1998-2017)`
18. `SEER Combined Summary Stage 2000 (2004-2017)`
19. `SEER historic stage A (1973-2015)`
20. `RX Summ--Surg Prim Site (1998+)`
21. `RX Summ--Scope Reg LN Sur (2003+)`
22. `RX Summ--Surg Oth Reg/Dis (2003+)`
23. `RX Summ--Surg/Rad Seq`
24. `Reason no cancer-directed surgery`
25. `Radiation recode`
26. `Chemotherapy recode (yes, no/unk)`
27. `Scope of reg lymph nd surg (1998-2002)`
28. `RX Summ--Reg LN Examined (1998-2002)`
29. `Site specific surgery (1973-1997 varying detail by year and site)`
30. `Radiation to Brain or CNS Recode (1988-1997)`
31. `RX Summ--Systemic/Sur Seq (2007+)`
32. `Time from diagnosis to treatment in days recode`
33. `Age recode with <1 year olds and 90+`
34. `Age recode with single ages and 85+`
35. `Age recode with single ages and 90+`
36. `Race recode (W, B, AI, API)`
37. `Origin recode NHIA (Hispanic, Non-Hisp)`
38. `Race and origin recode (NHW, NHB, NHAIAN, NHAPI, Hispanic)`
39. `Race/ethnicity`
40. `Year of follow-up recode`
41. `Year of death recode`
42. `Patient ID`
43. `Type of Reporting Source`
44. `Marital status at diagnosis`
45. `CoC Accredited Flag (2018+)`
46. `Median household income inflation adj to 2022`
47. `Rural-Urban Continuum Code`
48. `COD to site recode`
49. `SEER cause-specific death classification`
50. `SEER other cause of death classification`
51. `Survival months`
52. `Survival months flag`
53. `COD to site rec KM`
54. `COD to site recode ICD-O-3 2023 Revision`
55. `COD to site recode ICD-O-3 2023 Revision Expanded (1999+)`
56. `Vital status recode (study cutoff used)`

## Datasets/RawProstateCancer.txt

67 columns; Patient ID present: **True**.

1. `Age recode with <1 year olds`
2. `Race recode (White, Black, Other)`
3. `Sex`
4. `Year of diagnosis`
5. `Site recode ICD-O-3/WHO 2008`
6. `Behavior code ICD-O-3`
7. `TNM 7/CS v0204+ Schema (thru 2017)`
8. `TNM 7/CS v0204+ Schema recode`
9. `AYA site recode 2020 Revision`
10. `Lymphoid neoplasm recode 2021 Revision`
11. `ICCC site recode 3rd edition/IARC 2017`
12. `Site recode ICD-O-3 2023 Revision`
13. `Site recode ICD-O-3 2023 Revision Expanded`
14. `Primary Site`
15. `Histologic Type ICD-O-3`
16. `Grade Recode (thru 2017)`
17. `Laterality`
18. `Grade Clinical (2018+)`
19. `Grade Pathological (2018+)`
20. `Diagnostic Confirmation`
21. `ICD-O-3 Hist/behav`
22. `ICD-O-3 Hist/behav, malignant`
23. `Histology recode - broad groupings`
24. `ICCC site recode extended 3rd edition/IARC 2017`
25. `Site recode ICD-O-3/WHO 2008 (for SIRs)`
26. `Site recode - rare tumors`
27. `RX Summ--Surg Prim Site (1998+)`
28. `RX Summ--Scope Reg LN Sur (2003+)`
29. `RX Summ--Surg Oth Reg/Dis (2003+)`
30. `RX Summ--Surg/Rad Seq`
31. `Reason no cancer-directed surgery`
32. `Radiation recode`
33. `Chemotherapy recode (yes, no/unk)`
34. `Scope of reg lymph nd surg (1998-2002)`
35. `RX Summ--Reg LN Examined (1998-2002)`
36. `Surgery of oth reg/dis sites (1998-2002)`
37. `Site specific surgery (1973-1997 varying detail by year and site)`
38. `Radiation to Brain or CNS Recode (1988-1997)`
39. `RX Summ--Systemic/Sur Seq (2007+)`
40. `Time from diagnosis to treatment in days recode`
41. `Gleason Patterns Clinical Recode (2010+)`
42. `Gleason Patterns Pathological Recode (2010+)`
43. `Gleason Score Clinical Recode (2010+)`
44. `Gleason Score Pathological Recode (2010+)`
45. `PSA Lab Value Recode (2010+)`
46. `Tumor Size Over Time Recode (1988+)`
47. `COD to site recode`
48. `SEER cause-specific death classification`
49. `SEER other cause of death classification`
50. `Survival months`
51. `Survival months flag`
52. `COD to site rec KM`
53. `COD to site recode ICD-O-3 2023 Revision`
54. `COD to site recode ICD-O-3 2023 Revision Expanded (1999+)`
55. `Vital status recode (study cutoff used)`
56. `Total number of in situ/malignant tumors for patient`
57. `Total number of benign/borderline tumors for patient`
58. `Race recode (W, B, AI, API)`
59. `Origin recode NHIA (Hispanic, Non-Hisp)`
60. `Race and origin recode (NHW, NHB, NHAIAN, NHAPI, Hispanic)`
61. `Race/ethnicity`
62. `Year of follow-up recode`
63. `Year of death recode`
64. `Patient ID`
65. `Marital status at diagnosis`
66. `Median household income inflation adj to 2022`
67. `Rural-Urban Continuum Code`

## Datasets/RawSkinCancer.txt

39 columns; Patient ID present: **True**.

1. `Age recode with <1 year olds`
2. `Race recode (White, Black, Other)`
3. `Sex`
4. `Year of diagnosis`
5. `Site recode ICD-O-3/WHO 2008`
6. `Behavior code ICD-O-3`
7. `Primary Site - labeled`
8. `Primary Site`
9. `Histologic Type ICD-O-3`
10. `Laterality`
11. `RX Summ--Surg Prim Site (1998+)`
12. `RX Summ--Scope Reg LN Sur (2003+)`
13. `RX Summ--Surg Oth Reg/Dis (2003+)`
14. `RX Summ--Surg/Rad Seq`
15. `Reason no cancer-directed surgery`
16. `Radiation recode`
17. `Chemotherapy recode (yes, no/unk)`
18. `Scope of reg lymph nd surg (1998-2002)`
19. `RX Summ--Reg LN Examined (1998-2002)`
20. `Surgery of oth reg/dis sites (1998-2002)`
21. `Site specific surgery (1973-1997 varying detail by year and site)`
22. `Time from diagnosis to treatment in days recode`
23. `Gleason Patterns Clinical Recode (2010+)`
24. `Gleason Patterns Pathological Recode (2010+)`
25. `Gleason Score Clinical Recode (2010+)`
26. `Gleason Score Pathological Recode (2010+)`
27. `PSA Lab Value Recode (2010+)`
28. `Survival months`
29. `Survival months flag`
30. `Vital status recode (study cutoff used)`
31. `Race recode (W, B, AI, API)`
32. `Origin recode NHIA (Hispanic, Non-Hisp)`
33. `Race and origin recode (NHW, NHB, NHAIAN, NHAPI, Hispanic)`
34. `Race/ethnicity`
35. `Year of follow-up recode`
36. `Year of death recode`
37. `Patient ID`
38. `Marital status at diagnosis`
39. `Median household income inflation adj to 2022`
