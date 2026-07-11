/**
 * @brief A simple synchronous FIFO.
 *
 * Buffers data words between write and read clock domains that share a
 * single clock (synchronous FIFO — no CDC handling).
 */
module fifo #(
    parameter int DEPTH = 16,  ///< Number of entries in the FIFO
    parameter int WIDTH = 8    ///< Bit width of each data word
) (
    input  logic             clk,   ///< Clock
    input  logic             rst_n, ///< Active-low async reset
    input  logic              wr_en, ///< Write enable
    input  logic [WIDTH-1:0]  wr_data, ///< Data to write
    output logic              full,  ///< FIFO full flag
    input  logic              rd_en, ///< Read enable
    output logic [WIDTH-1:0]  rd_data, ///< Data read out
    output logic              empty  ///< FIFO empty flag
);

endmodule
