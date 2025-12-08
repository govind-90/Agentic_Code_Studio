import pandas as pd
import numpy as np
import os
from ml_workflow_package import DataLoader, FeatureEngineering, ModelTrainer, ModelEvaluator, train_test_split_data

# 1. Setup Dummy Data (Replace this with your actual file path)
# Create a dummy CSV file for demonstration
data = {
    'Age': np.random.randint(20, 60, 200),
    'Salary': np.random.randint(30000, 120000, 200),
    'City': np.random.choice(['NY', 'LA', 'CHI', 'BOS'], 200),
    'Experience': np.random.rand(200) * 10,
    'Target': np.random.randint(0, 2, 200)
}
df_dummy = pd.DataFrame(data)
df_dummy.loc[10:20, 'Age'] = np.nan # Introduce NaNs
dummy_file = 'dummy_data.csv'
df_dummy.to_csv(dummy_file, index=False)

# --- Workflow Start ---

# 2. Data Loading and Preprocessing
loader = DataLoader(dummy_file)
df = loader.load_data()
# Use 'mode' to handle both numerical (Age) and categorical (City) NaNs
df_processed = loader.preprocess(strategy='mode')

# 3. Train/Test Split
X_train, X_test, y_train, y_test = train_test_split_data(
    df_processed, 
    target_column='Target', 
    test_size=0.25
)

# 4. Feature Engineering (Scaling and Encoding)
fe = FeatureEngineering(X_train)

# Build and fit the preprocessor on training data
preprocessor = fe.build_preprocessor(scaling_method='standard', encoding_method='onehot', exclude_cols=[])
X_train_transformed = fe.apply_preprocessing(X_train)

# Transform test data using the fitted preprocessor
# Note: We use the fitted preprocessor object from fe.preprocessor
X_test_transformed = fe.preprocessor.transform(X_test)

# Optional: Feature Selection (Select top 5 features)
X_train_selected, selected_features = fe.select_features(X_train_transformed, y_train, k=5)
X_test_selected = X_test_transformed[selected_features]

print(f"\nSelected Features: {selected_features}")
print(f"Training data shape after selection: {X_train_selected.shape}")

# 5. Model Training
trainer = ModelTrainer()
trained_models = trainer.train_models(X_train_selected, y_train)

# 6. Model Evaluation
evaluator = ModelEvaluator()

print("\n--- Evaluation Results ---")
for name, model in trained_models.items():
    # Calculate test set metrics
    test_metrics = evaluator.calculate_metrics(model, X_test_selected, y_test)
    print(f"\nModel: {name}")
    print(f"Test Metrics: {test_metrics}")
    
    # Perform Cross-Validation on the training set
    cv_results = evaluator.cross_validate(model, X_train_selected, y_train, cv=5, scoring='accuracy')
    print(f"CV Mean Accuracy (5 folds): {cv_results['cv_mean_accuracy']:.4f}")

# Clean up dummy file
os.remove(dummy_file)