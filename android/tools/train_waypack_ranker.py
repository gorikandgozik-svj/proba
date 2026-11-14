#!/usr/bin/env python3
"""WAYPACK RankNet v1: small Google LiteRT recommender.
This model is trained ONLY on generated training scenarios and curated travel
signals, not on real user records. Google LiteRT is the runtime, NOT a pretrained
Gemini or Gemma model. The loss/holdout metrics quantify agreement with the
scenario teacher, not measured travel satisfaction.
"""
import json
import os
from pathlib import Path
import numpy as np
import tensorflow as tf

SEED=24071
FEATURES=18
OUT=Path(__file__).resolve().parents[1]/"app/src/main/assets/waypack-ranker.tflite"
AUDIT=Path(__file__).resolve().parents[1]/"tests/waypack-ranker-audit.json"
np.random.seed(SEED)
tf.keras.utils.set_random_seed(SEED)
rng=np.random.default_rng(SEED)

def make_samples(n):
    x=np.zeros((n,FEATURES),dtype=np.float32)
    # Item tags: beach / hike / ski / photo / general
    tags=rng.integers(0,5,n)
    x[np.arange(n),tags]=1
    # Selected activity flags: independent multi-label scenarios
    x[:,5:9]=(rng.random((n,4))<0.35).astype(np.float32)
    # Cold / hot are exclusive
    climates=rng.integers(0,3,n)
    x[:,9]=(climates==1)
    x[:,10]=(climates==2)
    x[:,11]=rng.uniform(1/30,1,n)
    x[:,12]=rng.uniform(1/8,1,n)
    x[:,13]=(rng.random(n)<0.40)
    x[:,14]=rng.uniform(0.15,1,n)
    x[:,15]=(rng.random(n)<0.30)
    x[:,16]=(rng.random(n)<0.25)
    x[:,17]=(rng.random(n)<0.25)
    # Synthetically defined relevance teacher, interpretable and auditable
    match=(x[:,:4]*x[:,5:9]).sum(axis=1)
    general=x[:,4]
    beach_hot=x[:,0]*x[:,5]*x[:,10]
    ski_cold=x[:,2]*x[:,7]*x[:,9]
    wet_beach=x[:,16]*x[:,5]
    tech_photo=x[:,17]*x[:,8]
    value=(0.5 + 2.8*match + 1.2*x[:,14] + 0.2*general
        + 0.5*beach_hot + 0.5*ski_cold + 0.3*wet_beach
        + 0.3*tech_photo + 0.2*x[:,11]*general
        + 0.15*x[:,15]*x[:,16])
    target=(1/(1+np.exp(-(value-1.7)*1.0))).astype(np.float32)
    return x,target[:,None]

x,y=make_samples(36000)
train_x,val_x=x[:31000],x[31000:]
train_y,val_y=y[:31000],y[31000:]
model=tf.keras.Sequential([
    tf.keras.layers.Input(shape=(FEATURES,),dtype=tf.float32),
    tf.keras.layers.Dense(32,activation='relu'),
    tf.keras.layers.Dense(16,activation='relu'),
    tf.keras.layers.Dense(1,activation='sigmoid'),
])
model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=0.007),loss='mse',metrics=['mae'])
model.fit(train_x,train_y,batch_size=512,epochs=18,verbose=0,validation_data=(val_x,val_y))
loss,mae=model.evaluate(val_x,val_y,verbose=0)
assert mae<0.065, f"Model did not learn synthetic ranking teacher: MAE={mae:.4f}"
converter=tf.lite.TFLiteConverter.from_keras_model(model)
converter.optimizations=[tf.lite.Optimize.DEFAULT]
lite=converter.convert()
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_bytes(lite)
# Use the actual TFLite interpreter (the same model format used in Android)
interpreter=tf.lite.Interpreter(model_content=lite,num_threads=1)
interpreter.allocate_tensors()
info=interpreter.get_input_details()[0]
out=interpreter.get_output_details()[0]
assert list(info['shape'])==[1,FEATURES],info
assert list(out['shape'])==[1,1],out

def predicted(sample):
    interpreter.set_tensor(info['index'],sample.reshape(1,-1).astype(np.float32))
    interpreter.invoke()
    return float(interpreter.get_tensor(out['index'])[0,0])
def candidate(tag,acts,climate=0,priority=0.5,wet=False,tech=False):
    a=np.zeros(FEATURES,np.float32)
    a[tag]=1.
    for i,v in enumerate(acts):a[5+i]=float(v)
    a[9]=float(climate==1);a[10]=float(climate==2)
    a[11]=7/30;a[12]=2/8;a[14]=priority
    a[16]=float(wet);a[17]=float(tech)
    return a

beach=[predicted(candidate(tag,[1,0,0,0],2)) for tag in range(5)]
ski=[predicted(candidate(tag,[0,0,1,0],1)) for tag in range(5)]
photo=[predicted(candidate(tag,[0,0,0,1],0)) for tag in range(5)]
assert max(range(5),key=lambda i:beach[i])==0,beach
assert max(range(5),key=lambda i:ski[i])==2,ski
assert max(range(5),key=lambda i:photo[i])==3,photo
assert max(beach)-min(beach)>0.35,beach
AUDIT.parent.mkdir(parents=True,exist_ok=True)
AUDIT.write_text(json.dumps({
    'architecture':'18 float inputs -> Dense32 ReLU -> Dense16 ReLU -> 1 relevance score sigmoid',
    'engine':'Google LiteRT / TFLite',
    'provenance':'trained from 31,000 synthetic travel-item relevance examples; validated on 5,000 held-out examples',
    'external_user_data_used':False,
    'seed':SEED,'holdout_mae':round(float(mae),5),
    'model_bytes':len(lite),
    'predictions_by_item_tag_beach_hike_ski_photo_general':{
      'beach_trip':beach,'ski_trip':ski,'photo_trip':photo
    }
},ensure_ascii=False,indent=2),encoding='utf-8')
print('RankNet model',str(OUT),len(lite),'bytes; heldout MAE',round(float(mae),5))
print('beach scores',beach,'ski scores',ski,'photo scores',photo)
