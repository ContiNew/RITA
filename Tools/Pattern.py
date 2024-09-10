import ChartFormat.bms as bms
import numpy as np
import pandas as pd

LANE_ORDER = ["16","11","12","13","14","15","18","19"]

class ChartMatrix:
    def __init__(self, chart:bms.BMS):
        self.chartMatrix, self.min_dist = self.chartToMatrix(chart)
        
        
    def chartToMatrix(self,chart:bms.BMS)-> tuple[pd.DataFrame, float]:
        if not chart.isRead: chart.readAll(); chart.close()
        df = chart.extractToPandas()

        beatstamps = df['beatstamp'].sort_values().unique()
        min_diff = np.diff(beatstamps).min() # 노트간 최소 비트 거리

        min_beatstamp = beatstamps.min()
        max_beatstamp = beatstamps.max()
        beatstamp_points = np.arange(min_beatstamp, max_beatstamp + min_diff, min_diff)
        # 비트 스탬프 그리드를 위한 Point 생성

        grid = pd.DataFrame(beatstamp_points, columns=['beatstamp'])
        for lane in df['laneInfo'].unique(): grid[lane] = 0
        # 포인트로 그리드 생성 및 그리드 완성

        df = df.pivot_table(index='beatstamp', columns='laneInfo', aggfunc='size', fill_value=0).reset_index()
        # 차트 데이터 프레임을 그리드와 합치기 위한 Form으로 바꿔줌
        merged_df = pd.merge(grid, df, on='beatstamp', how='left').fillna(0)
        
        for col in merged_df.filter(like='_x').columns:
            merged_df[col.replace('_x', '')] = merged_df[col].add(merged_df[col.replace('_x', '_y')], fill_value=0)
            merged_df.drop([col, col.replace('_x', '_y')], axis=1, inplace=True)

        merged_df.set_index('beatstamp', inplace=True)
        merged_df = merged_df.astype(int)
        merged_df = merged_df[LANE_ORDER] # 인게임에서의 순서대로 열정렬.      
        return (merged_df, min_diff)
        
        
        


