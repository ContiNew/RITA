import ChartFormat.bms as bms

test = bms.BMS("E:/Backup From Lenovo/BMS Dataset/Filtered Dataset/160 [ANOTHER]_LV10_.bms")

test.readAll()
df = test.extractToPandas()

matrix = df.pivot_table(index='beatstamp', columns='laneInfo', aggfunc='size', fill_value=0)

# beatstamp 열을 제거하고 행 이름으로만 유지
matrix_without_beatstamp_column = matrix.reset_index(drop=True)

# 결과 출력
print(matrix_without_beatstamp_column)
