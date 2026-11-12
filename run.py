import sys

if '--self-test' in sys.argv:
    import tempfile
    from pathlib import Path
    import joblib
    import numpy as np
    from ace_pilot.learning import History, train
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        history = History()
        features = np.stack([history.push(np.full((90, 160, 3), i, np.uint8)) for i in range(60)])
        for name in ('01', '02'):
            session = root / 'sessions' / name
            session.mkdir(parents=True)
            np.savez_compressed(session / 'samples.npz', x=features, y=np.zeros((60, 14)))
        train(root)
        model = joblib.load(root / 'candidate.joblib')['model']
        assert model.predict(features[:1]).shape == (1, 14)
    print('Packaged capture-feature/train/load/predict smoke test passed')
else:
    from ace_pilot.app import main
    main()
