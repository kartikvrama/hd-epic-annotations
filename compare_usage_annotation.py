import os
import glob
import json
from math import floor, ceil
import numpy as np
import pdb
import matplotlib.pyplot as plt

video_id = "P07-20240529-131737"

def calculate_precision_recall_f1(confusion_matrix):
    """
    Calculates precision, recall, and F1 score for a binary (2x2) confusion matrix.

    Args:
        confusion_matrix (np.ndarray): 2x2 array where
            rows = predicted [0, 1], columns = ground truth [0, 1]

    Returns:
        dict: {
            "precision": float,
            "recall": float,
            "f1": float,
            "per_class": {
                0: {"precision": float, "recall": float, "f1": float},
                1: {"precision": float, "recall": float, "f1": float}
            }
        }
    """
    # True negatives, false negatives, false positives, true positives
    # confusion_matrix[pred][actual]
    # [ [TN, FN],   [FP, TP] ]
    #    0    1        0    1  
    tp = confusion_matrix[1,1]
    tn = confusion_matrix[0,0]
    fp = confusion_matrix[1,0]
    fn = confusion_matrix[0,1]

    # For class 0 ("not used")
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    metrics = {
        "precision": prec,
        "recall": rec,
        "f1": f1,
    }
    return metrics


def main():

    ## LLM annotations
    usage_dir = "outputs/object_usage_labels_model-qwen3-vl:30b_max-segment-length-30_long_temp-80_numPredict-2000_tries-3-NoConfidences"
    filename = f"object_usage_labels_{video_id}.jsonl"
    filepath = os.path.join(usage_dir, filename)
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            object_usage_annotations = [json.loads(line) for line in f]

    ## Manual annotations
    usage_dir = "manual_usage_annotations"
    annotation_files = glob.glob(os.path.join(usage_dir, "usage_labels_manual-FILE*.json"))
    if annotation_files:
        label_filepath = max(annotation_files, key=os.path.getmtime)
        with open(label_filepath, "r") as f:
            manual_usage_annotations = json.load(f)
    else:
        raise FileNotFoundError("No manual usage annotations found")

    # Confusion matrix for classifying active and passive segments as used or not used
    active_segment_cf = np.zeros((2,2))
    passive_segment_cf = np.zeros((2,2))
    num_missing_labels = {"active": 0, "passive": 0}
    num_multiple_matching_annotations = 0

    duration_prediction_tuples = {"active": [], "passive": []}

    confidences_per_cat = {"active": [], "passive": []}

    for annotation in object_usage_annotations:
        object_name = annotation.get("object_name")
        if any(char.isdigit() for char in object_name):
            # print(f"Skipping object {object_name} because it contains digits")
            continue

        usage_label = annotation.get("llm_response_json", {})
        if not usage_label:
            num_missing_labels[annotation.get("segment_category", "passive")] += 1
            continue
        usage_llm = usage_label["is_used"]
        time_start = annotation.get("time_start")
        time_end = annotation.get("time_end")
        duration = time_end - time_start
        segment_category = annotation.get("segment_category")
        confidence = usage_label.get("prediction_confidence")
        confidences_per_cat[segment_category].append(confidence)

        ## Find matching manual annotations
        matching_manual_annotations = [
            manual_annotation for manual_annotation in sorted(manual_usage_annotations[video_id]["labels"], key=lambda x: x.get("time_start"))
            if manual_annotation.get("object_name") == annotation.get("object_name")
            and manual_annotation.get("time_start") < time_start
            and manual_annotation.get("time_end") > time_end
            ]
        if not matching_manual_annotations:
            continue

        print(f"Time start: {time_start}, Time end: {time_end}, Segment category: {segment_category}, Object name: {annotation.get('object_name')}")
        if len(matching_manual_annotations) > 1:
            print(f"    - Multiple matching manual annotations ({len(matching_manual_annotations)}) found for object {annotation.get('object_name')} between {time_start} and {time_end}, skippping")
            # pdb.set_trace()
            num_multiple_matching_annotations += 1
            # continue

        usage_gt = True if matching_manual_annotations[0].get("annotation").lower() == "used" else False

        x = 1 - int(usage_gt) ## 0 if used, 1 if not used
        y = 1 - int(usage_llm) ## 0 if used, 1 if not used
        if segment_category == "active":
            active_segment_cf[x,y] += 1
        else:
            passive_segment_cf[x,y] += 1

        duration_prediction_tuples[segment_category].append((duration, usage_llm))

    print(f"Number of missing labels: {num_missing_labels}")
    print(f"Number of multiple matching annotations: {num_multiple_matching_annotations}")
    print(f"--------------------------------\nConfusion matrix for active segments: \n{active_segment_cf}")
    print(f"--------------------------------\nMetrics for active segments: \n{calculate_precision_recall_f1(active_segment_cf)}")
    print(f"--------------------------------\nConfusion matrix for passive segments: \n{passive_segment_cf}")
    print(f"--------------------------------\nMetrics for passive segments: \n{calculate_precision_recall_f1(passive_segment_cf)}")

    ## Plot duration vs prediction
    plt.figure(figsize=(10, 5))
    plt.scatter([tup[0] for tup in duration_prediction_tuples["active"]], [tup[1] for tup in duration_prediction_tuples["active"]], color="red", label="Active")
    plt.scatter([tup[0] for tup in duration_prediction_tuples["passive"]], [tup[1] for tup in duration_prediction_tuples["passive"]], color="blue", label="Passive")
    plt.xlabel("Duration (seconds)")
    plt.ylabel("Prediction")
    plt.title("Duration vs Prediction")
    plt.legend()
    plt.show()
    plt.savefig(f"plots/duration_vs_prediction_{video_id}.png")

    counts_active = [(confidence, confidences_per_cat["active"].count(confidence)) for confidence in set(confidences_per_cat["active"])]
    counts_passive = [(confidence, confidences_per_cat["passive"].count(confidence)) for confidence in set(confidences_per_cat["passive"])]
    print(f"Counts for active segments: {dict(counts_active)}")
    print(f"Counts for passive segments: {dict(counts_passive)}")


if __name__ == "__main__":
    main()
