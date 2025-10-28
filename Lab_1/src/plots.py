# -*- coding: utf-8 -*-
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

def hist_rgb(img_arr: np.ndarray, out_png: str, title: str):
    fig, axes = plt.subplots(2,3, figsize=(12,6))
    for i, col in enumerate(['R','G','B']):
        axes[0,i].hist(img_arr[...,i].ravel(), bins=256)
        axes[0,i].set_title(f"Source {col}")
    axes[1,0].axis('off'); axes[1,1].axis('off'); axes[1,2].axis('off')
    fig.suptitle(title)
    plt.tight_layout()
    fig.savefig(out_png)
    plt.close(fig)

def save_xy_scatter(x: np.ndarray, y: np.ndarray, out_png: str, title: str):
    # Доп. график при желании (не обязателен)
    plt.figure(figsize=(5,5))
    plt.scatter(x, y, s=1)
    plt.title(title)
    plt.savefig(out_png)
    plt.close()