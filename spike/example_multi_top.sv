import fifo_pkg::*;

/**
 * @brief FIFO top-level using shared package types.
 */
module fifo_top (
    input  logic       clk,   ///< Clock
    input  fifo_mode_e mode,  ///< Operating mode
    output fifo_status_t status  ///< Status bundle
);
endmodule
