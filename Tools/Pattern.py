import ChartFormat.bms as bms
import numpy as np


class ChartMatrix:
    def __init__(self, chart:bms.BMS):
        self.chartMatrix = self.chartToMatrix(chart)
        
        
    def chartToMatrix(chart:bms.BMS):
        if not chart.isRead: chart.readAll(); chart.close()
        df = chart.extractToPandas()
        matrix = df.pivot_table(index='beatstamp', columns='laneInfo', aggfunc='size', fill_value=0)
        matrix = matrix.reset_index(drop=True)
        return matrix
        
        
        


