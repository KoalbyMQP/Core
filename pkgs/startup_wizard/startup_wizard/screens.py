import pygame
import math
import threading
from startup_wizard.components import (lerp, lerp_color, draw_rounded_rect,
                        Button, TextInput, NetworkCard, ProgressBar,
                        StatusDot, OSKeyboard,
                        draw_title, draw_subtitle, draw_label)
from startup_wizard.constants import *


# ── Shared face drawing ───────────────────────────────────────────────────────

def _oval_pts(cx, cy, rx, ry, angle_deg, n=60):
    a = math.radians(angle_deg)
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x = rx * math.cos(t)
        y = ry * math.sin(t)
        pts.append((x * math.cos(a) - y * math.sin(a) + cx,
                    x * math.sin(a) + y * math.cos(a) + cy))
    return pts


def draw_face_small(surf, cx, cy, scale=0.55, blink_t=0.0):
    blink = max(0.0, math.sin(blink_t) ** 12)
    ry = int(170 * scale * (1.0 - blink * 0.95))
    rx = int(118 * scale)
    left  = _oval_pts(cx - int(270 * scale), cy - int(45 * scale), rx, ry, -20)
    right = _oval_pts(cx + int(270 * scale), cy - int(45 * scale), rx, ry,  20)
    pygame.draw.polygon(surf, WHITE, left)
    pygame.draw.polygon(surf, WHITE, right)
    pygame.draw.line(surf, WHITE,
                     (cx - int(110 * scale), cy + int(205 * scale)),
                     (cx + int(110 * scale), cy + int(205 * scale)),
                     max(2, int(7 * scale)))


def _nav_buttons(back_label="←", next_label="→", next_style="primary"):
    """Return (btn_back, btn_next) at consistent screen positions."""
    back = Button(
        (BTN_MARGIN, BTN_Y, BTN_W, BTN_H),
        back_label, style="ghost"
    )
    nxt = Button(
        (W - BTN_MARGIN - BTN_W, BTN_Y, BTN_W, BTN_H),
        next_label, style=next_style
    )
    return back, nxt


# ── Welcome ───────────────────────────────────────────────────────────────────

class WelcomeScreen:
    def __init__(self):
        bw, bh = BTN_W * 2, BTN_H
        self._btn_rect = pygame.Rect(W // 2 - bw // 2, BTN_Y, bw, bh)
        self._hover_t  = 0.0
        self._press_t  = 0.0
        self._t        = 0.0
        self._blink_t  = 0.0
        self._entry_t  = 0.0

    def update(self, dt, events, mouse_pos, mouse_down):
        self._t       += dt
        self._entry_t  = min(1.0, self._entry_t + dt * 1.2)
        self._blink_t  = (self._t % 4.0) / 4.0 * math.pi * 2

        hovered = self._btn_rect.collidepoint(mouse_pos)
        self._hover_t = lerp(self._hover_t, 1.0 if hovered else 0.0, dt * LERP_SPEED)
        self._press_t = lerp(self._press_t,
                             1.0 if (hovered and mouse_down) else 0.0, dt * 30)

        for e in events:
            if (e.type == pygame.MOUSEBUTTONUP and e.button == 1
                    and self._btn_rect.collidepoint(e.pos)):
                return "name"
        return None

    def draw(self, surf):
        alpha = min(255, int(255 * self._entry_t))

        face_surf = pygame.Surface((W, H), pygame.SRCALPHA)
        draw_face_small(face_surf, W // 2, H // 2 - 30, scale=0.52, blink_t=self._blink_t)
        face_surf.set_alpha(alpha)
        surf.blit(face_surf, (0, 0))

        r      = self._btn_rect
        scale  = lerp(1.0, 0.96, self._press_t)
        r_draw = r.inflate(int(r.w * (scale - 1)), int(r.h * (scale - 1)))
        r_draw.center = r.center

        border_col = lerp_color((80, 85, 105), WHITE, self._hover_t)
        btn_surf = pygame.Surface((r_draw.w, r_draw.h), pygame.SRCALPHA)
        pygame.draw.rect(btn_surf, (0, 0, 0, 0),
                         (0, 0, r_draw.w, r_draw.h), border_radius=RADIUS)
        pygame.draw.rect(btn_surf, (*border_col, int(180 + 75 * self._hover_t)),
                         (0, 0, r_draw.w, r_draw.h), 1, border_radius=RADIUS)
        btn_surf.set_alpha(alpha)
        surf.blit(btn_surf, (r_draw.x, r_draw.y))

        font = pygame.font.SysFont("DejaVuSans,Arial", 14, bold=True)
        lbl  = font.render("Setup", True, lerp_color(TEXT_MUTED, WHITE, self._hover_t))
        lbl_s = pygame.Surface(lbl.get_size(), pygame.SRCALPHA)
        lbl_s.blit(lbl, (0, 0))
        lbl_s.set_alpha(alpha)
        surf.blit(lbl_s, lbl.get_rect(center=r_draw.center))


# ── Robot Name ────────────────────────────────────────────────────────────────

class NameScreen:
    def __init__(self):
        iw = 560
        self.inp = TextInput(
            (W // 2 - iw // 2, 110, iw, INPUT_H),
            placeholder="e.g.  Atlas"
        )
        self.inp.focused = True
        self.osk = OSKeyboard(y_start=195)
        self.osk.target = self.inp
        self.btn_back, self.btn_next = _nav_buttons()
        self._error = ""

    def update(self, dt, events, mouse_pos, mouse_down):
        self.inp.update(dt)
        self.osk.update(dt, mouse_pos, mouse_down)
        self.btn_back.update(dt, mouse_pos, mouse_down)
        self.btn_next.update(dt, mouse_pos, mouse_down)

        for e in events:
            self.osk.handle_event(e)
            if self.btn_back.is_clicked(e):
                return "welcome"
            if self.btn_next.is_clicked(e):
                name = self.inp.text.strip()
                if not name:
                    self._error = "Please enter a name"
                elif len(name) > 32:
                    self._error = "Name too long (max 32 chars)"
                else:
                    return ("wifi_scan", {"robot_name": name})
        return None

    def draw(self, surf):
        draw_title(surf, "Name your robot", 46)
        draw_subtitle(surf, "This will identify it on the network", 84)
        self.inp.draw(surf)
        self.osk.draw(surf)
        self.btn_back.draw(surf)
        self.btn_next.draw(surf)
        if self._error:
            draw_label(surf, self._error, (W // 2 - 80, 166), color=ERROR)


# ── WiFi Scan ─────────────────────────────────────────────────────────────────

class WifiScanScreen:
    def __init__(self, robot_name):
        self.robot_name = robot_name
        self.networks   = []
        self.cards      = []
        self._scanning  = True
        self._scan_t    = 0.0

        self.btn_back   = Button((BTN_MARGIN, BTN_Y, BTN_W, BTN_H), "←", style="ghost")
        self.btn_rescan = Button((W - BTN_MARGIN - BTN_W, BTN_Y, BTN_W, BTN_H), "↺", style="ghost")

        self._thread = threading.Thread(target=self._scan, daemon=True)
        self._thread.start()

    def _scan(self):
        import system
        self.networks = system.scan_networks()
        self._rebuild_cards()
        self._scanning = False

    def _rebuild_cards(self):
        self.cards = []
        card_h, card_gap = 56, 8
        list_y, list_x = 130, W // 2 - 340
        for i, (ssid, sig) in enumerate(self.networks[:6]):
            r = pygame.Rect(list_x, list_y + i * (card_h + card_gap), 680, card_h)
            self.cards.append(NetworkCard(r, ssid, sig))

    def update(self, dt, events, mouse_pos, mouse_down):
        self._scan_t += dt
        self.btn_back.update(dt, mouse_pos, mouse_down)
        self.btn_rescan.update(dt, mouse_pos, mouse_down)
        for c in self.cards:
            c.update(dt, mouse_pos)

        for e in events:
            if self.btn_back.is_clicked(e):
                return "name"
            if self.btn_rescan.is_clicked(e) and not self._scanning:
                self._scanning = True
                self.networks  = []
                self.cards     = []
                self._thread   = threading.Thread(target=self._scan, daemon=True)
                self._thread.start()
            for card in self.cards:
                if card.is_clicked(e):
                    return ("wifi_password", {
                        "robot_name": self.robot_name,
                        "ssid": card.ssid
                    })
        return None

    def draw(self, surf):
        draw_title(surf, "Select Network", 40)
        draw_subtitle(surf, "Choose your WiFi network", 78)

        if self._scanning:
            dots = "." * (int(self._scan_t * 2) % 4)
            draw_subtitle(surf, f"Scanning{dots}", H // 2 - 10, color=TEXT_MUTED)
            cx, cy = W // 2, H // 2 + 30
            for i in range(8):
                a  = 2 * math.pi * i / 8 + self._scan_t * 3
                x  = cx + int(18 * math.cos(a))
                y2 = cy + int(18 * math.sin(a))
                col = lerp_color(TEXT_SUBTLE, ACCENT, i / 8)
                pygame.draw.circle(surf, col, (x, y2), 3)
        elif not self.networks:
            draw_subtitle(surf, "No networks found", H // 2, color=TEXT_MUTED)
        else:
            for card in self.cards:
                card.draw(surf)

        self.btn_back.draw(surf)
        self.btn_rescan.draw(surf)


# ── WiFi Password ─────────────────────────────────────────────────────────────

class WifiPasswordScreen:
    def __init__(self, robot_name, ssid):
        self.robot_name = robot_name
        self.ssid       = ssid

        iw = 560
        self.inp = TextInput(
            (W // 2 - iw // 2, 110, iw, INPUT_H),
            placeholder="Password",
            secret=True
        )
        self.inp.focused = True
        self.osk = OSKeyboard(y_start=195)
        self.osk.target = self.inp
        self.btn_back, self.btn_next = _nav_buttons(next_label="→")
        self._error = ""

    def update(self, dt, events, mouse_pos, mouse_down):
        self.inp.update(dt)
        self.osk.update(dt, mouse_pos, mouse_down)
        self.btn_back.update(dt, mouse_pos, mouse_down)
        self.btn_next.update(dt, mouse_pos, mouse_down)

        for e in events:
            self.osk.handle_event(e)
            if self.btn_back.is_clicked(e):
                return ("wifi_scan", {"robot_name": self.robot_name})
            if self.btn_next.is_clicked(e):
                pw = self.inp.text
                if len(pw) < 8:
                    self._error = "Password must be at least 8 characters"
                else:
                    return ("connecting", {
                        "robot_name": self.robot_name,
                        "ssid": self.ssid,
                        "password": pw
                    })
        return None

    def draw(self, surf):
        draw_title(surf, f"Connect to  {self.ssid}", 46)
        draw_subtitle(surf, "Enter the WiFi password", 84)
        self.inp.draw(surf)
        self.osk.draw(surf)
        self.btn_back.draw(surf)
        self.btn_next.draw(surf)
        if self._error:
            draw_label(surf, self._error, (W // 2 - 130, 166), color=ERROR)


# ── Connecting ────────────────────────────────────────────────────────────────

class ConnectingScreen:
    def __init__(self, robot_name, ssid, password):
        self.robot_name = robot_name
        self.ssid       = ssid
        self.password   = password
        self._status    = "Connecting..."
        self._state     = "running"
        self._error_msg = ""
        self._t         = 0.0
        self._dot       = StatusDot((W // 2, H // 2 + 20), ACCENT)
        threading.Thread(target=self._connect, daemon=True).start()

    def _connect(self):
        import system
        self._status = f"Connecting to {self.ssid}..."
        ok, msg = system.connect_wifi(self.ssid, self.password)
        if not ok:
            self._error_msg = msg
            self._state     = "error"
            return
        self._status = "Verifying internet..."
        if not system.verify_internet():
            self._error_msg = "Connected but no internet — check password"
            self._state     = "error"
            return
        self._status = "Configuring..."
        system.set_hostname(self.robot_name)
        system.write_robot_config(self.robot_name)
        self._state = "success"

    def update(self, dt, events, mouse_pos, mouse_down):
        self._t += dt
        self._dot.update(dt)
        if self._state == "success":
            return ("pulling", {"robot_name": self.robot_name})
        if self._state == "error":
            for e in events:
                if e.type in (pygame.MOUSEBUTTONUP, pygame.KEYDOWN):
                    return ("wifi_scan", {"robot_name": self.robot_name})
        return None

    def draw(self, surf):
        draw_title(surf, "Connecting", H // 2 - 80)
        if self._state == "error":
            self._dot.color = ERROR
            self._dot.draw(surf)
            draw_subtitle(surf, self._error_msg, H // 2 + 50, color=ERROR)
            draw_subtitle(surf, "Tap anywhere to try again", H // 2 + 80, color=TEXT_MUTED)
        elif self._state == "success":
            self._dot.color = SUCCESS
            self._dot.draw(surf)
            draw_subtitle(surf, "Connected", H // 2 + 50, color=SUCCESS)
        else:
            self._dot.draw(surf)
            dots = "." * (int(self._t * 2) % 4)
            draw_subtitle(surf, self._status + dots, H // 2 + 50, color=TEXT_MUTED)


# ── Pulling ───────────────────────────────────────────────────────────────────

class PullingScreen:
    def __init__(self, robot_name):
        self.robot_name = robot_name
        self._bar = ProgressBar(pygame.Rect(W // 2 - 220, H // 2 + 10, 440, 4))
        self._t   = 0.0
        import system
        self._job = system.PullJob(CONTAINERS_TO_PULL)
        self._job.start()

    def update(self, dt, events, mouse_pos, mouse_down):
        self._t += dt
        self._bar.update(dt)
        self._bar.value = self._job.progress
        if self._job.status == "success":
            import system
            system.finalize_setup()
            return "done"
        if self._job.status == "error":
            for e in events:
                if e.type in (pygame.MOUSEBUTTONUP, pygame.KEYDOWN):
                    import system
                    system.finalize_setup()
                    return "done"
        return None

    def draw(self, surf):
        draw_title(surf, "Almost there", H // 2 - 80)
        draw_subtitle(surf, "Downloading ZaraOS components", H // 2 - 42, color=TEXT_MUTED)
        self._bar.draw(surf)
        if self._job.status == "error":
            draw_subtitle(surf, self._job.error, H // 2 + 30, color=ERROR)
            draw_subtitle(surf, "Tap to continue anyway", H // 2 + 56, color=TEXT_MUTED)
        elif self._job.current:
            img = self._job.current.split("/")[-1]
            draw_subtitle(surf, f"{img}  ({self._job.done}/{self._job.total})",
                          H // 2 + 30, color=TEXT_MUTED)


# ── Done ──────────────────────────────────────────────────────────────────────

class DoneScreen:
    def __init__(self, robot_name):
        self.robot_name = robot_name
        self._t         = 0.0
        self._blink_t   = 0.0

    def update(self, dt, events, mouse_pos, mouse_down):
        self._t      += dt
        self._blink_t = (self._t % 4.0) / 4.0 * math.pi * 2
        if self._t > 2.5:
            return "exit"
        return None

    def draw(self, surf):
        draw_face_small(surf, W // 2, H // 2 - 20, scale=0.38, blink_t=self._blink_t)
        fade = min(1.0, self._t / 0.8)
        draw_title(surf, f"Hello, {self.robot_name}",
                   H // 2 + 130, color=lerp_color(BG, SUCCESS, fade))
        draw_subtitle(surf, "ZaraOS is ready", H // 2 + 168, color=TEXT_MUTED)