idf_component_register(SRCS "main.c" "chessclock.c" "ui.c" INCLUDE_DIRS "."
                       REQUIRES common driver esp_timer esp_lcd)
