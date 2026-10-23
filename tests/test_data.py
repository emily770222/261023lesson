import numpy as np
import pandas as pd
import pytest
from iris_study import FEATURES, load_data, audit_data, split_data, fit_scaler, pca_projection

def test_dataset_saved_losslessly(tmp_path):
    df = load_data(tmp_path / 'iris.csv')
    assert df.shape == (150, 7)
    assert df['species'].value_counts().to_dict() == {'setosa':50,'versicolor':50,'virginica':50}
    assert df[FEATURES].min().min() > 0
    pd.testing.assert_frame_equal(df, pd.read_csv(tmp_path / 'iris.csv'))

def test_audit_counts_missing_duplicates_and_outliers(tmp_path):
    df = load_data(tmp_path / 'iris.csv')
    a = audit_data(df)
    assert a['rows'] == 150 and a['duplicate_observations'] == 1
    assert sum(a['missing'].values()) == 0
    changed = df.copy()
    changed.loc[0, FEATURES[0]] = np.nan
    changed.loc[1, FEATURES[1]] = 999
    b = audit_data(changed)
    assert b['missing'][FEATURES[0]] == 1
    assert b['iqr_flags'][FEATURES[1]] >= 1

def test_partition_is_repeatable_stratified_and_group_disjoint(tmp_path):
    df = load_data(tmp_path / 'iris.csv')
    parts = split_data(df, seed=42)
    again = split_data(df, seed=42)
    assert set(parts) == {'train','validation','test'}
    assert sorted(np.concatenate(list(parts.values()))) == list(range(150))
    for name, ids in parts.items():
        np.testing.assert_array_equal(ids, again[name])
        assert set(df.iloc[ids].target) == {0,1,2}
    groups = {k:set(map(tuple, df.iloc[v][FEATURES].to_numpy())) for k,v in parts.items()}
    assert not groups['train'] & groups['test']
    assert not groups['train'] & groups['validation']
    assert not groups['test'] & groups['validation']

def test_scaler_fits_training_only(tmp_path):
    df = load_data(tmp_path / 'iris.csv')
    p = split_data(df)
    s = fit_scaler(df, p['train'])
    np.testing.assert_allclose(s.mean_, df.iloc[p['train']][FEATURES].mean())
    altered = df.copy()
    altered.loc[p['test'], FEATURES] += 10000
    altered.loc[p['validation'], FEATURES] -= 10000
    np.testing.assert_array_equal(s.mean_, fit_scaler(altered,p['train']).mean_)

def test_pca_is_three_dimensional_finite_and_reports_variance(tmp_path):
    df=load_data(tmp_path/'iris.csv')
    points, pca = pca_projection(df)
    assert points.shape == (150,3) and np.isfinite(points).all()
    assert len(pca.explained_variance_ratio_) == 3
    assert 0.95 < pca.explained_variance_ratio_.sum() <= 1

def test_invalid_features_are_rejected(tmp_path):
    df=load_data(tmp_path/'iris.csv')
    df.loc[0,FEATURES[0]]=np.nan
    with pytest.raises(ValueError):
        split_data(df)
