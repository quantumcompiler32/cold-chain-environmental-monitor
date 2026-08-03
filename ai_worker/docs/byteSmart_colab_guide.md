# byteSmart Colab Notebook Guide

This folder contains the final three-notebook workflow for Monday.

## Files to Use

1. `byteSmart_combined_training_testing_inference.ipynb`
   - Runs the full workflow in one Colab notebook.
   - Splits the data into train and test sets.
   - Trains Linear Regression, Logistic Regression, and K-Means.
   - Tests the models and shows visuals for all three.
   - Saves and reloads the pickle files.

2. `byteSmart_training.ipynb`
   - Training-only notebook.
   - Trains the three models.
   - Saves `linear_regression_model.pkl`, `logistic_regression_model.pkl`, and `kmeans_model.pkl`.

3. `byteSmart_testing_inference.ipynb`
   - Testing and inference notebook.
   - Loads the three saved pickle files.
   - Runs predictions on the test data without retraining.

4. `byteSmart_model_writeup.md`
   - Simple write-up explaining performance, issues, improvements, and conceptual notes for Monday.

## Libraries Used

The notebooks keep the libraries limited: NumPy, Pandas, Matplotlib, pickle/file helpers, and scikit-learn only for the three algorithms plus the small helpers needed for train/test split, metrics, scaling, and PCA visualization.

## Recommended Use

For the full assignment, start with the combined notebook. Then use the training notebook to create the pickle files. Finally, use the testing notebook to prove the saved pickle files can be loaded and used without retraining.
