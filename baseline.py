## linear regression + 分組 train

import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error

df = pd.read_csv("total_dataset_final.csv")

# 處理 weekday
if 'weekday' in df.columns and df['weekday'].dtype == 'object':
    df['weekday'] = df['weekday'].map({'Y': 1, 'N': 0})

features = ['Hour', 'weekday', 'temperature', 'precipitation', 'rain', 
            'cloudcover', 'windspeed', 'demand', 'Air_quality']
target = 'volumn'

results = []

# train
for street, group in df.groupby('street'):
    X = group[features]
    y = group[target]

    # 資料標準化
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # 訓練、測試集
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

    # 線性回歸
    model = LinearRegression()
    model.fit(X_train, y_train)

    # 預測
    y_pred = model.predict(X_test)

    # 指標
    r2 = r2_score(y_test, y_pred)
    mse = mean_squared_error(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)

    results.append((street, r2, mse, mae))

# 儲存結果
pd.DataFrame(results, columns=["Street", "R2", "MSE", "MAE"]).to_csv("linear_regression_result.csv", index = False)
