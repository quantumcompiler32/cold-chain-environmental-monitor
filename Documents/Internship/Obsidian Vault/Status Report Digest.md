---
type: source
project: ByteSmart
branch: Connected Sources
status: Active
source:
  - "Gmail: sent Daily Report messages to bitwiseacademy.com"
created: 2026-07-21
updated: 2026-07-21
confidence: medium
review: false
cssclasses:
  - bytesmart-branch
  - branch-connected-sources
---

# Status Report Digest

Detailed chronological digest of the Gmail status reports reviewed for ByteSmart and Bitwise.

The reports are useful first-person evidence, but they are not a complete work log. Use them with project files, code, Drive records, and the source registry when checking what happened.

## 2026-06-24 — Direction

Brainstormed new use cases and moved away from ideas that were too narrowly targeted toward UAVs. Began refining the project report and its practical direction.

## 2026-06-25 — Feedback

Reviewed feedback on the report, annotated important sections, corrected the content, and reported a stronger understanding of the required concepts. Venkat asked for the latest document link, which was then sent.

## 2026-06-29 — Data foundations

Completed file read/write/update practice, Google Drive and Colab file handling, NumPy arrays, Pandas DataFrames, cleaning, filtering, sorting, statistics, and aggregates. Organized the work in a commented Colab notebook and began a reusable cookbook.

## 2026-06-30 — Visualization

Used the original report’s questions to create separate Colab visualization cells, including humidity-over-time and rolling-average views. Created a rough slideshow connecting the project to real-world impact.

## 2026-07-02 — Dataset reset

Changed the notebook to use the three CSV files in `14888121` rather than the older `input.csv`. Reframed the analysis around dry-ice depletion, Test 1 and Test 2 temperature behavior, O2/CO2 trends, and cross-test stability, using the units actually present in the data.

## 2026-07-06 — Hardware and computing

Studied binary arithmetic, number bases, bits, bytes, Boolean algebra, transistors, and logic. Set up the Arduino Uno R4 Minima in the Arduino IDE, configured board and USB ports, and ran Blink and repository examples. Planned sensor threshold and Serial Monitor work.

## 2026-07-07 — EDA story

Updated the slideshow with EDA based on the research questions and built visualizations that answer each question with a graph and interpretation.

## 2026-07-08 — ML notebook focus

Focused the vaccine-dataset Colab notebook on linear regression, K-Means, and logistic regression, while connecting the models to the cold-chain dataset and the project’s research questions.

## 2026-07-09 — Reproducible ML workflow

Organized the work into combined, training, and testing/inference notebooks. Saved three pickle models, loaded them for inference, reviewed performance, documented flaws and improvements, and prepared a writeup explaining the workflow.

## 2026-07-13 — Model understanding

Studied linear regression, logistic regression, K-Means, probability versus odds, planes, cost functions, and gradient descent. Added raw-data graphs, observed-versus-predicted plots, feature-impact graphs, class-balance graphs, confusion matrices, probability graphs, and a review table. Noted that labels must be created without answer leakage.

## 2026-07-14 — Scale and presentation correction

Improved the Google Slides presentation and corrected the dataset understanding: approximately 112,000 readings across 57 temperature channels, using almost all available data. K-Means centroid/assignment visualization remained unresolved. Planned facility outreach and further report updates.

## 2026-07-15 — Safety and outreach

Updated the vaccine-storage monitoring paper with Arduino hardware, sensor wiring, specifications, CSV logging, data collection, dataset cleaning, precise analytical definitions, ML caveats, visualizations, safety procedures, references, and table of contents. Started the facility request one-pager and identified four promising facilities with an outreach plan. Continued K-Means debugging and considered the elbow method.

## 2026-07-20 — Pipeline integration

Verified the MQTT/PostgreSQL pipeline end to end using CSV-backed JSON events. The subscriber displayed events and the listener persisted them. Venkat requested the custom generator prompt, code, and JSON schema; Moksh sent the generator code, sample event, and project prompt. The next work is data dictionary/range/outlier documentation and PostgreSQL analytics.

## Related notes

- [[Internship Index]]
- [[Bitwise Internship Timeline]]
- [[ByteSmart Project]]
- [[Current Internship Work Queue]]
- [[Internship Context And Glossary]]
