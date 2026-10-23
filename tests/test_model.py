import numpy as np
from sklearn.metrics import accuracy_score, confusion_matrix
from iris_study import load_data, split_data, fit_model, evaluate_model, FEATURES

def test_training_is_repeatable_and_returns_normalized_probabilities(tmp_path):
    df=load_data(tmp_path/'iris.csv'); parts=split_data(df)
    a=fit_model(df,parts,max_epochs=80,patience=20)
    b=fit_model(df,parts,max_epochs=80,patience=20)
    x=df.iloc[parts['test']][FEATURES].to_numpy()
    pa=a['model'].predict_proba(a['scaler'].transform(x))
    pb=b['model'].predict_proba(b['scaler'].transform(x))
    np.testing.assert_allclose(pa,pb,atol=1e-12)
    np.testing.assert_allclose(pa.sum(axis=1),1)
    assert np.isfinite(pa).all() and pa.shape == (len(x),3)
    history=a['history']
    assert history[0]['train_loss'] > history[-1]['train_loss']
    assert a['best_epoch'] == min(history,key=lambda x:x['validation_loss'])['epoch']

def test_test_data_cannot_influence_model_selection(tmp_path):
    df=load_data(tmp_path/'iris.csv'); parts=split_data(df)
    a=fit_model(df,parts,max_epochs=40,patience=10)
    altered=df.copy()
    altered.loc[parts['test'],FEATURES] += 999
    altered.loc[parts['test'],'target'] = 0
    b=fit_model(altered,parts,max_epochs=40,patience=10)
    assert a['history'] == b['history']
    assert a['best_epoch'] == b['best_epoch']
    for left,right in zip(a['model'].coefs_,b['model'].coefs_):
        np.testing.assert_array_equal(left,right)

def test_evaluation_matches_independent_metrics(tmp_path):
    df=load_data(tmp_path/'iris.csv'); parts=split_data(df)
    fitted=fit_model(df,parts,max_epochs=80,patience=20)
    metrics,pred=evaluate_model(df,parts['test'],fitted)
    assert metrics['accuracy'] == accuracy_score(pred.target,pred.predicted_target)
    assert metrics['confusion_matrix'] == confusion_matrix(pred.target,pred.predicted_target,labels=[0,1,2]).tolist()
    assert sum(map(sum,metrics['confusion_matrix'])) == len(parts['test'])
    assert set(metrics['classification_report']) >= {'setosa','versicolor','virginica','macro avg'}
