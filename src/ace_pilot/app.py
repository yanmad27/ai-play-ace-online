import json
import os
from pathlib import Path
import queue
import shutil
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox

import cv2
import joblib
import mss
import numpy as np

from ace_pilot.learning import CONTROLS, History, VERSION, train


class App:
    def __init__(self, window):
        from ace_pilot.windows import Desktop
        self.desktop = Desktop()
        self.root = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'AcePilot'
        self.root.mkdir(parents=True, exist_ok=True)
        self.window, self.events = window, queue.Queue()
        self.stop = threading.Event()
        self.worker = None
        window.title('ACE Pilot — experimental imitation learner')
        window.geometry('600x390')
        tk.Label(window, text='I-Gear: record → train → observe → activate → run', font=('', 14)).pack(pady=12)
        tk.Label(window, text='Select an exact game title. After starting, focus game within 5 seconds.\nF8 stops input immediately. Focus loss stops the session.').pack()
        self.title = tk.StringVar(value='ACE Online')
        tk.Entry(window, textvariable=self.title, width=55).pack(pady=8)
        for text, mode in [('Record demonstration', 'record'), ('Train candidate', 'train'),
                           ('Observe candidate (no input)', 'observe'), ('Run active model', 'run')]:
            tk.Button(window, text=text, command=lambda m=mode: self.start(m)).pack(fill='x', padx=50)
        tk.Button(window, text='Activate candidate', command=self.activate).pack(pady=4)
        tk.Button(window, text='STOP / take over (F8)', command=self.stop.set).pack()
        self.status = tk.StringVar(value=f'Data: {self.root}')
        tk.Label(window, textvariable=self.status, wraplength=570).pack(pady=8)
        window.protocol('WM_DELETE_WINDOW', self.close)
        window.after(100, self.poll)

    def busy(self):
        return self.worker is not None and self.worker.is_alive()

    def start(self, mode):
        if self.busy():
            return
        self.stop.clear()
        expected = self.title.get().strip()
        if not expected:
            return
        self.worker = threading.Thread(target=self.work, args=(mode, expected), daemon=True)
        self.worker.start()

    def activate(self):
        if self.busy():
            return
        source = self.root / 'candidate.joblib'
        if source.exists() and messagebox.askyesno('Activate', 'Review validation.json and observe predictions first. Activate candidate?'):
            active = self.root / 'active.joblib'
            if active.exists():
                shutil.copy2(active, self.root / 'previous.joblib')
            shutil.copy2(source, active)
            self.status.set('Candidate activated. Previous model preserved.')

    def work(self, mode, expected):
        samples, actions, timestamps = [], [], []
        video, session, prediction_log = None, None, None
        try:
            if mode == 'train':
                self.events.put('Training; please wait...')
                self.events.put(json.dumps(train(self.root)))
                return
            model = None
            if mode != 'record':
                bundle = joblib.load(self.root / ('candidate.joblib' if mode == 'observe' else 'active.joblib'))
                if bundle['version'] != VERSION:
                    raise ValueError('Model version mismatch')
                model = bundle['model']
            for count in range(5, 0, -1):
                self.events.put(f'Focus game: {count} seconds')
                if self.stop.wait(1):
                    return
            hwnd = self.desktop.foreground()
            if self.desktop.title(hwnd).casefold() != expected.casefold():
                raise ValueError('Foreground title differs. Enter the exact game window title.')
            region = self.desktop.region(hwnd)
            geometry = (region['width'], region['height'])
            if mode == 'record':
                session = self.root / 'sessions' / str(time.time_ns())
                session.mkdir(parents=True)
                (session / 'metadata.json').write_text(json.dumps({'title': expected, 'region': region,
                    'fps': 10, 'controls': CONTROLS, 'version': VERSION}))
                video = cv2.VideoWriter(str(session / 'screen.avi'), cv2.VideoWriter_fourcc(*'MJPG'), 10, geometry)
                if not video.isOpened():
                    raise RuntimeError('Video encoder unavailable')
            if mode != 'record':
                logs = self.root / 'predictions'
                logs.mkdir(exist_ok=True)
                prediction_log = (logs / f'{time.time_ns()}-{mode}.jsonl').open('w')
            history = History()
            started, frames = time.monotonic(), 0
            with mss.mss() as capture:
                while not self.stop.is_set():
                    tick = time.monotonic()
                    if self.desktop.user.GetAsyncKeyState(0x77) & 0x8000:  # F8
                        break
                    if self.desktop.foreground() != hwnd:
                        break
                    region = self.desktop.region(hwnd)
                    if geometry != (region['width'], region['height']):
                        raise RuntimeError('Window resized. Start a new session.')
                    frame = np.asarray(capture.grab(region))[:, :, :3].copy()
                    feature = history.push(frame)
                    if mode == 'record':
                        position = self.desktop.cursor(region)
                        if not all(0 <= value <= 1 for value in position):
                            break
                        action = np.array([*position, *(float(self.desktop.down(k)) for k in CONTROLS)], dtype=np.float32)
                        timestamps.append(time.monotonic() - started)
                        samples.append(feature)
                        actions.append(action)
                        video.write(frame)
                    else:
                        action = model.predict(feature[None])[0]
                        prediction_log.write(json.dumps({'t': time.monotonic()-started, 'action': action.tolist()}) + '\n')
                        prediction_log.flush()
                        # Re-check focus after potentially expensive prediction.
                        if self.stop.is_set() or self.desktop.foreground() != hwnd or self.desktop.user.GetAsyncKeyState(0x77) & 0x8000:
                            break
                        if mode == 'run':
                            self.desktop.apply(action, region, CONTROLS)
                    frames += 1
                    if frames % 10 == 0:
                        detail = '' if mode == 'record' else f' | mouse {action[0]:.2f}, {action[1]:.2f}'
                        self.events.put(f'{mode}: {frames} frames, {frames/(time.monotonic()-started):.1f} FPS{detail}')
                    # Bound RAM and recording size; multiple short sessions are preferred.
                    if mode == 'record' and frames >= 3000:
                        break
                    self.stop.wait(max(0, .1 - (time.monotonic()-tick)))
        except Exception as error:
            self.events.put(f'Error: {error}')
        finally:
            self.desktop.release()
            if prediction_log is not None:
                prediction_log.close()
            if video is not None:
                video.release()
            if samples:
                np.savez_compressed(session / 'samples.npz', x=np.stack(samples), y=np.stack(actions), t=np.asarray(timestamps))
                self.events.put(f'Saved {len(samples)} frames: {session}')
            elif mode not in ('train',):
                self.events.put('Stopped. All bot-held controls released.')

    def poll(self):
        try:
            while True:
                self.status.set(self.events.get_nowait())
        except queue.Empty:
            pass
        if self.busy() and self.desktop.user.GetAsyncKeyState(0x77) & 0x8000:
            self.stop.set()
        self.window.after(50, self.poll)

    def close(self):
        self.stop.set()
        if self.busy():
            self.status.set('Stopping and saving; waiting for worker...')
            self.window.after(100, self.close)
        else:
            self.window.destroy()


def main():
    if sys.platform != 'win32':
        raise SystemExit('ACE Pilot desktop app requires Windows. Learning tests run on macOS.')
    import ctypes
    ctypes.windll.user32.SetProcessDPIAware()
    window = tk.Tk()
    App(window)
    window.mainloop()
