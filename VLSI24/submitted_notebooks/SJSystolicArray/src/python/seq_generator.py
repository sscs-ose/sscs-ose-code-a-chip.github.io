
import torch
import argparse
import numpy as np
from fxpmath import Fxp

INIT, LOAD, RELOAD, RSLT = 0, 1, 2, 3
IFMP, FILT, PSUM = 0, 1, 2
IN1, IN2 = 0, 1
NUM_PE = 3

def get_int8_matrix(m, n):
    return torch.randint(-127, 127, (m, n), dtype=torch.int8)

def get_rand01_matrix(m, n):
    return torch.rand(m, n)

def binary(x, reverse=False, bits=8):
    if reverse: # for readability
        mask = 2**torch.arange(bits-1,-1,-1).to(x.device, x.dtype)
    else:    
        mask = 2**torch.arange(bits).to(x.device, x.dtype)
    return x.unsqueeze(-1).bitwise_and(mask).ne(0).byte()


def fp32_to_fxps86(matrix):
    return Fxp(matrix.detach().numpy(), dtype='fxp-s8/6') # 8bit: 1b-sign, 1b-int, 6b-frac


def fxps86_to_binary(matrix):
    matrix = [[np.packbits(list(map(int, ele))) for ele in row] for row in matrix.bin()]
    return torch.tensor(np.array(matrix)).squeeze()


def fp32_to_fxps86binary(matrix):
    return fxps86_to_binary(fp32_to_fxps86(matrix))


def ceildiv(a, b):
    return int(-(a // -b))


def gen_load_seq_idx(ifmap_size, filter_size):
    # data_idx = [matrix, row, col]
    load_seq = []

    edge = int((filter_size - 1)/2)
    output_size = ifmap_size - edge*2
    num_row_iter = ceildiv(output_size, NUM_PE)
    row_coverage = NUM_PE+edge*2 

    state = INIT
    for iter in range(num_row_iter+1):
        row_offset = iter*NUM_PE  # 0, 3, 5 ...
        for ifmp_col in range(ifmap_size):  # 0, 1 ..., 27
            for row in range(row_coverage):  # 0, 1, 2, 3, 4
                target_row = row_offset + row
                in1_idx = [IFMP, target_row, ifmp_col]
                if state == INIT:
                    if row < NUM_PE:  # 0, 1, 2, 3
                        in2_idx = [FILT, target_row, ifmp_col]
                    elif row == row_coverage-1:  # 4
                        load_seq[-1][IN2] = [IFMP, target_row, ifmp_col]
                        if ifmp_col == (filter_size-1): 
                            state = LOAD # enter load state sequence
                            in1_idx, in2_idx = [-1,-1,-1], [-1,-1,-1]
                            load_seq += [[in1_idx, in2_idx]]
                        continue
                    load_seq += [[in1_idx, in2_idx]]
                elif state == LOAD:
                    if row < row_coverage-1:
                        in1_idx = [IFMP, target_row, ifmp_col]
                        in2_idx = [-1,-1,-1]
                    else:
                        in1_idx = [-1,-1,-1]
                        in2_idx = [IFMP, target_row, ifmp_col]
                    if row < NUM_PE: # PSUM load handling
                        if not (target_row >= output_size):
                            if row == 0:
                                load_seq[-1][IN1] = [PSUM, target_row, ifmp_col-3]
                            else:                
                                load_seq[-1][IN2] = [PSUM, target_row, ifmp_col-3]
                    if (ifmp_col == (ifmap_size-1)) and (row == (row_coverage-1)) :
                        state = RELOAD
                    if target_row >= ifmap_size:
                        in1_idx, in2_idx = [-1,-1,-1], [-1,-1,-1]
                        load_seq += [[in1_idx, in2_idx]]
                        continue
                    load_seq += [[in1_idx, in2_idx]]
                elif state == RELOAD:
                    if row < NUM_PE and ifmp_col==0: # PSUM load handling
                        if not (target_row-filter_size >= output_size):
                            if row == 0:
                                load_seq[-1][IN1] = [PSUM, target_row-filter_size, output_size-1]
                            else:                
                                load_seq[-1][IN2] = [PSUM, target_row-filter_size, output_size-1]
                    if row == row_coverage-1:  # 4
                        if not (target_row >= ifmap_size):
                            load_seq[-1][IN2] = [IFMP, target_row, ifmp_col]
                        if ifmp_col == (filter_size-1): 
                            state = LOAD # enter load state sequence
                            in1_idx, in2_idx = [-1,-1,-1], [-1,-1,-1]
                            load_seq += [[in1_idx, in2_idx]]
                        continue
                    if target_row >= ifmap_size:
                        in1_idx, in2_idx = [-1,-1,-1], [-1,-1,-1]
                        load_seq += [[in1_idx, in2_idx]]
                        continue
                    in2_idx = [-1,-1,-1]
                    load_seq += [[in1_idx, in2_idx]]
    return load_seq


def add_result_seq(load_seq):
    for idx, seq in enumerate(load_seq):
        if len(seq)==3:
            in1, in2, in3 = seq
        else:
            in1, in2 = seq
            load_seq[idx] += [[-1,-1,-1]]
        if in1[0]==PSUM:
            load_seq[idx+3] += [[RSLT, in1[1], in1[2]]]
        elif in2[0]==PSUM:
            load_seq[idx+3] += [[RSLT, in2[1], in2[2]]]
        
    return load_seq


def gen_load_seq(ifmap, filter, psum, load_seq_idx):
    load_seq = []
    in_matrix = [ifmap, filter, psum]

    for seq in load_seq_idx:
        if seq[0][0] == -1:
            in1 = 0
        else:
            in1 = in_matrix[seq[0][0]][seq[0][1]][seq[0][2]]
        if seq[1][0] == -1:
            in2 = 0
        else:
            in2 = in_matrix[seq[1][0]][seq[1][1]][seq[1][2]]
        load_seq += [[in1, in2]]
    
    return load_seq


def gen_load_result_seq(ifmap, filter, psum, result, load_seq_idx):
    load_seq = []
    in_matrix = [ifmap, filter, psum, result]

    for seq in load_seq_idx:
        if seq[0][0] == -1:
            in1 = 0
        else:
            in1 = in_matrix[seq[0][0]][seq[0][1]][seq[0][2]]
        if seq[1][0] == -1:
            in2 = 0
        else:
            in2 = in_matrix[seq[1][0]][seq[1][1]][seq[1][2]]
        if seq[2][0] == -1:
            in3 = 0
        else:
            in3 = in_matrix[seq[2][0]][seq[2][1]][seq[2][2]]
        load_seq += [[in1, in2, in3]]
    
    return load_seq


def main():
    parser = argparse.ArgumentParser(description='PyTorch INT8 Conv Example')
    parser.add_argument('--m', type=int, default=6,
                        help='ifmap m x m (default: 6)')
    parser.add_argument('--n', type=int, default=3,
                        help='filter n x n (default: 3)')
    
    parser.add_argument('--no-binary', action='store_true', default=False,
                        help='print in binary 2s complement')
    parser.add_argument('--no-cuda', action='store_true', default=False,
                        help='disables CUDA training')
    parser.add_argument('--seed', type=int, default=1,
                        help='random seed (default: 1)')
    args = parser.parse_args()
    torch.manual_seed(args.seed)
    
    use_cuda = not args.no_cuda and torch.cuda.is_available()
    device = torch.device("cuda") if use_cuda else torch.device("cpu")

    filter_fp32 = get_rand01_matrix(2,3)
    filter_fxp = fp32_to_fxps86(filter_fp32)
    filter_fxpbin = fxps86_to_binary(filter_fxp)
    print(filter_fp32)
    print(filter_fxp)
    print(filter_fxpbin)

    load_seq_idx =gen_load_seq_idx(6, 3)
    # load_seq_idx = (torch.tensor(load_seq_idx) + 1).tolist()
    for seq_idx in load_seq_idx:
        print(seq_idx)

    ifmap = get_int8_matrix(args.m, args.m) 
    filter = get_int8_matrix(args.n, args.n)
    result = torch.nn.functional.conv2d(torch.unsqueeze(torch.unsqueeze(ifmap,0),0).type(torch.int32), 
                                        torch.unsqueeze(torch.unsqueeze(filter,0),0).type(torch.int32))
    result = torch.squeeze(result)

    psum = torch.zeros((4, 4), dtype=torch.int8)
    load_seq = gen_load_seq(ifmap, filter, psum, load_seq_idx)
    print("========================")
    for seq in torch.tensor(load_seq):
        print(seq.tolist())
    
    print("========================")
    for seq in binary(torch.tensor(load_seq)):
        print(seq.tolist())
    
    print("\n- ifmap - INT8 ---------------")
    print(ifmap)
    print("\n- filter - INT8 ---------------")
    print(filter)
    print("\n- Conv result - INT32 ----------")
    print(result)
    if not args.no_binary:
        print("\n- ifmap - 2's ----------------")
        print(binary(ifmap, reverse=True))
        print("\n- filter - 2's ----------------")
        print(binary(filter, reverse=True))
        print("\n- result - 2's -----------")
        print(binary(result, reverse=True, bits=32))

if __name__ == '__main__':
    main()