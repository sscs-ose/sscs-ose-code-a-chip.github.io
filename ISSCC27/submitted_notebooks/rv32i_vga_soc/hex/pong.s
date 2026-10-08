# RV32I Ping Pong Game for Digilent Zybo Z7-10 VGA
#
# Hardware configuration:
# - Single-cycle RV32I Core @ 25 MHz
# - Framebuffer: 160x120 (4x hardware pixel replication to 640x480 @ 60Hz)
# - MMIO Display Control: 0x1000_0000 | Framebuffer Base: 0x5000_0000
# - Input Register: 0x1000_0010 ([3:0] = btn, [7:4] = sw)
#
# Register map:
# x1:  temp / btn mask     x2:  white pixel (0x00FFFFFF)
# x3:  base addresses      x4:  ball_x
# x5:  ball_y              x6:  ball_vel_x
# x7:  ball_vel_y          x8:  paddle_left_y
# x9:  paddle_right_y      x10: pixel write address
# x11: scratch / counter   x12: comparison limits
# x13: delay counter       x14: prev_ball_x
# x15: prev_ball_y         x16: prev_paddle_left_y
# x17: prev_paddle_right_y x18: mmio base
# x19: input state

.global _start
_start:
    # 1. Enable VGA Display (MMIO 0x1000_0000 <= 1)
    lui  x3, 0x10000
    addi x1, x0, 1
    sw   x1, 0(x3)

    # 2. Setup Base Pointers & Initial Variables
    lui  x3, 0x50000        # Framebuffer base: 0x5000_0000
    lui  x2, 0x00FFF
    ori  x2, x2, 0xFFF      # White color (0x00FFFFFF)

    # Ball initial state (center of 160x120 screen)
    addi x4, x0, 80         # ball_x = 80
    addi x5, x0, 60         # ball_y = 60
    addi x6, x0, 1          # ball_vel_x = +1
    addi x7, x0, 1          # ball_vel_y = +1

    # Paddle initial state
    addi x8, x0, 50         # paddle_left_y = 50
    addi x9, x0, 50         # paddle_right_y = 50

    # Shadow state for flicker-free erasing
    addi x14, x4, 0
    addi x15, x5, 0
    addi x16, x8, 0
    addi x17, x9, 0

game_loop:
    # 3. Erase Previous Frame Objects

    # 3a. Erase previous ball (2x2) at (x14, x15)
    slli x10, x15, 9        # prev_y * 512
    slli x11, x15, 7        # prev_y * 128
    add  x10, x10, x11      # prev_y * 640 (stride)
    slli x11, x14, 2        # prev_x * 4
    add  x10, x10, x11
    add  x10, x10, x3
    sw   x0, 0(x10)
    sw   x0, 4(x10)
    sw   x0, 640(x10)
    sw   x0, 644(x10)

    # 3b. Erase previous left paddle at X=6, Y=x16 (height 16)
    slli x10, x16, 9
    slli x11, x16, 7
    add  x10, x10, x11
    addi x10, x10, 24       # 6 * 4
    add  x10, x10, x3
    addi x11, x0, 16
erase_lpad:
    sw   x0, 0(x10)
    sw   x0, 4(x10)
    addi x10, x10, 640
    addi x11, x11, -1
    bne  x11, x0, erase_lpad

    # 3c. Erase previous right paddle at X=152, Y=x17 (height 16)
    slli x10, x17, 9
    slli x11, x17, 7
    add  x10, x10, x11
    addi x10, x10, 608      # 152 * 4
    add  x10, x10, x3
    addi x11, x0, 16
erase_rpad:
    sw   x0, 0(x10)
    sw   x0, 4(x10)
    addi x10, x10, 640
    addi x11, x11, -1
    bne  x11, x0, erase_rpad

    # 4. Update Ball Position and Collisions
    add  x4, x4, x6         # ball_x += vel_x
    add  x5, x5, x7         # ball_y += vel_y

    # Vertical wall collisions
    addi x12, x0, 3
    bge  x12, x5, bounce_y  # ball_y <= 3
    addi x12, x0, 115
    blt  x5, x12, check_pad_coll # ball_y < 115
bounce_y:
    sub  x7, x0, x7         # vel_y = -vel_y

check_pad_coll:
    # Left paddle collision threshold (X <= 8)
    addi x12, x0, 8
    bge  x12, x4, test_left_pad
    # Right paddle collision threshold (X >= 150)
    addi x12, x0, 150
    bge  x4, x12, test_right_pad
    jal  x0, read_inputs

test_left_pad:
    blt  x5, x8, check_left_goal
    addi x12, x8, 16
    bge  x5, x12, check_left_goal
    addi x6, x0, 1          # Bounce right
    jal  x0, read_inputs

check_left_goal:
    addi x12, x0, 2
    blt  x4, x12, reset_ball_right
    jal  x0, read_inputs

test_right_pad:
    blt  x5, x9, check_right_goal
    addi x12, x9, 16
    bge  x5, x12, check_right_goal
    addi x6, x0, -1         # Bounce left
    jal  x0, read_inputs

check_right_goal:
    addi x12, x0, 156
    bge  x4, x12, reset_ball_left
    jal  x0, read_inputs

reset_ball_right:
    addi x4, x0, 80
    addi x5, x0, 60
    addi x6, x0, 1
    jal  x0, read_inputs

reset_ball_left:
    addi x4, x0, 80
    addi x5, x0, 60
    addi x6, x0, -1

    # 5. Read Controls & Update Paddles
read_inputs:
    lui  x18, 0x10000
    lw   x19, 16(x18)       # Read MMIO 0x1000_0010 (btn & sw)

    # Left Paddle (BTN0 = UP, BTN1 = DOWN)
    andi x1, x19, 1
    beq  x1, x0, check_btn1
    addi x8, x8, -2
    addi x12, x0, 2
    bge  x8, x12, check_right_pad_ctrl
    addi x8, x0, 2
    jal  x0, check_right_pad_ctrl

check_btn1:
    andi x1, x19, 2
    beq  x1, x0, check_right_pad_ctrl
    addi x8, x8, 2
    addi x12, x0, 102
    blt  x8, x12, check_right_pad_ctrl
    addi x8, x0, 102

    # Right Paddle (BTN2 = UP, BTN3 = DOWN, or AI tracking if SW1=0)
check_right_pad_ctrl:
    andi x1, x19, 4
    beq  x1, x0, check_btn3
    addi x9, x9, -2
    addi x12, x0, 2
    bge  x9, x12, draw_frame
    addi x9, x0, 2
    jal  x0, draw_frame

check_btn3:
    andi x1, x19, 8
    beq  x1, x0, check_ai_right
    addi x9, x9, 2
    addi x12, x0, 102
    blt  x9, x12, draw_frame
    addi x9, x0, 102
    jal  x0, draw_frame

check_ai_right:
    andi x1, x19, 32        # SW1 (bit 5): 1 = Manual only, 0 = AI assist
    bne  x1, x0, draw_frame
    addi x12, x9, 8         # Center of right paddle
    bge  x12, x5, rpad_ai_up
    addi x12, x0, 102
    bge  x9, x12, draw_frame
    addi x9, x9, 1          # AI move down
    jal  x0, draw_frame
rpad_ai_up:
    blt  x5, x12, rpad_do_up
    jal  x0, draw_frame
rpad_do_up:
    addi x12, x0, 2
    bge  x12, x9, draw_frame
    addi x9, x9, -1         # AI move up

    # 6. Render Current Frame
draw_frame:
    # 6a. Draw left paddle at (X=6, Y=x8)
    slli x10, x8, 9
    slli x11, x8, 7
    add  x10, x10, x11
    addi x10, x10, 24
    add  x10, x10, x3
    addi x11, x0, 16
draw_lpad:
    sw   x2, 0(x10)
    sw   x2, 4(x10)
    addi x10, x10, 640
    addi x11, x11, -1
    bne  x11, x0, draw_lpad

    # 6b. Draw right paddle at (X=152, Y=x9)
    slli x10, x9, 9
    slli x11, x9, 7
    add  x10, x10, x11
    addi x10, x10, 608
    add  x10, x10, x3
    addi x11, x0, 16
draw_rpad:
    sw   x2, 0(x10)
    sw   x2, 4(x10)
    addi x10, x10, 640
    addi x11, x11, -1
    bne  x11, x0, draw_rpad

    # 6c. Draw ball at (x4, x5) (2x2)
    slli x10, x5, 9
    slli x11, x5, 7
    add  x10, x10, x11
    slli x11, x4, 2
    add  x10, x10, x11
    add  x10, x10, x3
    sw   x2, 0(x10)
    sw   x2, 4(x10)
    sw   x2, 640(x10)
    sw   x2, 644(x10)

    # 6d. Update shadow variables for next frame erase
    addi x14, x4, 0
    addi x15, x5, 0
    addi x16, x8, 0
    addi x17, x9, 0

    # 7. Frame Delay Loop
    lui  x13, 0x18
delay_loop:
    addi x13, x13, -1
    bne  x13, x0, delay_loop

    # 8. Loop for next frame
    jal  x0, game_loop
