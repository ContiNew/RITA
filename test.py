import ChartFormat.bms as bms

test = bms.BMS("E:/Backup From Lenovo/BMS Dataset/Filtered Dataset/160 [ANOTHER]_LV10_.bms")

test.readAll()
df = test.extractToPandas()

print(df)
