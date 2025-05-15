from datetime import datetime
import pandas as pd

def is_weekday(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d").weekday() < 5  # weekday < 5 means Mon–Fri

# 讀取基本交通資料
auto_df = pd.read_csv("/home/weichen/AI/project/dataset/Automated_Traffic_Volume_Counts.csv")

# 建立 total dataset
total = pd.DataFrame(columns=[
    "ID", "Boro", "Date", "Hour", "weekday", "volumn",
    "segmentID", "street", "fromst", "tost", "Direction"
])

# --- 處理 Automated Traffic ---
auto_df = auto_df[auto_df["MM"] == 0]  # 只保留 MM=0 的資料
id_counter = 1
records = []  # 用 list 暫存每一筆資料

for _, row in auto_df.iterrows():
    date = f"{row['Yr']}-{row['M']:02}-{row['D']:02}"
    if row['Yr'] < 2016 or row['Yr'] > 2022:
        continue
    if row['Yr'] == 2022 and (row['M'] == 11 or row['M'] == 12):
        continue
    if row['Yr'] == 2022 and row['M'] == 10 and row['D'] >= 20:
        continue
    weekday = "Y" if is_weekday(date) else "N"
    
    records.append({
        "ID": id_counter,
        "Boro": row["Boro"],
        "Date": date,
        "Hour": row["HH"],
        "weekday": weekday,
        "volumn": row["Vol"],
        "segmentID": row["SegmentID"],
        "street": row["street"],
        "fromst": row["fromSt"],
        "tost": row["toSt"],
        "Direction": row["Direction"]
    })
    id_counter += 1

# 最後一次性建立 DataFrame
total = pd.DataFrame(records)

# 將 Date 轉為 datetime
total["Date"] = pd.to_datetime(total["Date"])
# --- 處理 nyc_traffic.csv 資料並加入 total ---
nyc_traffic = pd.read_csv("/home/weichen/AI/project/dataset/Traffic_Volume_Counts.csv")

# 時間欄位對應表（對應 Hour 數值）
hour_columns = [
    "12:00-1:00 AM", "1:00-2:00AM", "2:00-3:00AM", "3:00-4:00AM", "4:00-5:00AM",
    "5:00-6:00AM", "6:00-7:00AM", "7:00-8:00AM", "8:00-9:00AM", "9:00-10:00AM",
    "10:00-11:00AM", "11:00-12:00PM", "12:00-1:00PM", "1:00-2:00PM", "2:00-3:00PM",
    "3:00-4:00PM", "4:00-5:00PM", "5:00-6:00PM", "6:00-7:00PM", "7:00-8:00PM",
    "8:00-9:00PM", "9:00-10:00PM", "10:00-11:00PM", "11:00-12:00AM"
]

# 清理欄位名稱：統一街道大寫方便比對
nyc_traffic["Roadway Name"] = nyc_traffic["Roadway Name"].astype(str).str.upper()

# 建立 street-to-Boro 對應表（從 total 中建立）
street_to_boro = total[["street", "Boro"]].drop_duplicates().set_index("street")["Boro"].to_dict()

# 用來儲存轉換後的資料列
traffic_records = []
for _, row in nyc_traffic.iterrows():
    street = str(row["Roadway Name"]).upper()
    boro = street_to_boro.get(street, "UNKNOWN")  # 如果找不到 Boro，設成 UNKNOWN
    if boro == "UNKNOWN":
        continue
    try:
        date_obj = pd.to_datetime(row["Date"], errors="coerce")
        if pd.isna(date_obj):
            continue
        year = date_obj.year
        month = date_obj.month
        day = date_obj.day
        if year < 2016 or year > 2022:
            continue
        if year == 2022 and (month == 11 or month == 12):
            continue
        if year == 2022 and month == 10 and day >= 20:
            continue
        
    except:
        continue

    for hour, col_name in enumerate(hour_columns):
        volumn = row.get(col_name, None)
        if pd.isna(volumn):
            continue
        weekday = "Y" if is_weekday(str(date_obj.date())) else "N"
        traffic_records.append({
            "ID": id_counter,
            "Boro": boro,
            "Date": date_obj.date(),
            "Hour": hour,
            "weekday": weekday,
            "volumn": volumn,
            "segmentID": row["SegmentID"],
            "street": street,
            "fromst": row["From"],
            "tost": row["To"],
            "Direction": row["Direction"]
        })
        id_counter += 1

# 將新資料加到 total
traffic_df = pd.DataFrame(traffic_records)
total = pd.concat([total, traffic_df], ignore_index=True)
# 排序
# 確保 Date 欄位全部轉為 pd.Timestamp 格式，避免混用 datetime.date
total["Date"] = pd.to_datetime(total["Date"])
total = total.sort_values(by=["street", "Date", "Hour"], ascending=[True, True, True]).reset_index(drop=True)

# --- 加入天氣資料 ---
weather_df = pd.read_csv("/home/weichen/AI/project/dataset/NYC_Weather_2016_2022.csv")

# 將 weather 中的時間轉為 datetime 格式，保留到小時
weather_df["time"] = pd.to_datetime(weather_df["time"]).dt.floor("h")

# 欄位重新命名
weather_df = weather_df.rename(columns={
    "temperature_2m (°C)": "temperature",
    "precipitation (mm)": "precipitation",
    "rain (mm)": "rain",
    "cloudcover (%)": "cloudcover",
    "windspeed_10m (km/h)": "windspeed"
})
weather_df = weather_df[["time", "temperature", "precipitation", "rain", "cloudcover", "windspeed"]]

# 建立 total 的完整 datetime 欄位
total["DateTime"] = total.apply(lambda row: pd.Timestamp(row["Date"]) + pd.to_timedelta(int(row["Hour"]), unit='h'), axis=1)

# 合併資料（以完整時間為主）
total = total.merge(weather_df, how="left", left_on="DateTime", right_on="time").drop(columns=["time"])

# --- 加入 Pedestrian demand ---
demand_df = pd.read_csv("/home/weichen/AI/project/dataset/Pedestrian_Mobility_Plan_Pedestrian_Demand.csv")

# 將 demand_df 中的街道與行政區轉大寫以利比對
demand_df["street"] = demand_df["street"].astype(str).str.upper()
demand_df["BoroName"] = demand_df["BoroName"].astype(str).str.upper()

# 建立一個 demand 平均表：groupby street & BoroName，計算平均 Rank
avg_demand = demand_df.groupby(["street", "BoroName"])["Rank"].mean().reset_index()
avg_demand = avg_demand.rename(columns={"Rank": "avg_demand"})

# 將 total 中的 street 與 Boro 轉大寫以利 merge
total["street"] = total["street"].astype(str).str.upper()
total["Boro"] = total["Boro"].astype(str).str.upper()

# 合併 avg_demand 到 total（根據街道與行政區）
total = total.merge(avg_demand, how="left", left_on=["street", "Boro"], right_on=["street", "BoroName"])
total = total.drop(columns=["BoroName"])

# 若找不到對應的 demand，填入預設值 5；否則取整數平均值
total["demand"] = total["avg_demand"].round().fillna(5).astype(int)
total = total.drop(columns=["avg_demand"])

# --- 加入空氣品質（使用 date 與 pm25 欄位）---
air_df = pd.read_csv("/home/weichen/AI/project/dataset/new-york-air-quality.csv", header=None)

# 指定欄位名稱
air_df.columns = ["date", "pm25", "col3", "col4", "col5"]

# 將 date 轉為 datetime
air_df["date"] = pd.to_datetime(air_df["date"], format="%Y/%m/%d", errors="coerce").dt.floor("D")

# 只保留需要的兩欄
air_df = air_df[["date", "pm25"]].drop_duplicates()
air_df = air_df.rename(columns={"pm25": "Air_quality"})

# 合併 total 和 air_df
total = total.merge(air_df, how="left", left_on="Date", right_on="date").drop(columns=["date"])

# 移除 Air_quality 欄位中的前後空白（若為字串格式）
total["Air_quality"] = total["Air_quality"].astype(str).str.strip()

# 如果需要將其轉回數值型態
total["Air_quality"] = pd.to_numeric(total["Air_quality"], errors="coerce")

# total["Air_quality"] = total["Air_quality"].fillna(value)

"""
# --- 加入速限 ---
speed_df = pd.read_csv("/home/weichen/AI/project/dataset/speed_limit.csv")

# 將街道名稱轉為大寫統一格式
speed_df["street"] = speed_df["street"].astype(str).str.upper()
total["street"] = total["street"].astype(str).str.upper()

# 只保留必要欄位
speed_df = speed_df[["street", "postvz_sl"]].drop_duplicates()

# 合併 total 與 speed_df（依 street）
total = total.merge(speed_df, how="left", on="street")

# 填補缺失的限速為預設值 25
total["postvz_sl"] = total["postvz_sl"].fillna(25).astype(int)

# 重新命名欄位為 limit（如需一致命名）
total = total.rename(columns={"postvz_sl": "limit"})
"""

# 將 DateTime 拆成 Date 和 Hour 欄位
total["Date"] = total["DateTime"].dt.date.astype(str)   # 拆出日期字串格式
total["Hour"] = total["DateTime"].dt.hour               # 拆出小時

# 將欄位順序整理，移除原本 DateTime 欄位
total = total.drop(columns=["DateTime"])

# 將欄位順序調整
cols = ["ID", "Boro", "Date", "Hour", "weekday", "volumn",
        "segmentID", "street", "fromst", "tost", "Direction",
        "temperature", "precipitation", "rain", "cloudcover", "windspeed",
        "demand", "Air_quality"] # there have a comment
total = total[cols]

counts = total["street"].value_counts()
values_over_720 = counts[counts >= 720].index

filtered_df = total[total["street"].isin(values_over_720)]

# 移除特定日期的資料
filtered_df = filtered_df[~filtered_df["Date"].isin(["2017-01-28", "2017-09-06", "2017-09-07", "2017-09-08", "2022-03-03"])]

# --- 儲存成 CSV ---
filtered_df.to_csv("total_dataset_final.csv", index=False)
print("total_dataset_final.csv saved.")
