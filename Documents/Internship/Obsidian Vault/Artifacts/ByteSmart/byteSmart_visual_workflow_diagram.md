# byteSmart Visual Workflow Diagram

This diagram explains how the three notebooks, three models, pickle files, testing, inference, and write-up all work together.

## 1. Full Project Workflow

```mermaid
flowchart TD
    A[Raw Zip Data<br/>14888121 CSV files] --> B[Data Loading<br/>Find zip, extract files, read CSVs]
    B --> C[Data Cleaning<br/>Convert time, numbers, O2, CO2,<br/>temperature sensor readings]
    C --> D[Feature Creation<br/>Build input tables for each model]

    D --> E1[Linear Regression Dataset<br/>Input: hours + condition<br/>Target: dry ice mass]
    D --> E2[Logistic Regression Dataset<br/>Input: sensor window summaries<br/>Target: Test 1 or Test 2]
    D --> E3[K-Means Dataset<br/>Input: sensor behavior summaries<br/>Target: no label, find groups]

    E1 --> F1[Train/Test Split<br/>Train linear model on training data<br/>Test on held-out data]
    E2 --> F2[Train/Test Split<br/>Train logistic model on training data<br/>Test on held-out data]
    E3 --> F3[Train/Test Split<br/>Fit K-Means on training sensor data<br/>Predict clusters for test sensors]

    F1 --> G1[Linear Regression Model<br/>Predicts a number: dry ice mass]
    F2 --> G2[Logistic Regression Model<br/>Predicts a class: Test 1 vs Test 2]
    F3 --> G3[K-Means Model<br/>Finds groups of similar sensors]

    G1 --> H1[Visuals + Metrics<br/>Actual vs predicted mass<br/>MAE, RMSE, R2]
    G2 --> H2[Visuals + Metrics<br/>Confusion matrix<br/>Accuracy, classification report]
    G3 --> H3[Visuals + Metrics<br/>Cluster plot<br/>Silhouette score]

    G1 --> I1[linear_regression_model.pkl]
    G2 --> I2[logistic_regression_model.pkl]
    G3 --> I3[kmeans_model.pkl]

    I1 --> J[Testing and Inference Notebook<br/>Load saved models]
    I2 --> J
    I3 --> J

    J --> K[Run Predictions on Test Data<br/>No retraining needed]
    K --> L[Write-Up<br/>Performance, issues,<br/>improvements, concepts]
```

## 2. What Each Notebook Does

```mermaid
flowchart LR
    A[Combined Notebook] --> A1[Loads + cleans data]
    A --> A2[Splits train/test data]
    A --> A3[Trains all 3 models]
    A --> A4[Tests all 3 models]
    A --> A5[Shows visuals]
    A --> A6[Saves + reloads pkl files]

    B[Training Notebook] --> B1[Loads + cleans data]
    B --> B2[Creates model features]
    B --> B3[Trains Linear Regression]
    B --> B4[Trains Logistic Regression]
    B --> B5[Trains K-Means]
    B --> B6[Saves 3 pkl files]

    C[Testing/Inference Notebook] --> C1[Loads saved pkl files]
    C --> C2[Recreates test data]
    C --> C3[Runs predictions]
    C --> C4[Shows performance]
    C --> C5[Confirms no retraining]
```

## 3. Linear Regression Diagram

```mermaid
flowchart TD
    A[Dry Ice Data] --> B[Inputs]
    B --> B1[Elapsed hours]
    B --> B2[Condition<br/>baseline or refrigerated]
    B1 --> C[Linear Regression]
    B2 --> C
    C --> D[Prediction]
    D --> E[Predicted dry ice mass in pounds]
    E --> F[Compare to actual mass]
    F --> G[Metrics: MAE, RMSE, R2]
    G --> H[Useful because it explains<br/>how dry ice mass changes over time]
```

Purpose: Linear Regression predicts a number. Here, it predicts dry ice mass. It is useful because dry ice loss is close to a steady trend, so a line can describe the pattern pretty well.

## 4. Logistic Regression Diagram

```mermaid
flowchart TD
    A[Test 1 and Test 2 Sensor Data] --> B[Create Time Windows]
    B --> C[Calculate Window Features]
    C --> C1[Mean temperature]
    C --> C2[Sensor spread]
    C --> C3[Average O2]
    C --> C4[Average CO2]
    C --> C5[Temperature slope]
    C1 --> D[Logistic Regression]
    C2 --> D
    C3 --> D
    C4 --> D
    C5 --> D
    D --> E[Prediction]
    E --> F[Test 1 or Test 2]
    F --> G[Confusion Matrix + Accuracy]
    G --> H[Useful because it shows whether<br/>the model can tell the two tests apart]
```

Purpose: Logistic Regression predicts a category. Here, it predicts whether a sensor time window looks like Test 1 or Test 2. It is useful because it checks whether the test conditions have clearly different patterns.

## 5. K-Means Diagram

```mermaid
flowchart TD
    A[Temperature Sensors] --> B[Create Sensor Summary Features]
    B --> B1[Mean temperature]
    B --> B2[Standard deviation]
    B --> B3[Minimum temperature]
    B --> B4[Maximum temperature]
    B --> B5[Warming or cooling slope]
    B1 --> C[Scale Features]
    B2 --> C
    B3 --> C
    B4 --> C
    B5 --> C
    C --> D[K-Means Clustering]
    D --> E[Cluster 0]
    D --> F[Cluster 1]
    D --> G[Cluster 2]
    D --> H[Cluster 3]
    E --> I[Interpret sensor behavior groups]
    F --> I
    G --> I
    H --> I
    I --> J[Useful because it summarizes<br/>many sensors into a few groups]
```

Purpose: K-Means finds groups without being given correct labels. It is useful because there are many sensors, and clustering makes it easier to see which sensors behave similarly.

## 6. Pickle File Workflow

```mermaid
flowchart LR
    A[Train Model] --> B[Save Model as .pkl]
    B --> C[Close notebook or use later]
    C --> D[Load .pkl file]
    D --> E[Run predictions]
    E --> F[Inference without retraining]
```

Purpose: Pickle files store trained models. This is useful because once the model is trained, you do not need to train it again every time. You can load the saved model and use it directly.

## 7. How the Whole System Runs Together

```mermaid
sequenceDiagram
    participant Data as Raw Data
    participant Combined as Combined Notebook
    participant Train as Training Notebook
    participant PKL as Pickle Files
    participant Test as Testing Notebook
    participant Writeup as Write-Up

    Data->>Combined: Load, clean, split, train, test, visualize
    Combined->>Writeup: Gives results and visuals to explain
    Data->>Train: Load and prepare same features
    Train->>PKL: Save three trained models
    PKL->>Test: Load saved models
    Data->>Test: Recreate test inputs
    Test->>Test: Run inference without retraining
    Test->>Writeup: Add performance, issues, improvements
```

## 8. Simple Big Picture

The data is cleaned once in the same style across all notebooks. The combined notebook proves the full idea works. The training notebook creates reusable model files. The testing notebook proves those saved models can be loaded and used later. The write-up explains what happened, how accurate the models were, what problems exist, and how the results could be improved.

For Monday, the main concept is this:

- Training teaches the model.
- Testing checks if the model learned useful patterns.
- Inference uses the trained model to make predictions later.
- Pickle files let you save trained models so they can be reused.
