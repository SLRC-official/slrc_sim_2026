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
def retrieve_coordinates(a_value):
    if a_value < 0 or a_value >= 8750:
        return None
    return (a_value // 625) + 1, (a_value % 625) // 25, (a_value % 625) % 25


def decode_tag(tag_value):
    try:
        ts = str(tag_value).zfill(5)
        kid, p = int(ts[0]), int(ts[1:])
        if kid == 0:
            a = ((int(str(p).zfill(4)[::-1]) * 7) + 6180) % 10000
        elif kid == 1:
            s = str(p).zfill(4)
            a = ((int(s[2:4] + s[0:2]) * 3) + 3141) % 8750
        elif kid == 2:
            a = (((9999 - p) * 9) + 2718) % 8750
        elif kid == 3:
            s = list(str(p).zfill(4))
            s[0], s[3] = s[3], s[0]
            a = ((int("".join(s)) * 11) + 8080) % 8750
        elif kid == 4:
            a = ((p ^ (p >> 1)) + 4040) % 8750
        else:
            return None
        return retrieve_coordinates(a)
    except (ValueError, TypeError, IndexError):
        return None


class App:
    def __init__(self, root, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.root = root
        self.root.title("Portal Controller & LED Monitor")
        self.root.geometry("950x550")

        frame_top = tk.LabelFrame(root, text="Portal Settings & Live Monitor", padx=10, pady=10)
        frame_top.pack(fill="x", padx=10, pady=5)

        tk.Label(frame_top, text="Trigger Status:").pack(side="left", padx=5)
        self.led_canvas = tk.Canvas(frame_top, width=30, height=30, highlightthickness=0)
        self.led_canvas.pack(side="left", padx=5)
        self.led_circle = self.led_canvas.create_oval(5, 5, 25, 25, fill="grey", outline="black")

        tk.Label(frame_top, text="Count:").pack(side="left", padx=(20, 5))
        self.slider = tk.Scale(frame_top, from_=0, to=3, orient="horizontal")
        self.slider.pack(side="left", padx=5)

        self.check_var = tk.BooleanVar()
        self.check = tk.Checkbutton(frame_top, text="Trigger", variable=self.check_var)
        self.check.pack(side="left", padx=5)

        tk.Button(frame_top, text="Push Changes", command=self.send_settings, bg="#d1e7ff").pack(
            side="left", padx=10
        )
        tk.Button(frame_top, text="Manual Sync", command=self.sync_settings).pack(side="left")

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

        self.poll_trigger()

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

    def send_settings(self):
        try:
            requests.post(
                f"{self.base_url}/set_num_boxes_portal",
                json={"count": self.slider.get(), "trigger": self.check_var.get()},
                timeout=1,
            )
        except requests.RequestException as e:
            messagebox.showerror("Error", str(e))

    def sync_settings(self):
        try:
            r = requests.get(f"{self.base_url}/get_num_boxes_portal", timeout=1)
            data = r.json()
            self.slider.set(data.get("count", 0))
            self.check_var.set(data.get("trigger", False))
        except requests.RequestException:
            pass

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
