"""Reproducible Iris experiment; all model selection excludes the test set."""
from pathlib import Path
from copy import deepcopy
import json
import hashlib
import platform
import os
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from sklearn.datasets import load_iris
from sklearn.decomposition import PCA
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import log_loss, accuracy_score, classification_report, confusion_matrix

FEATURES = ['sepal_length_cm','sepal_width_cm','petal_length_cm','petal_width_cm']
SPECIES = ['setosa','versicolor','virginica']

def feature_matrix(df):
    # Canonical memory order prevents pandas block layout from changing reductions.
    return np.array(df[FEATURES].to_numpy(), dtype=np.float64, order='C', copy=True)

def load_data(path):
    raw = load_iris()
    df = pd.DataFrame(raw.data, columns=FEATURES)
    df.insert(0, 'sample_id', np.arange(len(df)))
    df['target'] = raw.target.astype(int)
    df['species'] = np.array(SPECIES)[raw.target]
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return df

def audit_data(df):
    x = df[FEATURES]
    q1,q3 = x.quantile(.25),x.quantile(.75)
    flags = (x < q1-1.5*(q3-q1)) | (x > q3+1.5*(q3-q1))
    return {'rows':len(df), 'missing':df.isna().sum().astype(int).to_dict(),
            'duplicate_observations':int(df.duplicated(FEATURES+['target']).sum()),
            'duplicate_sample_ids':df.loc[df.duplicated(FEATURES+['target'],keep=False),'sample_id'].tolist(),
            'class_counts':df.species.value_counts().to_dict(),
            'iqr_flags':flags.sum().astype(int).to_dict(),
            'iqr_flagged_ids':df.loc[flags.any(axis=1),'sample_id'].tolist(),
            'policy':'Retain original observations; group identical feature vectors in one partition; IQR flags are not automatic exclusions.'}

def split_data(df, seed=42):
    if not np.isfinite(df[FEATURES].to_numpy()).all():
        raise ValueError('All features must be finite.')
    # Group exact feature matches, preserving original row ids and all 150 rows.
    groups = df.groupby(FEATURES, sort=True).ngroup().to_numpy()
    distinct = pd.DataFrame({'group':groups,'target':df.target})
    if distinct.groupby('group').target.nunique().max() != 1:
        raise ValueError('Identical feature vectors have conflicting labels.')
    distinct = distinct.drop_duplicates('group')
    dev, test = train_test_split(distinct, test_size=.2, stratify=distinct.target, random_state=seed)
    train, validation = train_test_split(dev, test_size=.2, stratify=dev.target, random_state=seed)
    return {name:np.flatnonzero(np.isin(groups, rows.group)) for name,rows in
            [('train',train),('validation',validation),('test',test)]}

def fit_scaler(df, train_ids):
    return StandardScaler().fit(feature_matrix(df.iloc[train_ids]))

def pca_projection(df):
    """Full-data descriptive PCA only; never used as model input."""
    x = StandardScaler().fit_transform(feature_matrix(df))
    pca = PCA(n_components=3, svd_solver='full')
    return pca.fit_transform(x), pca

def fit_model(df, parts, seed=42, max_epochs=500, patience=40):
    """Select checkpoint by validation cross entropy, never by test scores."""
    if max_epochs < 1 or patience < 1:
        raise ValueError('Epochs and patience must be positive.')
    scaler = fit_scaler(df, parts['train'])
    train, val = df.iloc[parts['train']], df.iloc[parts['validation']]
    xt = scaler.transform(feature_matrix(train))
    xv = scaler.transform(feature_matrix(val))
    yt, yv = train.target.to_numpy(), val.target.to_numpy()
    model = MLPClassifier(hidden_layer_sizes=(16,8), activation='relu', solver='adam',
                          learning_rate_init=.01, alpha=.0001, batch_size=16,
                          shuffle=True, random_state=seed)
    history=[]; best_loss=float('inf'); best_epoch=0; best_model=None
    for epoch in range(1,max_epochs+1):
        model.partial_fit(xt, yt, classes=np.arange(3))
        pt, pv = model.predict_proba(xt), model.predict_proba(xv)
        row={'epoch':epoch,'train_loss':float(log_loss(yt,pt,labels=[0,1,2])),
             'validation_loss':float(log_loss(yv,pv,labels=[0,1,2])),
             'train_accuracy':float(accuracy_score(yt,pt.argmax(1))),
             'validation_accuracy':float(accuracy_score(yv,pv.argmax(1)))}
        history.append(row)
        if row['validation_loss'] < best_loss:
            best_loss=row['validation_loss']; best_epoch=epoch; best_model=deepcopy(model)
        if epoch-best_epoch >= patience:
            break
    return {'model':best_model,'scaler':scaler,'history':history,'best_epoch':best_epoch}

def evaluate_model(df, ids, fitted):
    test=df.iloc[ids].copy()
    prob=fitted['model'].predict_proba(fitted['scaler'].transform(feature_matrix(test)))
    pred=prob.argmax(1)
    report=classification_report(test.target,pred,labels=[0,1,2],target_names=SPECIES,output_dict=True,zero_division=0)
    metrics={'accuracy':float(accuracy_score(test.target,pred)),
             'macro_f1':report['macro avg']['f1-score'],
             'log_loss':float(log_loss(test.target,prob,labels=[0,1,2])),
             'classification_report':report,
             'confusion_matrix':confusion_matrix(test.target,pred,labels=[0,1,2]).tolist()}
    test['predicted_target']=pred
    test['predicted_species']=np.array(SPECIES)[pred]
    test['confidence']=prob.max(1)
    for i,name in enumerate(SPECIES): test['prob_'+name]=prob[:,i]
    return metrics,test

def write_json(path, value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')

def plot_results(root, df, points, pca, fitted, metrics):
    # Colab exports an inline backend unavailable in a fresh virtualenv.
    os.environ['MPLBACKEND']='Agg'
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    colors=['#237a8b','#db8b2b','#7755a5']
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,
                         'figure.facecolor':'white','savefig.facecolor':'white'})
    def save(fig,name):
        fig.savefig(root/'figures'/f'{name}.png',dpi=180,bbox_inches='tight')
        plt.close(fig)
    fig=plt.figure(figsize=(8,6)); ax=fig.add_subplot(projection='3d')
    for i,name in enumerate(SPECIES):
        mask=df.target==i
        ax.scatter(*points[mask].T,label=name,color=colors[i],s=24,alpha=.8)
    for axis,label,r in zip([ax.set_xlabel,ax.set_ylabel,ax.set_zlabel],['PC1','PC2','PC3'],pca.explained_variance_ratio_):
        axis(f'{label} ({r:.1%})',labelpad=10)
    ax.set_title(f'Iris: descriptive PCA | cumulative variance {pca.explained_variance_ratio_.sum():.2%}',pad=20)
    ax.legend(loc='upper right'); ax.view_init(elev=22,azim=125)
    # Some Matplotlib versions omit the 3D z-label from tight bounding boxes.
    ax.set_zlabel('')
    fig.text(.94,.50,f'PC3 ({pca.explained_variance_ratio_[2]:.1%})',rotation=90,va='center')
    save(fig,'pca_3d')
    fig,axes=plt.subplots(2,3,figsize=(12,7),layout='constrained')
    for ax,feature in zip(axes.flat,FEATURES):
        for i,name in enumerate(SPECIES):
            ax.hist(df.loc[df.target==i,feature],bins=10,alpha=.5,color=colors[i],label=name)
        ax.set(title=feature.replace('_',' '),xlabel='cm',ylabel='Count')
    axes[0,0].legend(fontsize=8)
    ax=axes[1,1]; ax.bar(SPECIES,[sum(df.target==i) for i in range(3)],color=colors)
    ax.set(title='Class balance',ylabel='Count')
    corr=df[FEATURES].corr().to_numpy(); ax=axes[1,2]
    im=ax.imshow(corr,vmin=-1,vmax=1,cmap='coolwarm')
    ax.set_xticks(range(4),['SL','SW','PL','PW']); ax.set_yticks(range(4),['SL','SW','PL','PW'])
    ax.set_title('Pearson correlation')
    for i in range(4):
        for j in range(4): ax.text(j,i,f'{corr[i,j]:.2f}',ha='center',va='center',fontsize=9)
    fig.colorbar(im,ax=ax,shrink=.7)
    save(fig,'exploration')
    h=pd.DataFrame(fitted['history'])
    fig,axs=plt.subplots(1,2,figsize=(10,3.8),layout='constrained')
    for ax,metric,title in zip(axs,['loss','accuracy'],['Cross-entropy (without L2 penalty)','Accuracy']):
        ax.plot(h.epoch,h['train_'+metric],label='Train',color=colors[0])
        ax.plot(h.epoch,h['validation_'+metric],label='Validation',color=colors[1])
        ax.axvline(fitted['best_epoch'],ls='--',color=colors[2],label='Selected checkpoint')
        ax.set(xlabel='Epoch',ylabel=title,title=title); ax.legend(fontsize=8); ax.grid(alpha=.2)
    save(fig,'training')
    cm=np.array(metrics['confusion_matrix'])
    fig,ax=plt.subplots(figsize=(6,4.5),layout='constrained')
    ax.imshow(cm,cmap='Blues',vmin=0)
    ax.set(xticks=range(3),yticks=range(3),xticklabels=SPECIES,yticklabels=SPECIES,
           xlabel='Predicted class',ylabel='True class',title='Held-out test confusion matrix')
    for i in range(3):
        for j in range(3): ax.text(j,i,str(cm[i,j]),ha='center',va='center',color='white' if cm[i,j]>cm.max()/2 else 'black')
    save(fig,'confusion')
    fig,ax=plt.subplots(figsize=(8,4),layout='constrained'); x=np.arange(3)
    for i,key in enumerate(['precision','recall','f1-score']):
        vals=[metrics['classification_report'][s][key] for s in SPECIES]
        bars=ax.bar(x+(i-1)*.24,vals,.24,label=key,color=colors[i])
        ax.bar_label(bars,fmt='%.2f',fontsize=8)
    ax.set(xticks=x,xticklabels=SPECIES,ylim=(0,1.2),ylabel='Score',title='Held-out test classification metrics')
    ax.legend(loc='upper right',fontsize=8,ncol=3)
    save(fig,'class_metrics')

def run_experiment(root, seed=42, max_epochs=500):
    import sklearn
    from sklearn.dummy import DummyClassifier
    root=Path(root)
    for folder in ['data','results','figures','reports']: (root/folder).mkdir(parents=True,exist_ok=True)
    df=load_data(root/'data/iris.csv')
    audit=audit_data(df); parts=split_data(df,seed)
    fitted=fit_model(df,parts,seed,max_epochs)
    metrics,predictions=evaluate_model(df,parts['test'],fitted)
    points,pca=pca_projection(df)
    baseline=DummyClassifier(strategy='most_frequent').fit(df.iloc[parts['train']][FEATURES],df.iloc[parts['train']].target)
    baseline_pred=baseline.predict(df.iloc[parts['test']][FEATURES])
    metrics.update({'seed':seed,'best_epoch':fitted['best_epoch'],'epochs_run':len(fitted['history']),
                    'max_epochs':max_epochs,'patience':40,
                    'partition_sizes':{k:len(v) for k,v in parts.items()},
                    'partition_class_counts':{k:df.iloc[v].species.value_counts().to_dict() for k,v in parts.items()},
                    'pca_variance_ratio':pca.explained_variance_ratio_.tolist(),
                    'pca_cumulative_variance':float(pca.explained_variance_ratio_.sum()),
                    'baseline_accuracy':float(accuracy_score(df.iloc[parts['test']].target,baseline_pred)),
                    'model':{'hidden_layers':[16,8],'activation':'relu','output':'softmax','solver':'adam',
                             'learning_rate':.01,'alpha':.0001,'batch_size':16,'loss':'cross entropy + L2 during training'},
                    'scaler_mean':fitted['scaler'].mean_.tolist(),
                    'versions':{'python':platform.python_version(),'scikit-learn':sklearn.__version__,'numpy':np.__version__,'pandas':pd.__version__}})
    write_json(root/'results/metrics.json',metrics); write_json(root/'results/audit.json',audit)
    write_json(root/'data/metadata.json',{'source':'sklearn.datasets.load_iris (bundled corrected Iris copy)',
               'source_url':'https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_iris.html',
               'original_reference':'Fisher (1936), UCI Iris, https://doi.org/10.24432/C56C76',
               'obtained_at_utc':datetime.now(timezone.utc).isoformat(),'scikit_learn_version':sklearn.__version__,
               'sha256':hashlib.sha256((root/'data/iris.csv').read_bytes()).hexdigest(),
               'features':{k:{'unit':'cm','dtype':'float'} for k in FEATURES},
               'target_mapping':dict(enumerate(SPECIES)),
               'sample_id':'zero-based source row; not a predictive feature',
               'note':'Use the bundled corrected copy consistently; do not silently mix alternate UCI file versions.'})
    df[FEATURES].describe().to_csv(root/'results/describe.csv')
    df.groupby('species')[FEATURES].mean().to_csv(root/'results/class_means.csv')
    df[FEATURES].corr().to_csv(root/'results/correlation.csv')
    pd.DataFrame(fitted['history']).to_csv(root/'results/history.csv',index=False)
    predictions.to_csv(root/'results/predictions.csv',index=False)
    predictions.loc[predictions.target!=predictions.predicted_target].to_csv(root/'results/misclassified.csv',index=False)
    split_rows=[{'sample_id':int(i),'partition':name} for name,ids in parts.items() for i in ids]
    pd.DataFrame(split_rows).sort_values('sample_id').to_csv(root/'results/splits.csv',index=False)
    pd.DataFrame(points,columns=['PC1','PC2','PC3']).assign(sample_id=df.sample_id,species=df.species).to_csv(root/'results/pca_scores.csv',index=False)
    pd.DataFrame(pca.components_,columns=FEATURES,index=['PC1','PC2','PC3']).to_csv(root/'results/pca_loadings.csv')
    plot_results(root,df,points,pca,fitted,metrics)
    return metrics

if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='.')
    parser.add_argument('--seed',type=int,default=42)
    args=parser.parse_args()
    print(json.dumps(run_experiment(args.output,args.seed),ensure_ascii=False,indent=2))
