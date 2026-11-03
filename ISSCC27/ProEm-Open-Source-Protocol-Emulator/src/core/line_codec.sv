// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: src/core/line_codec.sv
// Module: line_codec
// Type: RTL, core
// Hierarchy: tt_um_vertrex_star_proem > protocol_emulator > emulator_channel > line_codec
// Submodules: none
// Author: Paul Vincent Bezzina
// Language: SystemVerilog
// Description:
// =============================================================================

module line_codec (
	input logic clk,
	input logic rst_n,
	input logic [7:0] pins,
	input logic [15:0] line_config,
	input logic [31:0] clock_config,
	input logic [7:0] out_config,
	input logic listen,
	input logic line_free,
	input logic in_frame,
	input logic frame_mark,
	input logic halt,
	input logic tx_cancel,
	input logic tx_valid,
	input logic [3:0] tx_len,
	input logic [7:0] tx_data,

	output logic tx_ready,
	output logic tx_done,
	output logic [7:0] view,
	output logic tick,
	output logic end_tick,
	output logic code_error,
	output logic strict_tx,
	output logic tx_mismatch,
	output logic i2c_target,
	output logic i2c_start,
	output logic i2c_stop,
	output logic data_out,
	output logic data_oe,
	output logic pair_out,
	output logic pair_oe,
	output logic clock_out,
	output logic clock_oe,
	output logic select_out
);

localparam logic [1:0] SRC_SYNC = 2'd0;
localparam logic [1:0] SRC_ASYNC = 2'd1;
localparam logic [1:0] SRC_GENERATE = 2'd2;
localparam logic [1:0] SRC_RECOVER = 2'd3;

logic [2:0] code;
logic [2:0] pinA;
logic [2:0] pinB;
logic [3:0] stuffLen;
logic [1:0] source;
logic [1:0] edgeSel;
logic [2:0] clockPin;
logic [1:0] endSel;
logic [21:0] div;
logic [21:0] half;
logic [23:0] blankSum;
logic [21:0] blank;
logic [22:0] twoBits;
logic [1:0] drive;
logic inv;
logic boundary;
logic stuffAny;
logic clockIdle;
logic outIdle;
logic pairEnable;
logic eopEnable;
logic i2c;
logic selectHigh;
logic timed;
logic generating;
logic manchester;
logic nrzi;
logic pairCode;
logic thomas;
logic openDrain;
logic i2cTarget;

logic [21:0] rxCount;
logic [3:0] runCount;
logic [7:0] viewPins;
logic lineA;
logic rawA;
logic lineB;
logic clockIn;
logic prevA;
logic prevRaw;
logic prevClock;
logic aEdge;
logic clockRise;
logic clockFall;
logic syncTick;
logic se0;
logic se1;
logic locked;
logic lastSample;
logic runValue;
logic skipNext;
logic strobe;
logic bitValue;
logic dataValid;
logic stuffOn;
logic dropBit;
logic goodBit;
logic stuffBad;
logic txBegin;
logic runMatch;
logic [3:0] nextRun;
logic rxBit;
logic rxTick;
logic rxStrobe;
logic internal_code_error;

typedef enum logic [2:0] {
	T_IDLE,
	T_BIT,
	T_READ,
	T_START,
	T_REPEAT,
	T_STOP,
	T_EOP,
	T_WAIT
} txState;

txState state;

logic [21:0] txCount;
logic [22:0] eopLength;
logic [7:0] shiftData;
logic [7:0] dataAfter;
logic [7:0] nextData;
logic [3:0] shiftLeft;
logic [3:0] leftAfter;
logic [3:0] nextLen;
logic [3:0] txRun;
logic [3:0] txRunNew;
logic [1:0] step;
logic [1:0] dropCount;
logic nextValid;
logic sendBit;
logic nrziLevel;
logic holdLevel;
logic stuffing;
logic txRunValue;
logic phaseB;
logic packetActive;
logic i2cBusy;
logic endPending;
logic genTick;
logic clockHigh;
logic phaseAClock;
logic sampleLeading;
logic shiftEdge;
logic endOfBit;
logic dataBitEnded;
logic runMatchTx;
logic willStuff;
logic stuffValue;
logic entryDone;
logic continueNext;
logic nextBitValue;
logic halfDone;
logic bitLevel;
logic level;
logic se0Out;
logic dataPin;
logic clockLevel;
logic selectActive;
logic sending;
logic internal_tx_done;
logic checkPoint;
logic startWait;
logic idleHold;
logic [6:0] waitBits;
logic waitAligned;
logic idleLevel;
logic driveNow;

assign code = line_config[15:13];
assign inv = line_config[12];
assign boundary = line_config[11];
assign pinA = line_config[10:8];
assign stuffAny = line_config[7];
assign stuffLen = line_config[6:3];
assign pinB = line_config[2:0];
assign source = clock_config[31:30];
assign edgeSel = clock_config[29:28];
assign clockIdle = clock_config[27];
assign clockPin = clock_config[26:24];
assign endSel = clock_config[23:22];
assign div = {clock_config[21:16], clock_config[15:0]};
assign drive = out_config[7:6];
assign outIdle = out_config[5];
assign pairEnable = out_config[4];
assign eopEnable = out_config[3];
assign i2c = out_config[2];
assign selectHigh = out_config[1];

assign timed = (source == SRC_ASYNC) || (source == SRC_RECOVER);
assign generating = (source == SRC_GENERATE);
assign manchester = (code == 3'd3) || (code == 3'd4);
assign thomas = (code == 3'd4);
assign nrzi = (code == 3'd1) || (code == 3'd2);
assign pairCode = (code == 3'd2);
assign openDrain = (drive == 2'd2);
assign i2cTarget = i2c && (source == SRC_SYNC);
assign half = div >> 1;
assign blankSum = {2'd0, div} + {1'b0, div, 1'b0};
assign blank = blankSum[23:2];
assign twoBits = {div, 1'b0};

assign rawA = pins[pinA];
assign lineA = rawA ^ inv;
assign lineB = pins[pinB];
assign clockIn = pins[clockPin];
assign aEdge = lineA != prevA;
assign clockRise = clockIn && !prevClock;
assign clockFall = !clockIn && prevClock;
assign syncTick = (edgeSel == 2'd0 && clockRise) || (edgeSel == 2'd1 && clockFall) || (edgeSel == 2'd2 && (clockRise || clockFall));
assign se0 = pairCode && !rawA && !lineB;
assign se1 = pairCode && rawA && lineB;

assign strobe = timed && (manchester ? (aEdge && (locked ? (rxCount > blank) : !boundary)) : (rxCount == half));
assign bitValue = manchester ? (lineA ^ thomas) : (nrzi ? (lineA == lastSample) : lineA);
assign dataValid = strobe && !se0 && !se1;
assign stuffOn = stuffLen != 4'd0;
assign dropBit = dataValid && stuffOn && skipNext;
assign goodBit = dataValid && !dropBit;
assign stuffBad = dropBit && (stuffAny ? (bitValue == runValue) : bitValue);
assign runMatch = stuffAny ? (bitValue == runValue) : bitValue;
assign nextRun = runMatch ? runCount + 1'b1 : (stuffAny ? 4'd1 : 4'd0);
assign txBegin = (state == T_IDLE) && nextValid && (nextLen != 4'd0) && !startWait && !packetActive && !(i2c && generating && !i2cBusy);

always_ff @(posedge clk or negedge rst_n) begin
	if (!rst_n) begin
		prevA <= 1'b0;
		prevRaw <= 1'b1;
		prevClock <= 1'b0;
		rxCount <= '0;
		locked <= 1'b0;
		lastSample <= 1'b0;
		runCount <= '0;
		runValue <= 1'b0;
		skipNext <= 1'b0;
		rxBit <= 1'b0;
		rxTick <= 1'b0;
		rxStrobe <= 1'b0;
		internal_code_error <= 1'b0;
	end else begin
		prevA <= lineA;
		prevRaw <= rawA;
		prevClock <= clockIn;
		rxTick <= goodBit;
		rxStrobe <= strobe;
		internal_code_error <= stuffBad && !packetActive;
		if (!timed) begin
			rxCount <= '0;
			locked <= 1'b0;
		end else if (manchester) begin
			if (strobe) begin
				rxCount <= 22'd1;
				locked <= 1'b1;
			end else if (aEdge && !locked && boundary) begin
				rxCount <= half;
				locked <= 1'b1;
			end else begin
				if (rxCount != 22'h3FFFFF) begin
					rxCount <= rxCount + 1'b1;
				end
				if ({1'b0, rxCount} >= twoBits) begin
					locked <= 1'b0;
				end
			end
		end else if (aEdge) begin
			rxCount <= 22'd1;
		end else if (rxCount >= div - 1'b1) begin
			rxCount <= '0;
		end else begin
			rxCount <= rxCount + 1'b1;
		end
		if (strobe && !manchester) begin
			lastSample <= (se0 || se1) ? 1'b0 : lineA;
		end
		if (txBegin || (strobe && (se0 || se1))) begin
			runCount <= '0;
			runValue <= 1'b0;
			skipNext <= 1'b0;
		end else if (dropBit) begin
			skipNext <= 1'b0;
			runCount <= stuffAny ? 4'd1 : 4'd0;
			runValue <= bitValue;
		end else if (goodBit && stuffOn) begin
			runCount <= nextRun;
			runValue <= bitValue;
			skipNext <= (nextRun == stuffLen) && in_frame && (packetActive || line_free);
		end
		if (goodBit) begin
			rxBit <= bitValue;
		end
	end
end

always_comb begin
	viewPins = pins;
	if (timed) begin
		viewPins[pinA] = rxBit;
	end
end

assign phaseAClock = i2c ? 1'b0 : clockIdle;
assign sampleLeading = (edgeSel == 2'd2) || ((edgeSel == 2'd0) == !phaseAClock);
assign shiftEdge = (edgeSel == 2'd1) ? clockRise : clockFall;
assign clockHigh = !openDrain || clockIn;
assign halfDone = txCount >= half;
assign eopLength = twoBits;

always_comb begin
	if (generating) begin
		endOfBit = phaseB && clockHigh && (txCount == div - 1'b1);
	end else if (timed) begin
		endOfBit = (txCount == div - 1'b1);
	end else begin
		endOfBit = shiftEdge;
	end
end

assign dataBitEnded = !stuffing;
assign startWait = i2cTarget && !shiftEdge;
assign idleHold = packetActive && !(i2cTarget && openDrain);
assign idleLevel = idleHold ? holdLevel : (openDrain ? 1'b1 : outIdle);
assign runMatchTx = stuffAny ? (sendBit == txRunValue) : sendBit;
assign txRunNew = runMatchTx ? txRun + 1'b1 : (stuffAny ? 4'd1 : 4'd0);
assign willStuff = dataBitEnded && stuffOn && (txRunNew == stuffLen);
assign stuffValue = stuffAny ? !sendBit : 1'b0;
assign leftAfter = dataBitEnded ? shiftLeft - 1'b1 : shiftLeft;
assign dataAfter = dataBitEnded ? (shiftData >> 1) : shiftData;
assign entryDone = !willStuff && (leftAfter == 4'd0);
assign continueNext = entryDone && nextValid && (nextLen != 4'd0);
assign nextBitValue = willStuff ? stuffValue : (entryDone ? nextData[0] : dataAfter[0]);

always_ff @(posedge clk or negedge rst_n) begin
	if (!rst_n) begin
		state <= T_IDLE;
		txCount <= '0;
		step <= '0;
		dropCount <= '0;
		nextValid <= 1'b0;
		nextLen <= '0;
		nextData <= '0;
		shiftData <= '0;
		shiftLeft <= '0;
		sendBit <= 1'b0;
		nrziLevel <= 1'b0;
		holdLevel <= 1'b0;
		stuffing <= 1'b0;
		txRun <= '0;
		txRunValue <= 1'b0;
		phaseB <= 1'b0;
		packetActive <= 1'b0;
		i2cBusy <= 1'b0;
		endPending <= 1'b0;
		genTick <= 1'b0;
		internal_tx_done <= 1'b0;
		waitBits <= '0;
		waitAligned <= 1'b0;
	end else begin
		genTick <= 1'b0;
		internal_tx_done <= 1'b0;
		if (dropCount != 2'd0) begin
			dropCount <= dropCount - 1'b1;
			internal_tx_done <= 1'b1;
		end
		if (tx_valid && !nextValid && !endPending && !tx_cancel) begin
			nextValid <= 1'b1;
			nextLen <= tx_len;
			nextData <= tx_data;
		end
		if (frame_mark || halt) begin
			endPending <= 1'b1;
		end

		if (tx_cancel) begin
			dropCount <= dropCount - {1'b0, (dropCount != 2'd0)} + {1'b0, (state == T_BIT)} + {1'b0, nextValid};
			nextValid <= 1'b0;
			state <= T_IDLE;
			txCount <= '0;
			step <= '0;
			phaseB <= 1'b0;
			stuffing <= 1'b0;
			packetActive <= 1'b0;
			i2cBusy <= 1'b0;
		end else if (dropCount == 2'd0) begin
			unique case (state)
				T_IDLE: begin
					txCount <= '0;
					step <= '0;
					phaseB <= 1'b0;
					if (nextValid && nextLen == 4'd0) begin
						if (nextData[7] && timed && !manchester) begin
							waitBits <= nextData[6:0];
							waitAligned <= 1'b0;
							state <= T_WAIT;
						end else if (i2c && generating && i2cBusy) begin
							state <= T_REPEAT;
						end else begin
							nextValid <= 1'b0;
							internal_tx_done <= 1'b1;
						end
					end else if (nextValid && i2c && generating && !i2cBusy) begin
						state <= T_START;
					end else if (nextValid && !startWait) begin
						nextValid <= 1'b0;
						shiftData <= nextData;
						shiftLeft <= nextLen;
						sendBit <= nextData[0];
						stuffing <= 1'b0;
						if (!packetActive) begin
							txRun <= '0;
							txRunValue <= 1'b0;
							nrziLevel <= !nextData[0];
						end else begin
							nrziLevel <= nextData[0] ? nrziLevel : !nrziLevel;
						end
						packetActive <= 1'b1;
						state <= T_BIT;
					end else if (generating && listen && !endPending && (!i2c || i2cBusy)) begin
						state <= T_READ;
					end else if (endPending) begin
						endPending <= 1'b0;
						if (i2c && generating && i2cBusy) begin
							state <= T_STOP;
						end else if (packetActive && eopEnable) begin
							state <= T_EOP;
						end else begin
							packetActive <= 1'b0;
						end
					end
				end

				T_BIT: begin
					if (generating && !phaseB) begin
						if (txCount == div - 1'b1) begin
							txCount <= '0;
							phaseB <= 1'b1;
						end else begin
							txCount <= txCount + 1'b1;
						end
					end else if (generating && !clockHigh) begin
						txCount <= '0;
					end else if (endOfBit) begin
						txCount <= '0;
						phaseB <= 1'b0;
						if (generating && !sampleLeading) begin
							genTick <= 1'b1;
						end
						holdLevel <= level;
						if (willStuff) begin
							stuffing <= 1'b1;
						end else begin
							stuffing <= 1'b0;
						end
						if (stuffing) begin
							txRun <= stuffAny ? 4'd1 : 4'd0;
							txRunValue <= sendBit;
						end else begin
							txRun <= txRunNew;
							txRunValue <= sendBit;
						end
						if (continueNext) begin
							shiftData <= nextData;
							shiftLeft <= nextLen;
							nextValid <= 1'b0;
						end else begin
							shiftData <= dataAfter;
							shiftLeft <= leftAfter;
						end
						if (entryDone) begin
							internal_tx_done <= 1'b1;
						end
						if (!entryDone || continueNext) begin
							sendBit <= nextBitValue;
							nrziLevel <= nextBitValue ? nrziLevel : !nrziLevel;
						end else begin
							state <= T_IDLE;
						end
					end else begin
						if (generating && phaseB && txCount == '0 && sampleLeading) begin
							genTick <= 1'b1;
						end
						txCount <= txCount + 1'b1;
					end
				end

				T_READ: begin
					if (!phaseB) begin
						if (txCount == div - 1'b1) begin
							txCount <= '0;
							phaseB <= 1'b1;
						end else begin
							txCount <= txCount + 1'b1;
						end
					end else if (!clockHigh) begin
						txCount <= '0;
					end else if (txCount == div - 1'b1) begin
						txCount <= '0;
						phaseB <= 1'b0;
						if (!sampleLeading) begin
							genTick <= 1'b1;
						end
						state <= T_IDLE;
					end else begin
						if (txCount == '0 && sampleLeading) begin
							genTick <= 1'b1;
						end
						txCount <= txCount + 1'b1;
					end
				end

				T_START: begin
					if (txCount == div - 1'b1) begin
						txCount <= '0;
						if (step == 2'd1) begin
							step <= '0;
							i2cBusy <= 1'b1;
							state <= T_IDLE;
						end else begin
							step <= step + 1'b1;
						end
					end else begin
						txCount <= txCount + 1'b1;
					end
				end

				T_REPEAT: begin
					if (step == 2'd1 && !clockHigh) begin
						txCount <= '0;
					end else if (txCount == div - 1'b1) begin
						txCount <= '0;
						if (step == 2'd3) begin
							step <= '0;
							nextValid <= 1'b0;
							internal_tx_done <= 1'b1;
							state <= T_IDLE;
						end else begin
							step <= step + 1'b1;
						end
					end else begin
						txCount <= txCount + 1'b1;
					end
				end

				T_STOP: begin
					if (step == 2'd1 && !clockHigh) begin
						txCount <= '0;
					end else if (txCount == div - 1'b1) begin
						txCount <= '0;
						if (step == 2'd2) begin
							step <= '0;
							i2cBusy <= 1'b0;
							packetActive <= 1'b0;
							state <= T_IDLE;
						end else begin
							step <= step + 1'b1;
						end
					end else begin
						txCount <= txCount + 1'b1;
					end
				end

				T_EOP: begin
					if (step == 2'd0 && {1'b0, txCount} >= eopLength - 1'b1) begin
						txCount <= '0;
						if (pairCode) begin
							step <= 2'd1;
						end else begin
							packetActive <= 1'b0;
							state <= T_IDLE;
						end
					end else if (step == 2'd1 && txCount == div - 1'b1) begin
						txCount <= '0;
						step <= '0;
						nrziLevel <= 1'b0;
						packetActive <= 1'b0;
						state <= T_IDLE;
					end else begin
						txCount <= txCount + 1'b1;
					end
				end

				T_WAIT: begin
					if (!waitAligned) begin
						txCount <= '0;
						if (rxCount >= div - 1'b1) begin
							waitAligned <= 1'b1;
							if (skipNext) begin
								waitBits <= waitBits + 1'b1;
							end
						end
					end else if (waitBits == 7'd0) begin
						nextValid <= 1'b0;
						internal_tx_done <= 1'b1;
						waitAligned <= 1'b0;
						state <= T_IDLE;
					end else if (txCount == div - 1'b1) begin
						txCount <= '0;
						waitBits <= waitBits - 1'b1;
					end else begin
						txCount <= txCount + 1'b1;
					end
				end

				default: begin
					state <= T_IDLE;
				end
			endcase
		end
	end
end

always_comb begin
	if (timed) begin
		checkPoint = (txCount == (manchester ? (half >> 1) : half));
	end else if (generating) begin
		checkPoint = phaseB && clockHigh && (txCount == half);
	end else begin
		checkPoint = syncTick;
	end
end

assign bitLevel = manchester ? ((timed && !halfDone) ? (!sendBit ^ thomas) : (sendBit ^ thomas)) : (nrzi ? nrziLevel : sendBit);

always_comb begin
	level = 1'b1;
	clockLevel = clockIdle;
	case (state)
		T_IDLE, T_WAIT: begin
			level = idleLevel;
			clockLevel = i2c ? !i2cBusy : clockIdle;
		end
		T_BIT: begin
			level = (generating && !i2c && !sampleLeading && !phaseB) ? holdLevel : bitLevel;
			clockLevel = phaseB ? !phaseAClock : phaseAClock;
		end
		T_READ: begin
			level = openDrain ? 1'b1 : outIdle;
			clockLevel = phaseB ? !phaseAClock : phaseAClock;
		end
		T_START: begin
			level = 1'b0;
			clockLevel = (step == 2'd0);
		end
		T_REPEAT: begin
			level = (step < 2'd2);
			clockLevel = (step == 2'd1) || (step == 2'd2);
		end
		T_STOP: begin
			level = (step == 2'd2);
			clockLevel = (step != 2'd0);
		end
		T_EOP: begin
			level = pairCode ? 1'b0 : 1'b1;
			clockLevel = clockIdle;
		end
		default: begin
			level = 1'b1;
			clockLevel = clockIdle;
		end
	endcase
end

assign se0Out = (state == T_EOP) && (step == 2'd0) && pairCode;
assign dataPin = se0Out ? 1'b0 : (level ^ inv);
assign sending = ((state != T_IDLE) && (state != T_WAIT)) || packetActive;
assign selectActive = in_frame || sending || nextValid || !line_free;

assign tx_ready = !nextValid && !endPending && !tx_cancel;
assign tx_done = internal_tx_done;
assign view = viewPins;
assign tick = timed ? rxTick : (generating ? genTick : syncTick);
assign end_tick = (endSel == 2'd1) ? 1'b1 : ((endSel == 2'd2) ? (timed ? rxStrobe : tick) : tick);
assign code_error = internal_code_error;
assign strict_tx = !generating;
assign tx_mismatch = (state == T_BIT) && checkPoint && (rawA != dataPin);
assign i2c_target = i2cTarget;
assign i2c_start = i2cTarget && prevRaw && !rawA && clockIn && prevClock;
assign i2c_stop = i2cTarget && !prevRaw && rawA && clockIn && prevClock;
assign data_out = openDrain ? 1'b0 : dataPin;
assign driveNow = sending && (state != T_READ) && !(generating && (state == T_IDLE));
assign data_oe = openDrain ? !dataPin : ((drive == 2'd3) || (drive == 2'd1 && driveNow));
assign pair_out = se0Out ? 1'b0 : !(level ^ inv);
assign pair_oe = pairEnable && ((drive == 2'd3) || (drive == 2'd1 && driveNow));
assign clock_out = openDrain ? 1'b0 : clockLevel;
assign clock_oe = generating && (drive != 2'd0) && (openDrain ? !clockLevel : 1'b1);
assign select_out = selectHigh ? selectActive : !selectActive;

endmodule
