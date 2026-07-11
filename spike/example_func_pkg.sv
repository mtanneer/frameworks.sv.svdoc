/**
 * @brief Utility functions for FIFO address math.
 */
package fifo_util_pkg;

    /**
     * @brief Compute the next write pointer, wrapping at DEPTH.
     * @param ptr Current pointer value.
     * @param depth FIFO depth.
     * @return Next pointer value.
     */
    function automatic int next_ptr(
        input int ptr,   ///< Current pointer value
        input int depth  ///< FIFO depth
    );
        next_ptr = (ptr + 1) % depth;
    endfunction

    /**
     * @brief Reset the FIFO state (task, no return value).
     */
    task automatic do_reset(
        output logic done  ///< Set when reset completes
    );
        done = 1'b1;
    endtask

endpackage
