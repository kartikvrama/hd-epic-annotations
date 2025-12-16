import os
import json
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from utils import extract_touches_from_track


def plot_object_with_labels(track_sequence, object_name, object_id, ax, y_position, label_dict, video_end_time=None):
    """Plot object movement with labeled periods."""
    print("lets get them touches")
    touch_points = extract_touches_from_track(track_sequence)
    
    if len(touch_points) < 2:
        return  # Skip objects with less than 2 touches
    
    # Plot all touch points
    plot_x = []
    plot_o = []
    plot_points = []
    for touch in touch_points:
        plot_x.append(touch["pick"])
        plot_o.append(touch["drop"])
        plot_points.extend([touch["pick"], touch["drop"]])
    
    # Plot main track line (light gray background)
    if plot_points:
        ax.plot(plot_points, [y_position] * len(plot_points), "-", color="black", linewidth=1, alpha=0.2)
        ax.plot(plot_x, [y_position] * len(plot_x), "x", color="gray", markersize=4, alpha=0.5)
        ax.plot(plot_o, [y_position] * len(plot_o), "o", color="gray", markersize=4, alpha=0.5)
    
    # Find the last touch (last pick and drop)
    if touch_points:
        last_touch = touch_points[-1]
        last_pick = last_touch["pick"]
        last_drop = last_touch["drop"]
        # Draw a rectangle ("box") around the last pick and drop
        box_y = y_position - 0.15
        box_height = 0.3
        box_x_start = min(last_pick, last_drop) - 1
        box_x_end = max(last_pick, last_drop) + 1
        box_width = box_x_end - box_x_start
        rect = plt.Rectangle(
            (box_x_start, box_y), 
            box_width, 
            box_height, 
            linewidth=1, 
            edgecolor='green', 
            facecolor='none', 
            zorder=3
        )
        ax.add_patch(rect)
    
    print("basic touches plotted")
    ## Label dictionary structure    
    # {
    #   "object_name": "plastic spoon",
    #   "association_id": "85e1cf228aa07339",
    #   "pre_lastTrace_start": 49.37043,
    #   "pre_lastTrace_end": 56.39729,
    #   "pre_lastTrace_label": "idle",
    #   "lastTrace_start": 56.39729,
    #   "lastTrace_end": 124.32241,
    #   "lastTrace_label": "inuse",
    #   "after_lastTrace_start": 124.32241,
    #   "after_lastTrace_label": "idle"
    # },


    # import pdb; pdb.set_trace()
    # Plot shaded bars for usage periods
    if label_dict and not label_dict.get("skip", False):
        # Determine video end time (use provided or max from all drops)
        if video_end_time is None:
            video_end_time = max(plot_o) if plot_o else label_dict.get("after_lastTrace_start", 0) + 100

        # ax.axhspan(y_position - 0.2, y_position + 0.2, xmin=0, xmax=video_end_time, 
        #               color="blue", alpha=0.8, zorder=0)

        # Pre-lastTrace period
        if "pre_lastTrace_start" in label_dict and "pre_lastTrace_end" in label_dict:
            start = label_dict["pre_lastTrace_start"]
            end = label_dict["pre_lastTrace_end"]
            label = label_dict.get("pre_lastTrace_label")
            color = "red" if label == "inuse" else "blue"
            print(f"plotting pre_lastTrace from {start} to {end} with color {color}")
            ax.axhspan(y_position - 0.2, y_position + 0.2, xmin=int(start), xmax=int(end), 
                      color=color, alpha=0.4, zorder=0)
        
        # LastTrace period
        if "lastTrace_start" in label_dict and "lastTrace_end" in label_dict:
            start = label_dict["lastTrace_start"]
            end = label_dict["lastTrace_end"]
            label = label_dict.get("lastTrace_label")
            color = "red" if label == "inuse" else "blue"
            print(f"plotting lastTrace from {start} to {end} with color {color}")
            ax.axhspan(y_position - 0.2, y_position + 0.2, xmin=int(start), xmax=int(end), 
                      color=color, alpha=0.4, zorder=0)
        
        # After-lastTrace period
        if "after_lastTrace_start" in label_dict:
            start = label_dict["after_lastTrace_start"]
            end = video_end_time
            label = label_dict.get("after_lastTrace_label")
            color = "red" if label == "inuse" else "blue"
            print(f"plotting after_lastTrace from {start} to {end} with color {color}")
            ax.axhspan(y_position - 0.2, y_position + 0.2, xmin=int(start), xmax=int(end), 
                      color=color, alpha=0.4, zorder=0)
    print("--------------------------------")

def main():
    labels_file = "plots/object_usage_labels.json"
    if not os.path.exists(labels_file):
        print(f"Labels file not found: {labels_file}")
        return
    
    with open(labels_file, "r") as f:
        all_labels = json.load(f)
    
    # Load association info
    with open("scene-and-object-movements/assoc_info.json") as f:
        data_assoc = json.load(f)
    
    os.makedirs("plots", exist_ok=True)
    
    # Process each video
    for video_id, video_labels in all_labels.items():
        if video_id not in data_assoc:
            print(f"Skipping video {video_id} - not found in association data")
            continue
        print(f"Processing video: {video_id}")

        # Calculate video end time (maximum time from all objects in this video)
        video_end_time = 0
        for label_dict in video_labels:
            if label_dict.get("skip", False):
                continue
            object_id = label_dict['association_id']
            if object_id in data_assoc[video_id]:
                track_sequence = data_assoc[video_id][object_id]['tracks']
                touch_points = extract_touches_from_track(track_sequence)
                for touch in touch_points:
                    video_end_time = max(video_end_time, touch["drop"])
            # Also check after_lastTrace_start
            if "after_lastTrace_start" in label_dict:
                video_end_time = max(video_end_time, label_dict["after_lastTrace_start"])
        
        # Add a small buffer
        video_end_time += 10

        # Filter out skipped objects for plotting
        non_skipped_labels = [l for l in video_labels if not l.get("skip", False)]
        num_objects = len(non_skipped_labels)
        
        fig, ax = plt.subplots(figsize=(15, max(5, num_objects * 0.5)))
        ax.set_xlabel("Time (seconds)")
        ax.set_ylabel("Object")
        ax.set_title(f"Object Usage Labels - {video_id}")
        
        y_positions = []
        y_labels = []
        object_idx = 0
        
        for i, label_dict in enumerate(video_labels):
            if label_dict.get("skip", False):
                print(f"Skipping object {label_dict['object_name']} (ID: {label_dict['association_id']}) - already skipped")
                continue
            print(f"Processing object: {label_dict['object_name']} (ID: {label_dict['association_id']})")
            object_name = label_dict['object_name']
            object_id = label_dict['association_id']
            if object_id not in data_assoc[video_id]:
                print(f"  Warning: Object ID {object_id} not found in association data")
                continue
            track_sequence = data_assoc[video_id][object_id]['tracks']
            y_pos = object_idx
            plot_object_with_labels(track_sequence, object_name, object_id, ax, y_pos, label_dict, video_end_time)
            y_positions.append(y_pos)
            y_labels.append(f"{object_name}\n({object_id[:8]}...)")
            object_idx += 1
        
        # Set y-axis ticks and labels
        if y_positions:
            ax.set_yticks(y_positions)
            ax.set_yticklabels(y_labels, fontsize=8)
        
        # Set x-axis limits
        ax.set_xlim(0, video_end_time)
        
        # Add legend
        legend_elements = [
            Patch(facecolor='red', alpha=0.3, label='inuse'),
            Patch(facecolor='blue', alpha=0.3, label='idle')
        ]
        ax.legend(handles=legend_elements, loc='upper right')
        
        # Save the plot
        output_file = f"plots/{video_id}_usage_plot.png"
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"Saved plot to {output_file}")
        plt.close()


if __name__ == "__main__":
    main()
