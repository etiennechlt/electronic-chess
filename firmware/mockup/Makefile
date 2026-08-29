# Mockup firmware for NUCLEO-G474RE, bare CMSIS, no HAL.
# Build: make            (produces build/mockup.elf/.bin)
# Pins:  make pins       (regenerate src/board_pins.h from config/board.yaml)

CROSS   ?= arm-none-eabi-
CC      := $(CROSS)gcc
OBJCOPY := $(CROSS)objcopy
SIZE    := $(CROSS)size

BUILD   := build
TARGET  := $(BUILD)/mockup

SRCS := src/startup.c src/system.c src/main.c src/clock.c src/uart.c \
        src/adc.c src/comp.c src/fft.c src/measure.c src/calib.c src/cli.c
OBJS := $(SRCS:src/%.c=$(BUILD)/%.o)

CFLAGS := -mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard \
          -O2 -g -Wall -Wextra -Wno-unused-parameter \
          -ffunction-sections -fdata-sections -fno-common \
          -DSTM32G474xx -Ivendor -Isrc
LDFLAGS := -mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard \
           -T ld/stm32g474re.ld -nostartfiles --specs=nano.specs \
           --specs=nosys.specs -Wl,--gc-sections -Wl,-Map=$(TARGET).map -lm

all: $(TARGET).bin
	$(SIZE) $(TARGET).elf

$(BUILD)/%.o: src/%.c
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -c $< -o $@

$(TARGET).elf: $(OBJS)
	$(CC) $(OBJS) $(LDFLAGS) -o $@

$(TARGET).bin: $(TARGET).elf
	$(OBJCOPY) -O binary $< $@

pins:
	python3 scripts/gen_pins.py ../../config/board.yaml src/board_pins.h

flash: $(TARGET).bin
	@echo "Copy $(TARGET).bin to the NUCLEO mass-storage drive, or:"
	@echo "  st-flash write $(TARGET).bin 0x8000000"

clean:
	rm -rf $(BUILD)

.PHONY: all pins flash clean
