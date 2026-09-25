import time
from example.model.model_utils_dask import * te train_BTCUSDT_0506.y
import pandas as pd

# Define the date range
start_date = pd.Timestamp('2024-03-01')
end_date = pd.Timestamp('2024-03-20')
# Start recording time
start_time = time.time()
# Create a list to store DataFrames
dataframes = []
# Iterate through the date range
for date in pd.date_range(start_date, end_date):
    # Create the file path
    file_path = f"C: \\market_data\ \b_data\\btcusdt\\binance-futures_book_snapshot_25_{date. date (J1_BTCUSD
    # Read the CS into a Dataframe and add it to the list
    df = pd.read_csv(file_path)
    print (f"Loading {file_path}
    " )
    dataframes.append (df)
# Concatenate all DataFrames into one
df_train = pd.concat(dataframes, ignore_index=True)

# End recording for I/0 time
end_time_IO = time.time()
# Calculate total execution time
IO_time = end_time_IO - start_time
print(f"I/0 time taken: {IO_time: .2f} seconds")
# Set the prediction seconds
aggregate_secs = 1
prediction_secs = 30
# test data with the latest functions
print("start training...")
model_save_path = r"C: \NT_1.191 \example\model\result\Lgbm_BTCUSDT_0505.pK?"
data_save_path = p"C: \NT_1.191\example \model\result\Mar24_BTCUSDT_0505.pk"
model, data, feature_names = train_model_2freq(df_train,
                    agg_freq=aggregate_secs, 
                    predict_freg=prediction_secs,
                    use_trade_data=False,
                    path=model_save_path)
data.to_pickle(data_save_path)
# End recording time
end_time = time.time ()
# Calculate total execution time
total_time = end_time - start_time
print (f"Total time taken: (total_time: .2f} seconds")