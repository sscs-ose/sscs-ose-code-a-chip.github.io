module topLevelControl (
    input logic clk,
    input logic nRST,
    input logic [7:0] readA,
    input logic [7:0] readB,
    output logic [4:0] PERead,
    output logic [4:0] PEStart,
    output logic [2:0] filtRead
);

typedef enum logic [1:0] {
    idle,
    loadInit,
    loadSingle,
    reload
} state_t;

state_t state, nextState;

logic [4:0] PEReadNaive;

logic [2:0] countPE, nextCountPE;
logic [4:0] countRow, nextCountRow;
logic [4:0] countTile, nextCountTile;

logic [4:0] rowLen, nextRowLen;
logic [4:0] colTiles, nextColTiles;

always_ff @(posedge clk, negedge nRST) begin
    if(nRST == '0) begin
        state <= idle;
        countPE <= '0;
        countRow <= '0;
        countTile <= '0;
        rowLen <= '0;
        colTiles <= '0;
    end
    else begin
        state <= nextState;
        countPE <= nextCountPE;
        countRow <= nextCountRow;
        countTile <= nextCountTile;
        rowLen <= nextRowLen;
        colTiles <= nextColTiles;
    end
end

always_comb begin
    nextState = state;
    nextCountPE = countPE;
    nextCountRow = countRow;
    nextCountTile = countTile;

    nextRowLen = rowLen;
    nextColTiles = colTiles;

    PEReadNaive = '0;

    PERead = '0;
    PEStart = '0;
    filtRead = '0;

    case(countPE)
        3'd1: PEReadNaive[0] = 1'b1;
        3'd2: PEReadNaive[1] = 1'b1;
        3'd3: PEReadNaive[2] = 1'b1;
        3'd4: PEReadNaive[3] = 1'b1;
        3'd5: PEReadNaive[4] = 1'b1;
        default:PEReadNaive = '0;
    endcase

    case(state)
        idle: begin
            nextCountPE = '0;
            nextCountRow = '0;
            nextCountTile = '0;
            if(readA[7]) begin
                nextRowLen = readA[4:0];
                nextColTiles = readB[4:0];
                nextCountPE = 3'd1;
                nextState = loadInit;
            end
        end
        loadInit: begin
            PERead = {PEReadNaive[3], PEReadNaive[3:0]};
            filtRead = PEReadNaive[2:0];
            nextCountPE = countPE + 3'd1;
            if(countPE == 3'd4) begin
                nextCountPE = 3'd1;
                nextCountRow = countRow + 5'd1;
            end
            if(countRow == 5'd2) begin
                PEStart = PEReadNaive;
            end
            if(countRow == 5'd3) begin
                nextCountPE = 3'd1;
                PEStart[4] = 1'b1;
                filtRead = '0;
                PERead = '0;
                nextState = loadSingle;
            end
        end
        loadSingle: begin
            PEStart = PEReadNaive;
            PERead = PEReadNaive;
            nextCountPE = countPE + 3'd1;
            if(countPE == 3'd5) begin
                nextCountPE = 3'd1;
                nextCountRow = countRow + 5'd1;
                if(nextCountRow == rowLen) begin
                    nextState = reload;
                    nextCountTile = countTile + 5'd1;
                    nextCountRow = '0;
                end
            end
        end
        reload: begin
            PERead = {PEReadNaive[3], PEReadNaive[3:0]};
            nextCountPE = countPE + 3'd1;
            if(countPE == 3'd4) begin
                nextCountPE = 3'd1;
                nextCountRow = countRow + 5'd1;
            end
            if(countRow == 5'd2) begin
                    PEStart = PEReadNaive;
            end
            if(countRow == 5'd3) begin
                    nextCountPE = 3'd1;
                    PEStart[4] = 1'b1;
                    filtRead = '0;
                    PERead = '0;
                    nextState = loadSingle;
            end
            if(countTile == colTiles) begin
                nextState = idle;
                PERead = '0;
            end
        end
    endcase
end
    
endmodule