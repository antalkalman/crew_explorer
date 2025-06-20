import matplotlib
matplotlib.use('TkAgg')  # Only use this on your desktop, NOT in headless environments

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from PIL import Image
from scipy.ndimage import gaussian_filter

# Parameters
size = 50
iterations = 20
scale_factor = 64
blur_sigma = 1.0

# Initialize the grid
grid = np.random.choice([0, 1], size=(size, size))
neighbor_offsets = [(-1, -1), (-1, 0), (-1, 1),
                    ( 0, -1),          ( 0, 1),
                    ( 1, -1), ( 1, 0), ( 1, 1)]

def majority_color(i, j, grid):
    black = 0
    white = 0
    for dx, dy in neighbor_offsets:
        ni, nj = i + dx, j + dy
        if 0 <= ni < size and 0 <= nj < size:
            if grid[ni, nj] == 1:
                black += 1
            else:
                white += 1
    if black > white:
        return 1
    elif white > black:
        return 0
    else:
        return grid[i, j]

def process_frame(grid):
    grayscale = np.zeros_like(grid, dtype=float)
    for i in range(size):
        for j in range(size):
            black_neighbors = 0
            for dx, dy in neighbor_offsets:
                ni, nj = i + dx, j + dy
                if 0 <= ni < size and 0 <= nj < size:
                    black_neighbors += grid[ni, nj]
            grayscale[i, j] = black_neighbors / 8.0

    grayscale_img = (grayscale * 255).astype(np.uint8)
    grayscale_pil = Image.fromarray(grayscale_img)
    new_size = (grayscale_pil.width * scale_factor, grayscale_pil.height * scale_factor)
    upscaled = grayscale_pil.resize(new_size, resample=Image.Resampling.BICUBIC)
    smoothed = gaussian_filter(np.array(upscaled).astype(float) / 255.0, sigma=blur_sigma)
    return smoothed

# Plot setup
fig, ax = plt.subplots()
initial_smoothed = process_frame(grid)
im = ax.imshow(initial_smoothed, cmap='gray', vmin=0, vmax=1)
ax.axis('off')

def update(frame):
    global grid
    new_grid = grid.copy()
    for i in range(size):
        for j in range(size):
            new_grid[i, j] = majority_color(i, j, grid)
    grid = new_grid
    smoothed = process_frame(grid)
    im.set_data(smoothed)
    return [im]

ani = FuncAnimation(fig, update, frames=iterations, interval=300, blit=False)
plt.show()
