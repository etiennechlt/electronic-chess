# Plateau firmware for the brain board (STM32G474RE), bare CMSIS, no HAL.
# Build: make            (produces build/board.elf/.bin)
#        make NUCLEO=1   (bench variant: Nucleo-G474RE, one reduced 2x2
#                         quadrant, console on the ST-Link port; produces
#                         build/nucleo/board-nucleo.elf/.bin, note 19)
#        make NUCLEO=1 NUCLEO_FULL=1
#                        (same bench shield driving one full 4x4 quadrant;
#                         produces build/nucleo-full/board-nucleo-full.elf/.bin)
# Pins:  make pins       (regenerate src/board_pins.h from config/board.yaml)

CROSS   ?= arm-none-eabi-
CC      := $(CROSS)gcc
OBJCOPY := $(CROSS)objcopy
SIZE    := $(CROSS)size

NUCLEO  ?= 0
NUCLEO_FULL ?= 0
ifeq ($(NUCLEO)$(NUCLEO_FULL),11)
BUILD   := build/nucleo-full
TARGET  := $(BUILD)/board-nucleo-full
else ifeq ($(NUCLEO),1)
BUILD   := build/nucleo
TARGET  := $(BUILD)/board-nucleo
else
BUILD   := build
TARGET  := $(BUILD)/board
endif

SRCS := src/startup.c src/system.c src/main.c src/clock.c src/uart.c \
        src/adc.c src/comp.c src/fft.c src/measure.c src/calib.c src/cli.c src/led.c
OBJS := $(SRCS:src/%.c=$(BUILD)/%.o)

CFLAGS := -mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard \
          -O2 -g -Wall -Wextra -Wno-unused-parameter \
          -ffunction-sections -fdata-sections -fno-common \
          -DSTM32G474xx -DNUCLEO=$(NUCLEO) -DNUCLEO_FULL=$(NUCLEO_FULL) -Ivendor -Isrc
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
	PYTHONPATH=../../tools python3 scripts/gen_pins.py ../../config/board.yaml src/board_pins.h

flash: $(TARGET).bin
ifeq ($(NUCLEO),1)
	@echo "Copy onto the NUCLEO mass-storage drive, or with the on-board ST-Link:"
else
	@echo "Flash through the SWD header with an ST-Link:"
endif
	@echo "  st-flash write $(TARGET).bin 0x8000000"

clean:
	rm -rf $(BUILD)

.PHONY: all pins flash clean
