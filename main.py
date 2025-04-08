
"""
Centroid-Guided Regional Clustering Annotation
"""

import cv2
import numpy as np
from sklearn.cluster import DBSCAN
import os

def dbscan_and_generate_mask(sub_image, eps=5, min_samples=25):
    """
    Perform DBSCAN clustering and generate noise mask
    
    Args:
        sub_image: Local image region
        eps: DBSCAN neighborhood radius
        min_samples: Minimum samples for core point
    
    Returns:
        Binary noise mask in uint8 format
    """
    h, w, c = sub_image.shape
    img_reshaped = sub_image.reshape(-1, 3)
    dbscan = DBSCAN(eps=eps, min_samples=min_samples)
    labels = dbscan.fit_predict(img_reshaped)
    
    # Get largest cluster as background
    unique, counts = np.unique(labels, return_counts=True)
    cluster_counts = dict(zip(unique, counts))
    background_label = max(cluster_counts, key=cluster_counts.get)
    
    # Generate noise mask
    noise_mask = np.zeros((h, w), dtype=np.uint8)
    noise_mask[labels.reshape(h, w) != background_label] = 255
    return noise_mask


def process_single_image(img_path, mask_path, output_dir, 
                        eps=55, min_samples=100,
                        window_radius=20, core_radius=4):
    """
    Process single image with configurable parameters
    
    Args:
        img_path: Input image path
        mask_path: Initial mask path(centroid labels)
        output_dir: Output directory
        eps: DBSCAN parameter
        min_samples: DBSCAN parameter
        window_radius: Analysis window radius
        core_radius: Core processing radius
    """
    # Read image
    img = cv2.imread(img_path)
    if img is None:
        print(f"Image read failed: {img_path}")
        return
    
    # Read mask
    mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
    if mask is None:
        print(f"Mask read failed: {mask_path}")
        return
    
    os.makedirs(output_dir, exist_ok=True)
    
    final_mask = np.zeros_like(mask)
    white_pixels = np.argwhere(mask == 255)
    
    # Window parameters calculation
    # window_size = 2 * window_radius + 1
    # core_size = 2 * core_radius + 1
    
    for y, x in white_pixels:
        # Calculate analysis window
        y_min = max(0, y - window_radius)
        y_max = min(mask.shape[0], y + window_radius + 1)
        x_min = max(0, x - window_radius)
        x_max = min(mask.shape[1], x + window_radius + 1)
        
        sub_image = img[y_min:y_max, x_min:x_max]
        noise_mask = dbscan_and_generate_mask(sub_image, eps, min_samples)
        
        # Calculate core region
        y_min_core = max(0, y - core_radius)
        y_max_core = min(mask.shape[0], y + core_radius + 1)
        x_min_core = max(0, x - core_radius)
        x_max_core = min(mask.shape[1], x + core_radius + 1)
        
        # Apply processing result
        final_mask[y_min_core:y_max_core, x_min_core:x_max_core] = \
            noise_mask[y_min_core - y_min : y_max_core - y_min,
                       x_min_core - x_min : x_max_core - x_min]
    
    # Handle empty mask
    if cv2.countNonZero(final_mask) == 0:
        final_mask = mask
        print("Warning: Empty mask generated, using original mask")
    
    # Save result
    output_path = os.path.join(output_dir, os.path.basename(img_path))
    cv2.imwrite(output_path, final_mask)
    print(f"Processing completed: {output_path}")
    

def batch_process_dataset(base_dir, 
                         eps_values=(55,), 
                         min_samples_list=(100,),
                         window_radius=20,
                         core_radius=4):
    """
    Batch processing pipeline
    
    Args:
        base_dir: Dataset root path
        eps_values: List of eps parameters to try
        min_samples_list: List of min_samples to try
        window_radius: Analysis window radius
        core_radius: Core processing radius
    """
    # Path configuration
    img_root = os.path.join(base_dir, "img")
    mask_root = os.path.join(base_dir, "mask-pre")
    output_root = os.path.join(base_dir, "mask-dbscan")
    
    print("Starting batch processing...")
    print("Input directory: {img_root}")
    print("Output directory: {output_root}")

    for min_samples in min_samples_list:
        for eps in eps_values:
            param_dir = os.path.join(output_root, 
                                    f"minsamples_{min_samples}", 
                                    f"eps{eps}")
            
            # Traverse folders
            for folder in os.listdir(img_root):
                img_folder = os.path.join(img_root, folder)
                mask_folder = os.path.join(mask_root, folder)
                output_folder = os.path.join(param_dir, folder)
                
                if not os.path.exists(mask_folder):
                    print("Skipping unmatched folder: {folder}")
                    continue
                
                # Process each image
                for img_file in os.listdir(img_folder):
                    if not img_file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                        continue
                    
                    img_path = os.path.join(img_folder, img_file)
                    mask_path = os.path.join(mask_folder, 
                                           os.path.splitext(img_file)[0] + ".png")
                    
                    if not os.path.exists(mask_path):
                        print("Mask not found: {mask_path}")
                        continue
                    
                    process_single_image(
                        img_path=img_path,
                        mask_path=mask_path,
                        output_dir=output_folder,
                        eps=eps,
                        min_samples=min_samples,
                        window_radius=window_radius,
                        core_radius=core_radius
                    )

if __name__ == "__main__":
    # Configure relative path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_root = os.path.join(current_dir, "data/datasetA")
    
    # Execute batch processing 
    batch_process_dataset(
        base_dir=dataset_root,
        eps_values=[55],  
        min_samples_list=[100],
        window_radius=10,  # Adjustable window size
        core_radius=4     # Adjustable core region
        # Window parameters calculation
        # window_size = 2 * window_radius + 1
        # core_size = 2 * core_radius + 1
    )
    
    print("All processing completed!")
