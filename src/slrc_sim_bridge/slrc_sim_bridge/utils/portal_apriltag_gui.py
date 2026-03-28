#!/usr/bin/env python3
"""Tkinter GUI for SLRC portal settings and AprilTag monitoring (finals / competition).

Reads API base URL from env SLRC_API_URL (default http://127.0.0.1:8000).

The API server binds 0.0.0.0 (all interfaces). This GUI is an HTTP *client*: use
127.0.0.1 when it runs on the same host as the API, or http://<that-host-LAN-IP>:8000
from another machine. Do not use 0.0.0.0 in the URL when connecting — that address
is only for listening, not as a destination.
"""
import argparse
import os
import tkinter as tk
from tkinter import ttk, messagebox

import requests


def _server_url() -> str:
    return os.environ.get("SLRC_API_URL", "http://127.0.0.1:8000").rstrip("/")


# --- DECODING ALGORITHM (Internal) ---
def retrieve_coordinates(A_value):
    if A_value < 0 or A_value >= 8750:
        raise ValueError("Invalid A value")

    order = (A_value // 625) + 1
    remainder = A_value % 625
    row = remainder // 25
    col = remainder % 25
    return order, row, col


def decode_tag(tag_value):
    """Decode 5-digit tag; returns (order, row, col) or None on invalid input."""
    try:
        ts = str(tag_value).zfill(5)
        if len(ts) != 5:
            raise ValueError("Invalid tag value length")

        key_id = int(ts[0])
        payload = int(ts[1:])

        if key_id == 0:  # Key 0 = 6180
            p_rev = int(str(payload).zfill(4)[::-1])
            A = ((p_rev * 7) + 6180) % 10000
            return retrieve_coordinates(A)

        elif key_id == 1:  # Key 1 = 3141
            s = str(payload).zfill(4)
            p_swap = int(s[2:4] + s[0:2])
            A = ((p_swap * 3) + 3141) % 8750
            return retrieve_coordinates(A)

        elif key_id == 2:  # Key 2 = 2718
            p_comp = 9999 - payload
            A = ((p_comp * 9) + 2718) % 8750
            return retrieve_coordinates(A)

        elif key_id == 3:  # Key 3 = 8080
            s = list(str(payload).zfill(4))
            s[0], s[3] = s[3], s[0]
            p_int = int("".join(s))
            A = ((p_int * 11) + 8080) % 8750
            return retrieve_coordinates(A)

        elif key_id == 4:  # Key 4 = 4040
            g = payload ^ (payload >> 1)
            A = g ^ 4040
            return retrieve_coordinates(A)

        else:
            raise ValueError("Invalid key ID")
    except (ValueError, TypeError):
        return None


class App:
    def __init__(self, root, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.root = root
        self.root.title("Temp debug portal for contestants")
        self.root.geometry("950x550")
        self._push_after_id = None
        self._loading_from_server = False

        frame_top = tk.LabelFrame(root, text="Portal Settings & Live Monitor", padx=10, pady=10)
        frame_top.pack(fill="x", padx=10, pady=5)

        tk.Label(frame_top, text="Trigger Status:").pack(side="left", padx=5)
        self.led_canvas = tk.Canvas(frame_top, width=30, height=30, highlightthickness=0)
        self.led_canvas.pack(side="left", padx=5)
        self.led_circle = self.led_canvas.create_oval(5, 5, 25, 25, fill="grey", outline="black")

        tk.Label(frame_top, text="Count:").pack(side="left", padx=(20, 5))
        self.slider = tk.Scale(
            frame_top,
            from_=0,
            to=3,
            orient="horizontal",
            command=self._on_slider_moved,
        )
        self.slider.pack(side="left", padx=5)

        self.check_var = tk.BooleanVar()
        self.check = tk.Checkbutton(
            frame_top,
            text="Trigger",
            variable=self.check_var,
            command=self._push_portal_settings,
        )
        self.check.pack(side="left", padx=5)

        frame_bot = tk.LabelFrame(root, text="April Tag Validation", padx=10, pady=10)
        frame_bot.pack(fill="both", expand=True, padx=10, pady=5)

        cols = ("raw", "rx_o", "c_o", "rx_x", "c_x", "rx_y", "c_y", "status")
        self.tree = ttk.Treeview(frame_bot, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=c.upper())
            self.tree.column(c, width=90, anchor="center")

        self.tree.tag_configure("match", background="#d4edda")
        self.tree.tag_configure("mismatch", background="#f8d7da")
        self.tree.pack(fill="both", expand=True)

        btn_frame = tk.Frame(root)
        btn_frame.pack(fill="x", padx=10, pady=5)
        tk.Button(btn_frame, text="Refresh Table", command=self.fetch_tags).pack(side="left")
        tk.Button(btn_frame, text="Reset Server Tags", command=self.reset_tags, fg="red").pack(side="right")

        self._load_initial_from_server()
        self.poll_trigger()
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _on_closing(self):
        if self._push_after_id is not None:
            try:
                self.root.after_cancel(self._push_after_id)
            except tk.TclError:
                pass
            self._push_after_id = None
        self.root.destroy()

    def _on_slider_moved(self, _value):
        """Scale fires on every tick while dragging; debounce POST to avoid flooding."""
        if self._loading_from_server:
            return
        if self._push_after_id is not None:
            self.root.after_cancel(self._push_after_id)
        self._push_after_id = self.root.after(200, self._debounced_push)

    def _debounced_push(self):
        self._push_after_id = None
        self._push_portal_settings()

    def _load_initial_from_server(self):
        """One-time GET so slider/checkbox match server before live updates."""
        try:
            r = requests.get(f"{self.base_url}/get_num_boxes_portal", timeout=2)
            if r.status_code != 200:
                return
            data = r.json()
            self._loading_from_server = True
            try:
                self.slider.set(int(data.get("count", 0)))
                self.check_var.set(bool(data.get("trigger", False)))
            finally:
                self._loading_from_server = False
        except requests.RequestException:
            pass

    def update_led(self, state):
        color = "#00FF00" if state else "#808080"
        self.led_canvas.itemconfig(self.led_circle, fill=color)

    def poll_trigger(self):
        try:
            r = requests.get(f"{self.base_url}/get_num_boxes_portal", timeout=0.5)
            if r.status_code == 200:
                self.update_led(r.json().get("trigger", False))
        except requests.RequestException:
            self.update_led(False)
        self.root.after(1000, self.poll_trigger)

    def _push_portal_settings(self):
        if self._loading_from_server:
            return
        try:
            requests.post(
                f"{self.base_url}/set_num_boxes_portal",
                json={"count": int(self.slider.get()), "trigger": bool(self.check_var.get())},
                timeout=1,
            )
        except requests.RequestException as e:
            messagebox.showerror("Error", str(e))

    def fetch_tags(self):
        try:
            data = requests.get(f"{self.base_url}/get_april_tag", timeout=2).json().get("data", [])
            for i in self.tree.get_children():
                self.tree.delete(i)
            for e in data:
                calc = decode_tag(e["raw"])
                res = calc if calc else ("?", "?", "?")
                is_match = calc and (
                    int(e["order"]) == res[0] and int(e["x"]) == res[1] and int(e["y"]) == res[2]
                )
                status = "MATCH" if is_match else "FAIL"
                tag = "match" if status == "MATCH" else "mismatch"

                self.tree.insert(
                    "",
                    "end",
                    values=(
                        e["raw"],
                        e["order"],
                        res[0],
                        e["x"],
                        res[1],
                        e["y"],
                        res[2],
                        status,
                    ),
                    tags=(tag,),
                )
        except (requests.RequestException, KeyError, ValueError, TypeError):
            pass

    def reset_tags(self):
        try:
            requests.post(
                f"{self.base_url}/reset_april_tag",
                json={"pass": "slrc_is_the_best"},
                timeout=2,
            )
            self.fetch_tags()
        except requests.RequestException:
            pass


def main():
    parser = argparse.ArgumentParser(description="Portal & AprilTag organizer GUI")
    parser.add_argument(
        "--api-url",
        default=_server_url(),
        help="API base URL (overrides SLRC_API_URL)",
    )
    args = parser.parse_args()
    os.environ["SLRC_API_URL"] = args.api_url
    root = tk.Tk()
    App(root, args.api_url)
    root.mainloop()


if __name__ == "__main__":
    main()
