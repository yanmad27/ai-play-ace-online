"""Small CPU imitation baseline; dataset sessions stay separate during validation."""
from collections import deque
import json
from pathlib import Path

import cv2
import joblib
import numpy as np
from sklearn.ensemble import ExtraTreesRegressor

KEYS = ('w', 'a', 's', 'd', 'space', '1', '2', '3', '4', '5')
CONTROLS = KEYS + ('left', 'right')
VERSION = 1


class History:
    def __init__(self):
        self.frames = deque(maxlen=3)

    def push(self, frame):
        small = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (48, 27))
        self.frames.append(small.astype(np.float32).ravel() / 255)
        while len(self.frames) < 3:
            self.frames.appendleft(self.frames[0].copy())
        return np.concatenate(self.frames)


def train(root):
    sessions = sorted(Path(root).glob('sessions/*/samples.npz'))
    if len(sessions) < 2:
        raise ValueError('Record at least two separate sessions; last session is validation.')
    xs, ys = [], []
    for file in sessions:
        with np.load(file, allow_pickle=False) as data:
            if data['x'].shape[0] < 50:
                raise ValueError(f'Session too short (minimum 50 frames): {file.parent.name}')
            xs.append(data['x'].copy())
            ys.append(data['y'].copy())
    model = ExtraTreesRegressor(n_estimators=48, max_depth=18,
                               min_samples_leaf=3, n_jobs=2, random_state=42)
    model.fit(np.concatenate(xs[:-1]), np.concatenate(ys[:-1]))
    predicted = model.predict(xs[-1])
    report = {
        'version': VERSION,
        'training_sessions': [p.parent.name for p in sessions[:-1]],
        'validation_session': sessions[-1].parent.name,
        'mouse_normalized_mae': float(np.abs(predicted[:, :2] - ys[-1][:, :2]).mean()),
        'button_accuracy': float(((predicted[:, 2:] >= .5) == (ys[-1][:, 2:] >= .5)).mean()),
        'note': 'Offline imitation metrics do not demonstrate successful farming.',
    }
    # Deliberately require explicit activation; a new candidate never replaces active.
    joblib.dump({'version': VERSION, 'model': model}, Path(root) / 'candidate.joblib')
    (Path(root) / 'validation.json').write_text(json.dumps(report, indent=2))
    return report
