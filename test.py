import ChartFormat.bms as bms
from Tools.Pattern import ChartMatrix
import numpy as np
import pandas as pd

test = bms.BMS("E:/Backup From Lenovo/BMS Dataset/Filtered Dataset/160 [ANOTHER]_LV10_.bms")

test.readAll()
df = test.extractToPandas()

cm = ChartMatrix(test)

print(cm.chartMatrix) 