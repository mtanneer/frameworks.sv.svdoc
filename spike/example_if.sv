/**
 * @brief Simple request/ack handshake interface.
 */
interface handshake_if #(
    parameter int WIDTH = 8   ///< Data bus width
) (
    input logic clk   ///< Shared clock
);
    logic              valid; ///< Request valid
    logic              ready; ///< Request ready
    logic [WIDTH-1:0]  data;  ///< Payload data

    /**
     * @brief Producer-side view of the handshake.
     */
    modport producer (
        output valid,  ///< Drive valid
        input  ready,   ///< Sample ready
        output data    ///< Drive data
    );

    /**
     * @brief Consumer-side view of the handshake.
     */
    modport consumer (
        input  valid,  ///< Sample valid
        output ready,  ///< Drive ready
        input  data    ///< Sample data
    );
endinterface
