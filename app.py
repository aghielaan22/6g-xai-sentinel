from pathlib import Path
import json
import joblib
import numpy as np
import pandas as pd
import streamlit as st
import shap
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title='6G-XAI Sentinel', page_icon='🛡️', layout='wide')
st.markdown('''<style>

[data-testid="stMetric"] {border:1px solid #64748b55;border-radius:12px;padding:18px;}

.stButton button {border-radius:8px;}
</style>''', unsafe_allow_html=True)
def read(name):
    return json.loads((ROOT/name).read_text())
features=read('features.json'); metrics=read('metrics.json'); examples=read('examples.json')
@st.cache_resource
def load_engine():
    model=joblib.load(ROOT/'model.pkl')
    background=pd.read_csv(ROOT/'background.csv',float_precision='round_trip')[features]
    return model, shap.TreeExplainer(model,data=background)

st.sidebar.title('🛡️ 6G-XAI Sentinel')
st.sidebar.caption('Research prototype • 2026')
page=st.sidebar.radio('Navigation',['Overview','Classify & Explain','Explainability','Evaluation','About'])
st.sidebar.info('Offline flow-level analysis • CICIDS2017 + simulated timing anomalies')
st.title('6G-XAI Sentinel')
st.caption('Explainable intelligence for next-generation network security')
colors={'Attack':'#f87171','Normal':'#34d399','Timing Anomaly':'#fbbf24'}
classes=metrics['classes']
if page=='Overview':
    st.header('Network intelligence overview')
    c=st.columns(4)
    for col,label,key in zip(c,['Accuracy','Weighted precision','Weighted recall','Weighted F1'],['accuracy','precision','recall','f1_score']):
        col.metric(label,f'{metrics[key]:.2%}')
    a,b=st.columns(2)
    with a:
        st.subheader('Classification recall')
        for name in classes:
            r=metrics['classification_report'][name]['recall']
            st.write(f'{name} · {r:.2%}')
            st.progress(r)
    with b:
        st.subheader('Experimental dataset')
        st.metric('Training flows',f"{metrics['training_records']:,}")
        st.metric('Test flows',f"{metrics['test_records']:,}")
        st.success('SHAP numerical verification passed on 200 sampled records')
    st.info('Start with Classify & Explain in the sidebar to run live inference on an example or your own numerical inputs.')
elif page=='Classify & Explain':
    st.header('Network traffic classification')
    st.caption('Choose a held-out example or edit the ten flow features. Predictions and SHAP values are computed on demand.')
    options=['Custom input']+[f"{e['actual_category']} — example {i%5+1}" for i,e in enumerate(examples)]
    choice=st.selectbox('Traffic example',options,index=6)
    idx=options.index(choice)-1
    defaults=examples[idx]['features'] if idx>=0 else dict.fromkeys(features,0.0)
    with st.form('traffic_form'):
        cols=st.columns(2); values={}
        for i,name in enumerate(features):
            values[name]=cols[i%2].number_input(name,min_value=0.0,value=float(defaults[name]),format='%.8g',key=f'{choice}-{name}')
        submitted=st.form_submit_button('Classify & Explain',type='primary')
    if submitted:
        try:
            x=pd.DataFrame([values],columns=features)
            if not np.isfinite(x.to_numpy()).all() or (x.to_numpy()<0).any():
                raise ValueError('Enter finite non-negative values.')
            with st.spinner('Running Random Forest and SHAP…'):
                model,explainer=load_engine()
                p=model.predict_proba(x)[0]; pred=str(model.predict(x)[0]); k=list(model.classes_).index(pred)
                exp=explainer(x,check_additivity=False); local=exp[0,:,k]
                error=abs(float(local.base_values)+float(local.values.sum())-p[k])
            st.subheader('Classification result')
            a,b=st.columns(2); a.metric('Predicted category',pred); b.metric('Predicted class probability',f'{p[k]:.2%}')
            if idx>=0 and values==defaults: st.caption(f"Actual example label: {examples[idx]['actual_category']}")
            else: st.caption('Edited/custom input: actual label unknown.')
            for name,prob in zip(model.classes_,p):
                st.write(f'{name}: {prob:.2%}'); st.progress(float(prob))
            st.subheader(f'Why {pred}?')
            df=pd.DataFrame({'Feature':features,'SHAP contribution':local.values}); df['Magnitude']=df['SHAP contribution'].abs()
            st.dataframe(df.sort_values('Magnitude',ascending=False).drop(columns='Magnitude'),hide_index=True,use_container_width=True)
            shap.plots.waterfall(local,max_display=10,show=False)
            fig=plt.gcf(); st.pyplot(fig); plt.close(fig)
            st.caption('Red increases the predicted class output; blue decreases it. Contributions are not causal effects.')
            if error<1e-4: st.success(f'Explanation reconstruction check passed (error {error:.2e}).')
            else: st.warning(f'Explanation reconstruction mismatch: {error:.2e}.')
        except Exception as exc:
            st.error(f'Inference failed: {exc}')
elif page=='Explainability':
    st.header('Explainable AI analysis')
    st.caption('Saved experimental plots; use Classify & Explain for a new local explanation.')
    for title,file,desc in [('Global feature importance','6G_XAI_Global_SHAP.png','Mean absolute SHAP contributions across 200 sampled test records and three classes.'),('Attack classification beeswarm','6G_XAI_Attack_SHAP.png','Each dot represents a sampled flow; horizontal position is the contribution to the Attack output, and colour indicates the feature value.'),('Local explanation — saved example','6G_XAI_Local_SHAP.png','Contributions to the predicted class for one previously explained record.')]:
        st.subheader(title); st.image(str(ROOT/file)); st.caption(desc)
    st.write(f"Maximum reconstruction difference: {metrics['shap_verification']['max_difference']:.3e}")
elif page=='Evaluation':
    st.header('Model evaluation')
    c=st.columns(4)
    for col,label,key in zip(c,['Accuracy','Weighted precision','Weighted recall','Weighted F1'],['accuracy','precision','recall','f1_score']): col.metric(label,f'{metrics[key]:.2%}')
    st.image(str(ROOT/'6G_XAI_Confusion_Matrix.png'))
    report=pd.DataFrame(metrics['classification_report']).T.loc[classes]
    st.dataframe(report.style.format({'precision':'{:.2%}','recall':'{:.2%}','f1-score':'{:.2%}','support':'{:.0f}'}),use_container_width=True)
    st.caption('2,277 correct classifications; 21 misclassifications. Results apply to the experimental test split.')
else:
    st.header('About the research')
    st.write('Explainable AI (XAI)-Driven Framework for Protocol Anomaly Classification and Identification in 6G-Communication Networks.')
    st.markdown('**Methodology:** CICIDS2017 → preprocessing → 10 flow features → stratified train/test split → separately simulated timing anomalies → Random Forest (100 trees) → SHAP TreeExplainer.')
    st.warning('CICIDS2017 is not real 6G traffic. Timing anomalies are synthetic and may be easier to identify because they follow predefined transformations. This is an offline flow-level proof of concept, not live packet monitoring or evidence of real 6G attack detection. SHAP does not establish causation. Model probabilities are not guaranteed correctness.')
st.divider(); st.caption('6G-XAI Sentinel | Final Year Project | Offline experimental research prototype')
