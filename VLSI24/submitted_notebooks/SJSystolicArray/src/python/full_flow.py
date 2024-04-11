import torch
import torch.nn.functional as F
import cv2
from canny import CannyFilter
from seq_generator import (gen_load_seq_idx, gen_load_seq, binary, fp32_to_fxps86binary, 
                           fp32_to_fxps86, add_result_seq, gen_load_result_seq)

import os

filter_size = 3
pad = filter_size // 2
image_size = 256
psum_size = int(image_size - 2*((filter_size-1)/2) + 2*pad)
filename = 'rubiks_cube.jpg'

# Read image, resize and convert to grayscale
image = cv2.imread(filename) 
image = cv2.resize(image, (image_size, image_size))  # original 256*256
gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
  
# Convert the image to Torch tensor 
img_tensor = torch.from_numpy(gray_image).unsqueeze(2)  #  transform(image)
img_tensor = img_tensor.permute(2, 0, 1).unsqueeze(0)

# Run inference
model = CannyFilter()
grad_x, grad_y, grad_magnitude, grad_orientation, thin_edges = model(img_tensor.float())

# Save image results
cv2.imwrite('edge_rubiks_cube.jpg', grad_magnitude[0].permute(1, 2, 0).detach().numpy())

# Generate load sequence for Systolic Array
ifmap = torch.load('img_0.pt').squeeze()//2
ifmap = F.pad(ifmap, (pad, pad, pad, pad), "constant", 0)
psum = torch.zeros((psum_size, psum_size), dtype=torch.int8)
load_seq_idx = gen_load_seq_idx(image_size+2, filter_size)
load_seq_idx = add_result_seq(load_seq_idx)

# Sequence for convolving image and sobel_filter_x to get grad_x
filter = torch.load('soble_filter_x_weight.pt').squeeze()
filter = fp32_to_fxps86binary(filter.squeeze())
result_x = torch.load('soble_result_x_0.pt').squeeze()//2
result_x = torch.clamp(result_x, min=-127, max=127)
load_seq_x = gen_load_result_seq(ifmap, filter, psum, result_x, load_seq_idx)
f = open("seq_x.txt", "w")
f.write("255,214,0\n")
for seq in torch.tensor(load_seq_x):
    print_seq = ','.join([str(x) for x in seq.to(dtype=torch.uint8).tolist()])
    f.write(f'{print_seq}\n')
f.close()

# Sequence for convolving image and sobel_filter_y to get grad_y
filter = torch.load('soble_filter_y_weight.pt').squeeze()
filter = fp32_to_fxps86binary(filter.squeeze())
result_y = torch.load('soble_result_y_0.pt').squeeze()//2
result_y = torch.clamp(result_y, min=-127, max=127)
load_seq_y = gen_load_result_seq(ifmap, filter, psum, result_y, load_seq_idx)
f = open("seq_y.txt", "w")
f.write("255,214,0\n")
for seq in torch.tensor(load_seq_y):
    print_seq = ','.join([str(x) for x in seq.to(dtype=torch.uint8).tolist()])
    f.write(f'{print_seq}\n')
f.close()

os.system("cp seq_x.txt /content/convInput.txt")
os.system("/content/obj_dir/Vtop > /content/SystolicArray/src/python/seq_x_SA.txt")

# Get the Systolic Array result
result_x_seq_sa = []
with open("seq_x_SA.txt", "r") as filestream:
    filestream.readline()
    for line in filestream:
        line = line.strip()
        if line:
            elems = line.split(",")
            result_x_seq_sa += [[int(elems[0]), int(elems[1]), int(elems[2])]]
result_x_seq_sa = torch.tensor(result_x_seq_sa)
result_x_sa = torch.zeros(result_x.shape, dtype=torch.int8)
for seq, ele in zip(load_seq_idx, result_x_seq_sa):
    if seq[2][0] != -1:
        result_x_sa[seq[2][1], seq[2][2]] = ele[2]

os.system("cp seq_y.txt /content/convInput.txt")
os.system("/content/obj_dir/Vtop > /content/SystolicArray/src/python/seq_y_SA.txt")
#os.system("rm /content/convInput.txt")

result_y_seq_sa = []
with open("seq_y_SA.txt", "r") as filestream:
    filestream.readline()
    for line in filestream:
        line = line.strip()
        if line:
            elems = line.split(",")
            result_y_seq_sa += [[int(elems[0]), int(elems[1]), int(elems[2])]]
result_y_seq_sa = torch.tensor(result_y_seq_sa)
result_y_sa = torch.zeros(result_y.shape, dtype=torch.int8)
for seq, ele in zip(load_seq_idx, result_y_seq_sa):
    if seq[2][0] != -1:
        result_y_sa[seq[2][1], seq[2][2]] = ele[2]

# Verify Systolic Array result
compare = result_x_sa.eq(result_x)
print(f'Systolic Array Result Correct: {torch.all(compare)}')

# Plot Systolic Array result
grad_x, grad_y, grad_magnitude, grad_orientation, thin_edges = model(img_tensor.float(),
                                                                     use_sa=True,
                                                                     grad_x_sa=result_x_sa.unsqueeze(0).unsqueeze(0)*2,
                                                                     grad_y_sa=result_y_sa.unsqueeze(0).unsqueeze(0)*2)
cv2.imwrite('edge_rubiks_cube_sa.jpg', grad_magnitude[0].permute(1, 2, 0).detach().numpy())