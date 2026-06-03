from datetime import datetime, timedelta

def generate_date_range(start_date_str, end_date_str):
    start_date = datetime.strptime(start_date_str, "%Y%m%d")
    end_date = datetime.strptime(end_date_str, "%Y%m%d")
    date_range = []
    current_date = start_date
    while current_date <= end_date:
        date_range.append(current_date.strftime("%Y%m%d"))
        current_date += timedelta(days=1)
    return date_range
dates = generate_date_range("20250101", "20250405")
print(dates)
