W, H = 1024, 600

# Colors — white-only highlight theme, no blue
BLACK        = (0, 0, 0)
WHITE        = (255, 255, 255)
BG           = (10, 11, 14)
CARD_BG      = (18, 20, 26)
CARD_HOVER   = (28, 32, 42)
CARD_BORDER  = (35, 40, 55)
SUCCESS      = (200, 220, 200)
ERROR        = (255, 90, 90)
TEXT_PRIMARY = (240, 240, 248)
TEXT_MUTED   = (90, 95, 115)
TEXT_SUBTLE  = (45, 48, 62)

# White-scale accents replacing blue
ACCENT       = (200, 200, 210)
ACCENT_DIM   = (70, 72, 88)

# Layout
RADIUS       = 16
PADDING      = 40

# Consistent button sizing across all pages
BTN_W        = 56
BTN_H        = 48
BTN_MARGIN   = 64          # distance from screen edge
BTN_Y        = H - 72      # consistent vertical position

INPUT_H      = 52
BUTTON_H     = BTN_H       # alias

# Animation
LERP_SPEED   = 14.0

# Containers to pull after WiFi setup — extend freely
CONTAINERS_TO_PULL = [
    "koalby/zaraos-face:latest",
]

# Setup config paths
DATA_CONFIG_DIR   = "/data/config"
WIFI_CONFIG_PATH  = "/data/config/wifi.conf"
ROBOT_CONFIG_PATH = "/data/config/robot.conf"
WPA_CONF_PATH     = "/etc/wpa_supplicant.conf"
SETUP_DONE_FLAG   = "/data/.setup-done"
HOSTNAME_PATH     = "/etc/hostname"