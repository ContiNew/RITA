import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os



class ChartVisualReporter:
    def __init__(self, matchedReplay:pd.DataFrame ,overallDifficulty):
        # Define judgement_ranges based on OD
        OD = overallDifficulty
        self.judgement_ranges = {
            "PERFECT": 16 - 3 * OD,
            "GREAT": 64 - 3 * OD,
            "GOOD": 97 - 3 * OD,
            "OK": 127 - 3 * OD,
            "BAD": 151 - 3 * OD
        }
        self.matchedReplay = matchedReplay

    def time_interval_plot(self, isPlotting:bool=True, isSaving:bool=False, path:str=""):
        df = self.matchedReplay.copy()
        df['color'] = df['interval'].apply(self.get_color)
        # Plotting
        plt.figure(figsize=(12, 6))
        plt.scatter(df['recorded_timestamp'], df['interval'], c=df['color'], label="Interval")
        plt.axhline(0, color='black', linestyle='--', linewidth=0.5)  # Reference line at 0 interval
        plt.xlabel('Recorded Timestamp')
        plt.ylabel('Interval')
        plt.title('Interval Changes Over Time with Judgement-Based Coloring')
        if isPlotting:
            plt.show()
        else:
            plt.savefig(path)

    
    def interval_overay_plot(self, isPlotting:bool=True, isSaving:bool=False, path:str=""):
        df = self.matchedReplay.copy()
        df['color'] = df['interval'].apply(self.get_color)

        # Plotting
        plt.figure(figsize=(10, 8))

        # Define lane positions and number of lanes
        num_lanes = 4
        lane_positions = np.arange(num_lanes) * 2  # Spacing out lanes

        # Plot notes and player hits on each lane
        for lane in range(num_lanes):
            lane_data = df[df['lane'] == lane]
            lane_pos = lane_positions[lane]
            
            # Plot target notes
            plt.scatter(lane_data['target_timestamp'], [lane_pos] * len(lane_data), 
                        color='lightgray', s=100, label="Target Notes" if lane == 0 else "")
            
            # Plot recorded notes with interval color
            plt.scatter(lane_data['recorded_timestamp'], [lane_pos] * len(lane_data) + lane_data['interval'] / 10,
                        c=lane_data['color'], s=50, label="Recorded Notes" if lane == 0 else "")

        plt.xlabel("Timestamp")
        plt.ylabel("Lane Position")
        plt.title("Rhythm Game Replay Visualization: Notes with Timing Overlay")
        plt.legend()
        if isPlotting:
            plt.show()
        else:
            plt.savefig(path)

    # Calculate absolute interval and assign colors based on ranges
    def get_color(self,interval):
        abs_interval = abs(interval)
        if abs_interval <= self.judgement_ranges["PERFECT"]:
            return 'blue'  # PERFECT range
        elif abs_interval <= self.judgement_ranges["GREAT"]:
            return 'green'  # GREAT range
        elif abs_interval <= self.judgement_ranges["GOOD"]:
            return 'yellow'  # GOOD range
        elif abs_interval <= self.judgement_ranges["OK"]:
            return 'orange'  # OK range
        elif abs_interval <= self.judgement_ranges["BAD"]:
            return 'red'  # BAD range
        else:
            return 'gray'  # MISS range
        
    
   
