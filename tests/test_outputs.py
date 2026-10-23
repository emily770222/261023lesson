import json
import numpy as np
import pandas as pd
from iris_study import run_experiment

def test_experiment_writes_consistent_data_metrics_and_figures(tmp_path):
    summary=run_experiment(tmp_path, max_epochs=80)
    data=pd.read_csv(tmp_path/'data/iris.csv')
    predictions=pd.read_csv(tmp_path/'results/predictions.csv')
    saved=json.loads((tmp_path/'results/metrics.json').read_text())
    assert len(data)==150
    assert saved['accuracy']==summary['accuracy']
    assert saved['accuracy']==(predictions.target==predictions.predicted_target).mean()
    assert sum(saved['partition_sizes'].values())==150
    assert sum(map(sum,saved['confusion_matrix']))==len(predictions)
    assert np.isfinite(pd.read_csv(tmp_path/'results/history.csv').to_numpy()).all()
    for name in ['pca_3d','exploration','training','confusion','class_metrics']:
        image=tmp_path/'figures'/f'{name}.png'
        assert image.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
        assert image.stat().st_size>10000
    assert (tmp_path/'data/metadata.json').exists()
    assert (tmp_path/'results/splits.csv').exists()
    assert (tmp_path/'results/misclassified.csv').exists()
