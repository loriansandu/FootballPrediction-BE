from pickle import dump
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import warnings
from sklearn import svm
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, recall_score, precision_score, f1_score

import pandas as pd
from Predict.consts import MODEL_COLUMNS


def train_and_evaluate_classifiers():
    # Load data from CSV file
    df = pd.read_csv("data/EPL_full_2020-2021_2021-2022_2022-2023.csv")

    # Extract the features to be scaled
    features_to_scale = MODEL_COLUMNS
    features = df[features_to_scale]
    predictors = features_to_scale

    # Scale the features
    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(features)
    dump(scaler, open('models/scaler/scaler.pkl', 'wb'))
    # Replace the original features with the scaled features in the dataframe
    df[features_to_scale] = scaled_features
    df = df[predictors + ['target']]
    df = df.dropna()
    # Save the scaled data to CSV file
    df.to_csv('data/EPL_data_scaled_2020-2021_2021-2022_2022-2023.csv', index=False)

    x = df[predictors]
    y = df['target']

    # Split the data into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(x, y, test_size=0.30)

    # Define the classifiers
    clf_random = RandomForestClassifier()
    clf_logistic = LogisticRegression()
    clf_svm = svm.SVC()
    clf_knn = KNeighborsClassifier()
    warnings.filterwarnings("ignore")

    # Train and evaluate the classifiers
    classifiers = [clf_random, clf_logistic, clf_svm, clf_knn]
    classifier_names = ['Random Forest', 'Logistic Regression', 'SVM', 'K-NN']
    result_df = pd.DataFrame(columns=['Classifier', 'Accuracy', 'Precision', 'Recall', 'F1 Score'])

    for classifier, classifier_name in zip(classifiers, classifier_names):
        accuracy_scores = []
        precision_scores = []
        recall_scores = []
        f1_scores = []

        for _ in range(1000):
            # Split the data into training and testing sets
            X_train, X_test, y_train, y_test = train_test_split(x, y, test_size=0.30)

            # Train the classifier
            classifier.fit(X_train, y_train)

            # Make predictions on the test set
            y_pred = classifier.predict(X_test)

            # Calculate evaluation metrics
            accuracy = accuracy_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred, average='weighted')
            recall = recall_score(y_test, y_pred, average='weighted')
            f1 = f1_score(y_test, y_pred, average='weighted')

            # Append scores to the respective lists
            accuracy_scores.append(accuracy)
            precision_scores.append(precision)
            recall_scores.append(recall)
            f1_scores.append(f1)

        # Print the average and standard deviation of the evaluation metrics
        print(f"{classifier_name} Accuracy: {np.mean(accuracy_scores):.4f} +/- {np.std(accuracy_scores):.4f}")
        print(f"{classifier_name} Precision: {np.mean(precision_scores):.4f} +/- {np.std(precision_scores):.4f}")
        print(f"{classifier_name} Recall: {np.mean(recall_scores):.4f} +/- {np.std(recall_scores):.4f}")
        print(f"{classifier_name} F1 Score: {np.mean(f1_scores):.4f} +/- {np.std(f1_scores):.4f}")
        print()
        result_df = result_df.append({
            'Classifier': classifier_name,
            'Accuracy': np.mean(accuracy_scores),
            'Precision': np.mean(precision_scores),
            'Recall': np.mean(recall_scores),
            'F1 Score': np.mean(f1_scores)
        }, ignore_index=True)

    # Save the evaluation results to a file
    result_df.to_csv('evaluation_results.csv', index=False)

    # Save the trained models
    joblib.dump(clf_random, "models/joblib/RandomForest_model.joblib")
    joblib.dump(clf_logistic, "models/joblib/LogisticRegression_model.joblib")
    joblib.dump(clf_svm, "models/joblib/SVM_model.joblib")
    joblib.dump(clf_knn, "models/joblib/KNN_model.joblib")

    dump(clf_random, open('models/pkl/RandomForest_model.pkl', 'wb'))
    dump(clf_logistic, open('models/pkl/LogisticRegression_model.pkl', 'wb'))
    dump(clf_svm, open('models/pkl/SVM_model.pkl', 'wb'))
    dump(clf_knn, open('models/pkl/KNN_model.pkl', 'wb'))
