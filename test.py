from ChartFormat.bms import BMS
from Tools.Pattern import ChartMatrix
from Tools.Pattern import extract_patterns_with_flex_window
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

test = BMS("E:/Backup From Lenovo/BMS Dataset/Filtered Dataset/160 [ANOTHER]_LV10_.bms")

test.readAll()
df = test.extractToPandas()

cm = ChartMatrix(test)

l=extract_patterns_with_flex_window(cm,pHeight=8,slide=8)

print("len of collected patterns", len(l))
print(l[0:3])
