/**
 * @brief Shared types for the FIFO subsystem.
 */
package fifo_pkg;

    /**
     * @brief FIFO operating mode.
     */
    typedef enum logic [1:0] {
        MODE_NORMAL = 0, ///< Standard FIFO behavior
        MODE_BYPASS = 1, ///< Bypass buffering entirely
        MODE_FLUSH  = 2  ///< Drain and clear on next cycle
    } fifo_mode_e;

    /**
     * @brief FIFO status bundle.
     */
    typedef struct packed {
        logic full;   ///< FIFO full flag
        logic empty;  ///< FIFO empty flag
        logic [7:0] count; ///< Current occupancy
    } fifo_status_t;

    typedef logic [15:0] fifo_word_t; ///< Single FIFO data word

endpackage
