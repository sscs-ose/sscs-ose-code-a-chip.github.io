//GQA只支持2
//embd size 支持 128 256 512 
//context len支持 64 128 256 512
//softmax_rc_shift 必须和rms_rc_shift一样
//power mode 和 debug mode打开了需要手动关闭
//qspi, burst cnt, MOSI为255， MISO为63 （FIFO深度限制）
//两clean kv cache之间需要保证最好至少1000个chip clk 
//SPI的优先级比QSPI高，在写QSPI时必须保证SPI为IDLE状态，不能浮空！！
//上电时先上电QSPI和SPI clk？？

//SPI CLK 是 FPGA CLK的一半
//保证chip clk是SPI CLK和QSPI CLK的四倍以上？？
 
`ifndef __SYS_DEFS_SVH__
`define __SYS_DEFS_SVH__

`define ASSERT_EN
`define MEM_ACCESS_CNT
`define INTERFACE_ENABLE //important !!! /disable for functional test for quick simulation, but need to enable for synthesis
// `define TRUE_MEM //TRUE MEM otherwise data array
// `define APR_TWO_HEADS
`define CHIP_TOP_SIMULATION
`timescale 1ns/1ps  
// `define CLOCK_PERIOD 2000
`define SD #0
    //////////////////////////////////////////////////
    //                                              //
    //              Layer parameters                //
    //                                              //
    //////////////////////////////////////////////////
`define HEAD_NUM  8 //for debugging, use small number for quick simumation

`define MAX_EMBD_SIZE 512
`define MAX_HEAD_DIM (`MAX_EMBD_SIZE/`HEAD_NUM)

`define MAX_CONTEXT_LENGTH 256
`define MAX_CONTEXT_LENGTH_WITH_GQA (`MAX_CONTEXT_LENGTH*2)

`define HEAD_CORE_NUM  16   //How many cores for one head
`define MAX_NUM_USER 1 //needs to be even number, because of 2 user share one mem

`define MAX_QKV_WEIGHT_COLS_PER_CORE (`MAX_EMBD_SIZE/`HEAD_NUM/`HEAD_CORE_NUM) 
`define MAX_TOKEN_PER_CORE (`MAX_CONTEXT_LENGTH_WITH_GQA/`HEAD_CORE_NUM) //每个core里面存放了多少个token，针对K矩阵
    //////////////////////////////////////////////////
    //                                              //
    //                Core Array                    //
    //                                              //
    //////////////////////////////////////////////////

`define IDATA_WIDTH   8
`define MAC_MULT_NUM  ${mac_num} //This is the number of MACs in one core, this is also the number of multipliers in one core
`define ODATA_WIDTH   (`IDATA_WIDTH*2+$clog2(`MAC_MULT_NUM)+5) //5 for no overflow in acc -BUCK

// `define ARR_CDATA_BIT   5 
`define CDATA_ACCU_NUM_WIDTH 10 //need to larger or equal to CDATA_SCALE_WIDTH (for residual)
`define CDATA_SCALE_WIDTH 10
`define CDATA_BIAS_WIDTH 16 
`define CDATA_SHIFT_WIDTH 5
`define QUANT_SCALE_RETIMING 3 //TODO

//abuf
`define ABUF_MAX_ITER_WIDTH 10 //TODO,需要调整为合理数值
`define ABUF_EMBD_REG_DEPTH `MAX_EMBD_SIZE/`MAC_MULT_NUM //如果MAX_CONTEXT_LENGTH*2 <= MAX_EMBD_SIZE的话

//core ctrl
`define OP_GEN_CNT_WIDTH   10  //TODO,需要调整为合理数值

//gbus
`define BUS_PACKET_FIFO_DEPTH  28 //dont need to be power of 2
`define GBUS_DATA_WIDTH    32

//arbiter
`define ROUND_ROBIN_ARBITER //Enable ROUND_ROBIN_ARBITER saves the BUS FIFO depth but increases the arbiter latency
`define BUS_REQ_MAX_NUM  `HEAD_CORE_NUM
`define ARBITER_REQ_WIDTH  `BUS_REQ_MAX_NUM

//recompute RMS
`define RECOMPUTE_SCALE_WIDTH 24
`define RECOMPUTE_SHIFT_WIDTH 5
`define RECOMPUTE_FIFO_DEPTH 16 
`define RC_RETIMING_REG_NUM 7 //TODO
`define FIXED_SQUARE_SUM_WIDTH 24

//recompute Softmax RMSNORM
`define SOFTMAX_RETIMING_NUM 8
`define RMSNORM_RT_NUM 4

//residaul adder
`define RESIDUAL_DEQUANT_RETIMING 7

`define USER_ID_WIDTH  $clog2(`MAX_NUM_USER)
`define SEQ_LEN_WIDTH  $clog2(`MAX_CONTEXT_LENGTH_WITH_GQA+1)
`define EMBD_SIZE_WIDTH  $clog2(`MAX_EMBD_SIZE+1)
`define QKV_WEIGHT_COLS_PER_CORE_WIDTH  $clog2(`MAX_QKV_WEIGHT_COLS_PER_CORE + 1)
`define TOKEN_PER_CORE_WIDTH $clog2(`MAX_TOKEN_PER_CORE + 1)
`define HEAD_NUM_WIDTH  $clog2(`HEAD_NUM+1)

//SRAM DEFINES
//Calculate the DEPTH here
//https://docs.google.com/spreadsheets/d/1xzBwB_yHY48no7eCyaSvvRwQojUWLVjq/edit?gid=1117410533#gid=1117410533

// `define WMEM_DEPTH   (3072/2)
`define WMEM_DEPTH   ${wmem_depth} 
`define WMEM_NUM_PER_CORE 3 //one for qkvproj,one for ffn0, one for ffn1 each 1024 in depth

// `define KV_CACHE_DEPTH_SINGLE_USER  (256/2) //This is for one user, two user share one KV Cache, so one KV Cache depth is 512
`define KV_CACHE_DEPTH_SINGLE_USER  ${kv_cache_depth} 
`define KV_CACHE_DEPTH_SINGLE_USER_WITH_GQA (`KV_CACHE_DEPTH_SINGLE_USER*2)

// `define KV_CACHE_DEPTH_ALL_USER (`KV_CACHE_DEPTH_SINGLE_USER_WITH_GQA*`MAX_NUM_USER)

// `define KV_CACHE_PKT_NUM (`MAX_NUM_USER/2) //no kv cache pkt now

`define HEAD_SRAM_DEPTH (64/2)

`define GLOBAL_SRAM_DEPTH  (64/2)

// `define CMEM_ADDR_WIDTH (1 + $clog2(`WMEM_DEPTH)) //if $clog2(`WMEM_DEPTH) >=  $clog2(`MAC_MULT_NUM) +  $clog2(`KV_CACHE_DEPTH_SINGLE_USER_WITH_GQA)
`define CMEM_ADDR_WIDTH (1 + ($clog2(`MAC_MULT_NUM) +  $clog2(`KV_CACHE_DEPTH_SINGLE_USER_WITH_GQA))) //if $clog2(`WMEM_DEPTH) <= $clog2(`MAC_MULT_NUM) +  $clog2(KV_CACHE_DEPTH_SINGLE_USER_WITH_GQA)
                         //This bit determine weight of cache -BUCK
                         //1: cache, 0: wmem
                         //CMEM use same data width as GBUS                  

`define GBUS_ADDR_WIDTH   (2 + $clog2(`HEAD_CORE_NUM) + `CMEM_ADDR_WIDTH)
                        //2 for residual sram
                        //1 for the head sram
                        //0 for core

`define SIG_WIDTH 7
`define EXP_WIDTH 8


// typedef struct packed {
// logic       [`CDATA_ACCU_NUM_WIDTH-1:0]  cfg_acc_num;
// logic       [`CDATA_SCALE_WIDTH-1:0]     cfg_quant_scale;
// logic       [`CDATA_BIAS_WIDTH-1:0]      cfg_quant_bias;
// logic       [`CDATA_SHIFT_WIDTH-1:0]     cfg_quant_shift;
// }OP_CONFIG;

// typedef struct packed {
// logic       [`USER_ID_WIDTH-1:0]    user_id;
// logic       [`SEQ_LEN_WIDTH-2:0]    user_token_cnt; //this token's position in MAX_CONTEXT_LENGTH，(usr_cfg.user_token_cnt / `MAC_MULT_NUM)会和qkv weight per core相乘，注意延时
// logic                               user_kv_cache_not_full;
// // logic                               user_first_token_flag;
// }USER_CONFIG;

// typedef struct packed {
//     logic   pmu_cfg_bc1;
//     logic   pmu_cfg_bc2;
//     logic   pmu_cfg_en;
//     logic   deepsleep_en;
// }PMU_CONFIG;

// //实际上qkv_weight_cols_per_core和embd_size是等价的，max_context_length和token_per_core是等价的，实际传的时候，只需要各自的其中一个就可以了
// typedef struct packed {
// logic   [`SEQ_LEN_WIDTH-1:0]                     max_context_length; //(model_cfg.max_context_length / `MAC_MULT_NUM) * model_cfg.qkv_weight_cols_per_core
// logic   [`QKV_WEIGHT_COLS_PER_CORE_WIDTH-1:0]    qkv_weight_cols_per_core; //这会和embd_size做乘法，注意延时（/`MAC_MULT_NUM相当于右移，应该能减latency），然后不同控制逻辑里面乘法器能够综合时复用
// logic   [`TOKEN_PER_CORE_WIDTH-1:0]              token_per_core; // Max_Context_Length / head_core_num 
// logic   [`EMBD_SIZE_WIDTH-1:0]                   embd_size;
// logic                                            gqa_en;
// }MODEL_CONFIG;

// typedef struct packed {
//     //rms norm
//     logic   [`RECOMPUTE_SHIFT_WIDTH - 1:0]           rms_rc_shift;
//     logic   [`EMBD_SIZE_WIDTH-1:0]                   rms_K;
//     logic   [`SIG_WIDTH+`EXP_WIDTH : 0]              attn_rms_dequant_scale_square;
//     logic   [`SIG_WIDTH+`EXP_WIDTH : 0]              mlp_rms_dequant_scale_square;
//     //softmax
//     logic   [`RECOMPUTE_SHIFT_WIDTH - 1:0]           softmax_rc_shift; //这个必须和rms_rc_shift一样
//     logic   [`SIG_WIDTH+`EXP_WIDTH : 0]              softmax_input_dequant_scale;
//     logic   [`SIG_WIDTH+`EXP_WIDTH : 0]              softmax_exp_quant_scale;
// }RC_CONFIG;


// typedef struct packed {
//     OP_CONFIG                       Q_GEN_CFG;
//     OP_CONFIG                       K_GEN_CFG;
//     OP_CONFIG                       V_GEN_CFG;
//     OP_CONFIG                       ATT_QK_CFG;
//     OP_CONFIG                       ATT_PV_CFG;
//     OP_CONFIG                       PROJ_CFG;
//     OP_CONFIG                       FFN0_CFG;
//     OP_CONFIG                       FFN1_CFG;
//     OP_CONFIG                       ATTN_RESIDUAL_CFG;//这个比较特殊，其中的accu num用于scale a, scale 用于 scale b
//     OP_CONFIG                       MLP_RESIDUAL_CFG;//这个比较特殊，其中的accu num用于scale a, scale 用于 scale b
// }OP_CONFIG_PKT;

    //////////////////////////////////////////////////
    //                                              //
    //                GBUS DEFINE                   //
    //                                              //
    //////////////////////////////////////////////////
// parameter integer BUS_DATA_WIDTH = `GBUS_DATA_WIDTH;
// parameter integer BUS_CMEM_ADDR_WIDTH = `CMEM_ADDR_WIDTH; 
// parameter integer BUS_CORE_ADDR_WIDTH = $clog2(`HEAD_CORE_NUM);
// parameter integer HEAD_SRAM_BIAS_WIDTH = 2;

// typedef struct packed {
//     logic [HEAD_SRAM_BIAS_WIDTH-1:0]    hs_bias;   
//     logic [BUS_CORE_ADDR_WIDTH-1:0]     core_addr;
//     logic [BUS_CMEM_ADDR_WIDTH-1:0]     cmem_addr;
// }BUS_ADDR;

// typedef struct packed {
//     logic [BUS_DATA_WIDTH-1:0] bus_data;
//     BUS_ADDR bus_addr;
// }BUS_PACKET;


    /////////////////////////////////////////////////////
    //                                                 //
    //                CONTROL DEFINE                   //
    //                                                 //
    /////////////////////////////////////////////////////

// typedef enum{
//     IDLE_STATE,
//     Q_GEN_STATE,
//     K_GEN_STATE,
//     V_GEN_STATE,
//     ATT_QK_STATE,
//     ATT_PV_STATE,
//     PROJ_STATE,
//     FFN0_STATE,
//     FFN1_STATE
// } CONTROL_STATE;


    /////////////////////////////////////////////////////
    //                                                 //
    //                INTERFACE DEFINE                 //
    //                                                 //
    /////////////////////////////////////////////////////
//SPI and QSPI channel
`define INTERFACE_ADDR_WIDTH 22
`define INTERFACE_DATA_WIDTH 16

//control register initial channhel
`define CONTROL_REGISTERS_ADDR_WIDTH 6
`define CONTROL_REGISTERS_DATA_WIDTH 16
                                    //2MB*2          //4KB*2
`define CONTROL_REGISTERS_BASE_ADDR (22'h200000 + 22'h1000 + 22'h0) //22!

//instruction register channel
`define INSTRUCTION_REGISTERS_ADDR_WIDTH 2 
`define INSTRUCTION_REGISTERS_DATA_WIDTH 16
`define INSTRUCTION_REGISTERS_BASE_ADDR (22'h200000 + 22'h1000 + 22'h100)

//state register channel
`define STATE_REGISTERS_ADDR_WIDTH 2 
`define STATE_REGISTERS_DATA_WIDTH 16
`define STATE_REGISTERS_BASE_ADDR (22'h200000 + 22'h1000 + 22'h200)

//global mem channel
`define GLOBAL_MEM_ADDR_WIDTH 8
`define GLOBAL_MEM_DATA_WIDTH 16           //2KB*2
`define GLOBAL_MEM_BASE_ADDR (22'h200000 + 22'h800)

//residual mem channel
`define RESIDUAL_MEM_ADDR_WIDTH 8
`define RESIDUAL_MEM_DATA_WIDTH 16            //2KB*2+0.5KB
`define RESIDUAL_MEM_BASE_ADDR (22'h200000 + 22'h900)

//core mem channel
`define CORE_MEM_ADDR_WIDTH 14 

//head mem channel
`define HEAD_MEM_ADDR_WIDTH (18+1)

//array mem channel
`define ARRAY_MEM_ADDR_WIDTH (21+1)
`endif