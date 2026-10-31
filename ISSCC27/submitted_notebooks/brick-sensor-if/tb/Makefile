# Makefile for cocotb simulation of brick_sensor_if
SIM ?= icarus
TOPLEVEL_LANG ?= verilog

VERILOG_SOURCES += $(PWD)/../rtl/spi_master.v
VERILOG_SOURCES += $(PWD)/../rtl/can_framer.v
VERILOG_SOURCES += $(PWD)/../rtl/brick_sensor_if.v
VERILOG_SOURCES += $(PWD)/tb_brick_sensor_if.v

TOPLEVEL = tb_brick_sensor_if
MODULE = test_sensor_if,test_sensor_if_ext
COMPILE_ARGS += -g2012

include $(shell cocotb-config --makefiles)/Makefile.sim
