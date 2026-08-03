# byteSmart Short Workflow Explanation

This project is split into three Colab notebooks plus one write-up. Together, they show the full machine learning workflow: train models, save them, reload them, and use them later without retraining.

## 1. Combined Notebook

File: `byteSmart_combined_training_testing_inference.ipynb`

This is the full end-to-end notebook. It loads the data, cleans it, creates the model inputs, splits the data into training and testing sets, trains all three algorithms, tests them, and shows visuals.

The three algorithms are:

- Linear Regression: predicts dry ice mass from time and condition.
- Logistic Regression: predicts whether a sensor time window looks like Test 1 or Test 2.
- K-Means: groups sensors into clusters based on similar behavior.

This notebook also saves the trained models as pickle files and reloads them to prove they can be used again.

## 2. Training Notebook

File: `byteSmart_training.ipynb`

This notebook only does the training part. It uses the same preparation steps from the combined notebook, trains the three models, and saves them as:

- `linear_regression_model.pkl`
- `logistic_regression_model.pkl`
- `kmeans_model.pkl`

These pickle files store the trained models so they can be used later without running training again.

## 3. Testing and Inference Notebook

File: `byteSmart_testing_inference.ipynb`

This notebook loads the saved pickle files and runs predictions on the test data. It does not retrain the models.

This proves that the saved models work correctly after being loaded back from files.

## 4. Write-Up

File: `byteSmart_model_writeup.md`

The write-up explains how the models performed, what the results mean, what issues came up, and how the work could be improved.

Main results:

- Linear Regression worked well for dry ice mass prediction because the mass changed in a mostly steady pattern.
- Logistic Regression was very accurate because Test 1 and Test 2 had clear differences in temperature and gas behavior.
- K-Means was useful for grouping sensors, but its clusters need interpretation because it does not use correct answer labels.

## How Everything Works Together

The combined notebook shows the full process in one place. The training notebook separates out only the model-building step and creates reusable `.pkl` files. The testing notebook then loads those `.pkl` files and uses them for inference. The write-up explains the results in simple language.

So the workflow is:

1. Prepare the data.
2. Train the three models.
3. Save the models as pickle files.
4. Load the saved models later.
5. Run predictions on test data.
6. Explain the model performance and improvements.

## Monday Discussion Notes

Linear Regression predicts a number by fitting the best straight-line relationship between inputs and output.

Logistic Regression predicts a category. In this project, it predicts Test 1 vs Test 2.

K-Means is unsupervised. It finds groups in the data without being told the correct labels.

The key idea to explain is that training teaches the model, testing checks performance, and inference uses the saved model to make predictions later.
