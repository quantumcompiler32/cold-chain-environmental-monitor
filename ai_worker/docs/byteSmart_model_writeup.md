# byteSmart Model Write-Up and Workflow Explanation

## Overview

For this project, I took the original Colab notebook and split it into a cleaner machine learning workflow. At first, everything was in one place, which worked, but it also made the notebook feel crowded. The goal was to organize it so each part had a clear purpose: one notebook for the full process, one notebook only for training, and one notebook only for testing and inference.

The main idea is simple. The data comes in, gets cleaned, gets turned into features, and then the models learn from it. After that, the models are saved as pickle files so they can be loaded later without training again. That is important because training is like the model's learning stage, while inference is the stage where the model uses what it already learned.

## Files Created

### 1. Combined Notebook

File: `byteSmart_combined_training_testing_inference.ipynb`

This is the full notebook. It runs everything from beginning to end:

- loads the zip data
- cleans the CSV files
- creates features for the models
- splits the data into training and testing data
- trains Linear Regression, Logistic Regression, and K-Means
- tests the models using test data
- creates visuals for all three algorithms
- saves the trained models as `.pkl` files
- loads the saved models again and runs inference

This notebook is useful because it shows the whole process in one place. If someone wants to understand how the project works from start to finish, this is the notebook they should look at first.

### 2. Training Notebook

File: `byteSmart_training.ipynb`

This notebook only focuses on training. It takes the training parts from the combined notebook and separates them into a stand-alone file. It trains the three models and saves them as:

- `linear_regression_model.pkl`
- `logistic_regression_model.pkl`
- `kmeans_model.pkl`

This is useful because once the models are trained, we do not need to retrain them every time. The pickle files hold the trained models, almost like saving progress in a game. The work is already done, and later notebooks can just load the models.

### 3. Testing and Inference Notebook

File: `byteSmart_testing_inference.ipynb`

This notebook loads the saved pickle files and runs predictions on the test data. It does not train the models again. That is the whole point of this notebook: to prove that the saved models can be reused later.

This matters because in real projects, training can take time. If the model already learned the pattern, it should be able to load from a file and make predictions directly.

### 4. Write-Up and Diagrams

The write-up explains how the models performed, what worked, what issues showed up, and how the results could be improved. The visual diagram file explains how the notebooks, models, pickle files, and inference process all connect.

## Libraries Used

I kept the libraries limited so the project does not look overloaded or confusing. The main libraries are:

- `numpy`
- `pandas`
- `matplotlib`
- `pickle`
- `zipfile`
- `pathlib`
- scikit-learn tools for the three algorithms and small helpers

The scikit-learn pieces used are:

- `LinearRegression`
- `LogisticRegression`
- `KMeans`
- `train_test_split`
- basic metrics
- `StandardScaler` for K-Means
- `PCA` only for making the K-Means visual easier to understand

I did not add extra libraries just to make it look more advanced. The goal was to keep the project understandable.

## Model 1: Linear Regression

Linear Regression was used to predict dry ice mass based on time and condition. The inputs were elapsed hours and whether the dry ice was baseline or refrigerated. The output was the predicted dry ice mass in pounds.

Performance:

- Mean Absolute Error: `2.809 lb`
- Root Mean Squared Error: `4.184 lb`
- R2 Score: `0.912`

This model worked pretty well because the dry ice mass dropped in a mostly steady pattern. A straight line was able to capture a lot of that behavior. The R2 score of 0.912 means the model explained most of the pattern in the test data.

The issue is that real dry ice loss is not always perfectly straight. Airflow, container openings, outside temperature, and sensor noise can all change the pattern. So even though the model did well, it is still a simplified version of what is happening.

To improve it, I could add more features, like room temperature or container conditions. I could also try a curved model if the dry ice loss bends over time instead of staying linear.

## Model 2: Logistic Regression

Logistic Regression was used to classify whether a time window looked like `Test 1` or `Test 2`. The model used features like average temperature, sensor spread, O2, CO2, and temperature slope.

Performance:

- Accuracy: `0.996`

This model performed extremely well. That tells me Test 1 and Test 2 had patterns that were different enough for the model to separate them. It was not just guessing. The temperature and gas behavior gave the model strong clues.

At the same time, accuracy can be a little misleading. There were more Test 1 windows than Test 2 windows, so the data was not perfectly balanced. That means I cannot only look at accuracy and say everything is perfect. The confusion matrix and classification report matter because they show where the model might still be missing things.

To improve this model, I would want more balanced data from both tests. I could also try different window sizes because using only 60-row windows might hide some smaller patterns.

## Model 3: K-Means

K-Means was used to group sensors based on how they behaved. It looked at each sensor's average temperature, standard deviation, minimum, maximum, and warming or cooling slope.

Performance:

- Silhouette Score: `0.784`

K-Means is different from the other two models because it does not use labels. It is unsupervised, which means it is not told the correct answer ahead of time. Instead, it tries to find groups by looking at which sensors are similar.

The silhouette score was strong, which means the clusters were fairly well separated. This is useful because there are many sensors, and looking at every single one by itself can feel like staring at scattered puzzle pieces. K-Means helps turn that mess into a few groups that are easier to understand.

The main issue is that K-Means depends on the number of clusters we choose. I used 4 clusters, but another number might make more sense. The clusters also need interpretation. The model can group sensors, but a person still has to decide what those groups mean.

To improve it, I could test different cluster counts, compare silhouette scores, and use sensor location information if that data is available.

## Pickle File Confirmation

The models were saved and then loaded again successfully.

- Linear Regression loaded without retraining: `True`
- Logistic Regression loaded without retraining: `True`
- K-Means loaded without retraining: `True`

This confirms that the training notebook creates reusable model files, and the testing notebook can use those files later. That is the main purpose of separating training from inference.

## Issues and Limitations

The biggest limitation is that the data comes from a specific set of tests. The models may work well here, but that does not automatically mean they will work perfectly on a new experiment. Models can sometimes learn the patterns of one dataset too closely, almost like memorizing a study guide instead of understanding the whole subject.

Another issue is class balance for Logistic Regression. Since there were more Test 1 windows than Test 2 windows, the accuracy score needs to be interpreted carefully.

For K-Means, the issue is interpretation. It can find clusters, but it does not explain the real-world reason behind them by itself.

## How I Would Improve the Project

If I had more time, I would improve the project by:

- collecting more data from more tests
- balancing the Test 1 and Test 2 examples
- trying different time-window sizes
- testing different numbers of K-Means clusters
- adding sensor location information
- comparing the models on new data that was not part of this project

These improvements would make the results stronger and more reliable.

## Conceptual Notes for Monday

Linear Regression predicts a number. In this project, it predicts dry ice mass. It works by finding the best straight-line relationship between the inputs and the output.

Logistic Regression predicts a category. In this project, it predicts whether a time window is Test 1 or Test 2. Even though it has "regression" in the name, it is used for classification.

K-Means finds groups. It does not need labels. It looks for data points that are close to each other and puts them into clusters.

The main thing I need to explain is the difference between training, testing, and inference. Training is when the model learns. Testing is when we check if it learned something useful. Inference is when we use the saved model later to make predictions.

## Final Takeaway

Overall, the models performed well. Linear Regression captured the dry ice loss trend, Logistic Regression separated Test 1 and Test 2 very accurately, and K-Means helped organize the sensor behavior into understandable groups.

The project is useful because it shows a complete machine learning pipeline. It does not just train a model and stop. It trains, tests, saves, reloads, and runs inference. That full process is what makes the notebooks work together instead of feeling like separate pieces floating around.
