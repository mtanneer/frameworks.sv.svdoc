# Module: `fifo`

@brief A simple synchronous FIFO.

Buffers data words between write and read clock domains that share a
single clock (synchronous FIFO — no CDC handling).

## Parameters

| Name | Type | Default | Description |
|---|---|---|---|
| `DEPTH` | `int` | `16` | Number of entries in the FIFO |
| `WIDTH` | `int` | `8` | Bit width of each data word |

## Ports

| Name | Direction | Type | Description |
|---|---|---|---|
| `clk` | input | `logic` | Clock |
| `rst_n` | input | `logic` | Active-low async reset |
| `wr_en` | input | `logic` | Write enable |
| `wr_data` | input | `logic [WIDTH-1:0]` | Data to write |
| `full` | output | `logic` | FIFO full flag |
| `rd_en` | input | `logic` | Read enable |
| `rd_data` | output | `logic [WIDTH-1:0]` | Data read out |
| `empty` | output | `logic` | FIFO empty flag |

